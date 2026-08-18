"""Configuration loading and merging for the workforce.

Precedence (lowest to highest):
    built-in defaults < workforce.yaml < environment variables < explicit overrides
"""

from __future__ import annotations

import json
import os
import pathlib
from dataclasses import dataclass, field, asdict
from typing import Any, Mapping

import yaml

DEFAULT_YAML = "workforce.yaml"
DEFAULT_ENV_FILE = ".env"


# --------------------------------------------------------------------------- #
# dataclasses
# --------------------------------------------------------------------------- #
@dataclass
class LLMConfig:
    """Credentials and endpoint for the OpenAI-compatible chat API."""

    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout_seconds: float = 120.0
    max_tool_rounds: int = 8

    def endpoint(self) -> str:
        base = self.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"


@dataclass
class ToolConfig:
    """Which tools are enabled for agents."""

    fetch_url: bool = True
    search_web: bool = True
    file_ops: bool = True
    shell: bool = False  # intentionally off by default
    sandbox: str = "workspace"


@dataclass
class WorkforceConfig:
    run_id: str = ""
    goal: str = ""
    provider: str = "openai"  # "openai" or "mock"
    llm: LLMConfig = field(default_factory=LLMConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    workers: int = 3
    max_attempts: int = 3
    artifact_dir: str = "data/runs"
    memory_db: str = "data/workforce.db"
    tracing: bool = True
    verbose: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# .env loader (no external dependency)
# --------------------------------------------------------------------------- #
def load_dotenv(path: str | os.PathLike | None = DEFAULT_ENV_FILE) -> dict[str, str]:
    """Parse a KEY=VALUE dotenv file into a dict. Missing files return {}."""
    p = pathlib.Path(path) if path else None
    if p is None or not p.is_file():
        return {}
    out: dict[str, str] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            out[key] = value
    return out


ENV_MAP = {
    "api_key": "OPENAI_API_KEY",
    "base_url": "OPENAI_BASE_URL",
    "model": "OPENAI_MODEL",
    "temperature": "OPENAI_TEMPERATURE",
    "max_tokens": "OPENAI_MAX_TOKENS",
    "timeout_seconds": "OPENAI_TIMEOUT_SECONDS",
    "max_tool_rounds": "OPENAI_MAX_TOOL_ROUNDS",
    "allow_shell": "WORKFORCE_ALLOW_SHELL",
    "workers": "WORKFORCE_WORKERS",
    "max_attempts": "WORKFORCE_MAX_ATTEMPTS",
    "sandbox": "WORKFORCE_SANDBOX",
    "provider": "WORKFORCE_PROVIDER",
    "memory_db": "WORKFORCE_MEMORY_DB",
    "artifact_dir": "WORKFORCE_ARTIFACT_DIR",
    "tracing": "WORKFORCE_TRACING",
}


def _coerce(key: str, value: Any) -> Any:
    if isinstance(value, str):
        low = value.lower()
        if low in {"true", "1", "yes", "on"}:
            return True
        if low in {"false", "0", "no", "off"}:
            return False
        if key in {"temperature", "timeout_seconds"}:
            return float(value)
        if key in {
            "max_tokens",
            "max_tool_rounds",
            "workers",
            "max_attempts",
        }:
            return int(value)
    return value


def _apply_env(cfg: WorkforceConfig, env: Mapping[str, str]) -> WorkforceConfig:
    for attr, var in ENV_MAP.items():
        if var in env and env[var] != "":
            put = _coerce(attr, env[var])
            if attr == "allow_shell":
                cfg.tools.shell = bool(put)
            elif attr == "sandbox":
                cfg.tools.sandbox = str(put)
            elif hasattr(cfg.llm, attr):
                setattr(cfg.llm, attr, put)
            else:
                setattr(cfg, attr, put)
    return cfg


def _apply_yaml(cfg: WorkforceConfig, data: Mapping[str, Any]) -> WorkforceConfig:
    if not data:
        return cfg
    llm_data = data.get("llm", {})
    tools_data = data.get("tools", {})
    if isinstance(llm_data, Mapping):
        for k, v in llm_data.items():
            setattr(cfg.llm, k, _coerce(k, v))
    if isinstance(tools_data, Mapping):
        for k, v in tools_data.items():
            setattr(cfg.tools, k, _coerce(k, v))
    for k, v in data.items():
        if k in {"llm", "tools"}:
            continue
        setattr(cfg, k, _coerce(k, v))
    return cfg


def load_config(
    yaml_path: str | os.PathLike | None = DEFAULT_YAML,
    env_path: str | os.PathLike | None = DEFAULT_ENV_FILE,
    overrides: Mapping[str, Any] | None = None,
) -> WorkforceConfig:
    """Load configuration with defaults < yaml < env < overrides."""
    cfg = WorkforceConfig()

    # yaml
    if yaml_path:
        p = pathlib.Path(yaml_path)
        if p.is_file():
            with p.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            _apply_yaml(cfg, data)

    # env
    env = dict(os.environ)
    env.update(load_dotenv(env_path))
    _apply_env(cfg, env)

    # overrides (explicit CLI flags)
    for k, v in (overrides or {}).items():
        if v is None:
            continue
        if k == "llm" and isinstance(v, Mapping):
            for kk, vv in v.items():
                setattr(cfg.llm, kk, _coerce(kk, vv))
        elif k == "api_key":
            cfg.llm.api_key = str(v)
        elif hasattr(cfg.llm, k):
            setattr(cfg.llm, k, _coerce(k, v))
        else:
            setattr(cfg, k, _coerce(k, v))

    # derived bits
    cfg.tools.sandbox = os.path.abspath(cfg.tools.sandbox)
    cfg.artifact_dir = os.path.abspath(cfg.artifact_dir)
    cfg.memory_db = os.path.abspath(cfg.memory_db)
    return cfg


def config_to_json(cfg: WorkforceConfig) -> str:
    """Serialise a config for the CLI / API responses."""
    return json.dumps(cfg.to_dict(), indent=2, default=str)
