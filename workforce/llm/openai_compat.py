"""OpenAI-compatible chat completions client built on the standard library."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .base import LLMError, LLMResponse, ToolCall, Usage

API_RESPONSE_FORMAT = {"type": "json_object"}


class OpenAICompatProvider:
    """Speaks the ``POST /chat/completions`` protocol.

    Works with OpenAI, Azure, OpenRouter, Ollama, vLLM, LM Studio and any other
    OpenAI-compatible server. Only the standard library is used.
    """

    name = "openai"

    def __init__(self, cfg) -> None:
        self.cfg = cfg
        self.endpoint = cfg.endpoint()

    # ------------------------------------------------------------------ #
    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.cfg.model,
            "messages": messages,
            "temperature": self.cfg.temperature if temperature is None else temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        elif self.cfg.max_tokens:
            payload["max_tokens"] = self.cfg.max_tokens
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        if json_mode:
            payload["response_format"] = API_RESPONSE_FORMAT

        data = self._post(payload)
        # Some servers reject response_format; retry without it.
        if json_mode and self._payload_rejected(data):
            del payload["response_format"]
            data = self._post(payload)

        return self._parse(data)

    # ------------------------------------------------------------------ #
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.cfg.api_key:
            headers["Authorization"] = f"Bearer {self.cfg.api_key}"
        return headers

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint, data=body, headers=self._headers(), method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:800]
            raise LLMError(
                f"LLM HTTP {exc.code} from {self.endpoint}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise LLMError(f"LLM connection error to {self.endpoint}: {exc.reason}") from exc
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMError(f"Invalid JSON from LLM endpoint: {raw[:300]}") from exc

    @staticmethod
    def _payload_rejected(data: dict[str, Any]) -> bool:
        err = data.get("error") or {}
        return bool(err) and str(err.get("code", "")).lower() in {
            "invalid_request_error",
            "bad_request",
            "unsupported_parameter",
        }

    def _parse(self, data: dict[str, Any]) -> LLMResponse:
        try:
            choice = data["choices"][0]
            message = choice.get("message", {}) or {}
        except (KeyError, IndexError) as exc:
            raise LLMError(f"Unexpected LLM response shape: {str(data)[:400]}") from exc

        usage_raw = data.get("usage") or {}
        usage = Usage(
            prompt_tokens=int(usage_raw.get("prompt_tokens") or 0),
            completion_tokens=int(usage_raw.get("completion_tokens") or 0),
        )
        tool_calls = []
        for tc in message.get("tool_calls") or []:
            try:
                args = json.loads(tc.get("function", {}).get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(
                ToolCall(
                    id=tc.get("id", ""),
                    name=tc.get("function", {}).get("name", ""),
                    arguments=args,
                )
            )
        return LLMResponse(
            text=message.get("content") or "",
            tool_calls=tool_calls,
            usage=usage,
        )
