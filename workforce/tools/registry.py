"""Tool registry: web, filesystem (sandboxed) and opt-in shell tools."""

from __future__ import annotations

import html
import pathlib
import re
import subprocess
import urllib.parse
import urllib.request
from typing import Any, Callable

TOOL_TIMEOUT = 30


class SandboxError(Exception):
    pass


_FORBIDDEN = (".git", ".env")  # never expose or mutate these from the workspace


def _resolve_in_sandbox(sandbox: str, rel: str) -> pathlib.Path:
    root = pathlib.Path(sandbox).resolve()
    candidate = (root / rel).resolve()
    if candidate != root and root not in candidate.parents:
        raise SandboxError(f"path escapes sandbox: {rel!r}")
    return candidate


def _scrape_duckduckgo(query: str) -> str:
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 workforce"})
    with urllib.request.urlopen(req, timeout=TOOL_TIMEOUT) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    results: list[str] = []
    for block in re.findall(
        r'<div class="result[^"]*".*?</div>\s*</div>', raw, flags=re.DOTALL
    )[:5]:
        title = re.search(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', block, flags=re.DOTALL)
        snippet = re.search(
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', block, flags=re.DOTALL
        )
        link = re.search(r'href="([^"]+)"', block)
        href = ""
        if link:
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(link.group(1)).query)
            href = parsed.get("uddg", [""])[0]
        title_t = html.unescape(re.sub(r"<[^>]+>", "", title.group(1))) if title else ""
        snip_t = html.unescape(re.sub(r"<[^>]+>", "", snippet.group(1))) if snippet else ""
        if title_t:
            results.append(f"- {title_t} {href}\n  {snip_t}")
    if not results:
        return f"No results fetched for: {query}"
    return "Search: " + query + "\n" + "\n".join(results)


def _fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 workforce"})
    with urllib.request.urlopen(req, timeout=TOOL_TIMEOUT) as resp:
        ctype = resp.headers.get("Content-Type", "")
        raw = resp.read(200_000).decode("utf-8", errors="replace")
    if "html" in ctype or raw.lstrip().startswith(("<", "{")):
        raw = re.sub(r"<script.*?</script>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
        raw = re.sub(r"<style.*?</style>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
        raw = re.sub(r"<[^>]+>", " ", raw)
        raw = html.unescape(raw)
        raw = re.sub(r"\s+", " ", raw).strip()
    return f"URL: {url}\nContent-Type: {ctype}\n\n{raw[:8000]}"


class ToolRegistry:
    """A mutable, sandbox-aware tool collection."""

    def __init__(self, config) -> None:
        self.config = config
        self._tools: dict[str, dict[str, Any]] = {}
        self._register_builtins()

    # ------------------------------------------------------------------ #
    def _register_builtins(self) -> None:
        tc = self.config.tools
        builtins: list[tuple[str, dict[str, Any], Callable[[dict[str, Any]], str], bool]] = [
            (
                "search_web",
                {
                    "description": "Search the web and return top result snippets for a query.",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                },
                lambda a: self._wrap(_scrape_duckduckgo, self._arg(a, "query")),
                tc.search_web,
            ),
            (
                "fetch_url",
                {
                    "description": "Fetch and return the text content of a URL.",
                    "parameters": {
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"],
                    },
                },
                lambda a: self._wrap(_fetch_url, self._arg(a, "url")),
                tc.fetch_url,
            ),
            (
                "read_file",
                {
                    "description": "Read a file inside the sandbox. Relative paths are allowed.",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
                lambda a: self.read_file(self._arg(a, "path")),
                tc.file_ops,
            ),
            (
                "write_file",
                {
                    "description": "Write UTF-8 content to a file inside the sandbox (creates parent dirs).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                    },
                },
                lambda a: self.write_file(self._arg(a, "path"), self._arg(a, "content")),
                tc.file_ops,
            ),
            (
                "list_files",
                {
                    "description": "List files (recursively optional) inside a sandbox directory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "directory, default '.'"},
                            "recursive": {"type": "boolean", "default": False},
                        },
                    },
                },
                lambda a: self.list_files(self._arg(a, "path", "."), bool(a.get("recursive"))),
                tc.file_ops,
            ),
            (
                "run_command",
                {
                    "description": "Run a shell command inside the sandbox (disabled by default).",
                    "parameters": {
                        "type": "object",
                        "properties": {"command": {"type": "string"}},
                        "required": ["command"],
                    },
                },
                lambda a: self.run_command(self._arg(a, "command")),
                tc.shell,
            ),
        ]
        for name, spec, fn, enabled in builtins:
            self._tools[name] = {"spec": spec, "fn": fn, "enabled": enabled}

    # ------------------------------------------------------------------ #
    def register(self, name: str, spec: dict[str, Any], fn: Callable[[dict[str, Any]], str], enabled: bool = True) -> None:
        self._tools[name] = {"spec": spec, "fn": fn, "enabled": enabled}

    def enabled_names(self) -> list[str]:
        return [n for n, t in self._tools.items() if t["enabled"]]

    def tool_specs(self) -> dict[str, dict[str, Any]]:
        return {n: t["spec"] for n, t in self._tools.items() if t["enabled"]}

    def executors(self) -> dict[str, Callable[[str, dict[str, Any]], str]]:
        def make(name: str, fn: Callable[[dict[str, Any]], str]) -> Callable[[str, dict[str, Any]], str]:
            def run(_name: str, args: dict[str, Any]) -> str:
                return fn(args)

            return run

        return {n: make(n, t["fn"]) for n, t in self._tools.items() if t["enabled"]}

    # ------------------------------------------------------------------ #
    # sandboxed filesystem
    # ------------------------------------------------------------------ #
    def read_file(self, rel: str) -> str:
        safe = _resolve_in_sandbox(self.config.tools.sandbox, rel)
        self._guard(safe)
        if not safe.is_file():
            return f"ERROR: file not found: {rel}"
        return safe.read_text(encoding="utf-8", errors="replace")[:20_000]

    def write_file(self, rel: str, content: str) -> str:
        safe = _resolve_in_sandbox(self.config.tools.sandbox, rel)
        self._guard(safe)
        safe.parent.mkdir(parents=True, exist_ok=True)
        safe.write_text(content, encoding="utf-8")
        return f"Wrote {safe} ({len(content)} chars)"

    def list_files(self, rel: str = ".", recursive: bool = False) -> str:
        safe = _resolve_in_sandbox(self.config.tools.sandbox, rel)
        if not safe.is_dir():
            return f"ERROR: not a directory: {rel}"
        pattern = "**/*" if recursive else "*"
        items = sorted(safe.glob(pattern))
        lines = [f"{i.relative_to(self.config.tools.sandbox)}" for i in items if i.is_file()]
        return "\n".join(lines) or "(empty)"

    def run_command(self, command: str) -> str:
        if not self.config.tools.shell:
            return "ERROR: shell execution is disabled. Enable with allow_shell: true."
        cwd = pathlib.Path(self.config.tools.sandbox).resolve()
        cwd.mkdir(parents=True, exist_ok=True)
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=TOOL_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return "ERROR: command timed out"
        out = proc.stdout[-8000:] + proc.stderr[-4000:]
        return out or f"(exit {proc.returncode})"

    # ------------------------------------------------------------------ #
    def _guard(self, path: "pathlib.Path") -> None:
        for part in path.relative_to(self.config.tools.sandbox).parts:
            if part in _FORBIDDEN:
                raise SandboxError(f"path touches protected entry: {part!r}")

    @staticmethod
    def _arg(args: dict[str, Any], key: str, default: Any = "") -> Any:
        return args.get(key, default)

    @staticmethod
    def _wrap(fn: Callable[[str], str], value: str) -> str:
        try:
            return fn(value)
        except Exception as exc:
            return f"ERROR: {type(exc).__name__}: {exc}"


def build_default_registry(config) -> ToolRegistry:
    return ToolRegistry(config)
