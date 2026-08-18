"""Agentic tool-calling loop shared by every agent."""

from __future__ import annotations

from typing import Any, Callable

from .base import LLMError, LLMResponse

ToolExecutor = Callable[[str, dict[str, Any]], str]


def tool_schemas(specs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert {name: {description, parameters}} to OpenAI tool definitions."""
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": spec.get("description", ""),
                "parameters": spec.get(
                    "parameters",
                    {"type": "object", "properties": {}},
                ),
            },
        }
        for name, spec in specs.items()
    ]


def chat_with_tools(
    llm,
    system: str,
    messages: list[dict[str, Any]],
    *,
    tools: dict[str, ToolExecutor],
    tool_specs: dict[str, dict[str, Any]],
    json_mode: bool = False,
    max_rounds: int = 8,
) -> tuple[LLMResponse, list[dict[str, Any]]]:
    """Run an LLM conversation, executing tool calls in the loop.

    Returns the final (non-tool) response and the full message transcript.
    """
    transcript = [{"role": "system", "content": system}, *messages]
    final = LLMResponse()
    schemas = tool_schemas(tool_specs) if tool_specs else None

    for _ in range(max_rounds):
        response = llm.chat(
            transcript,
            tools=schemas,
            json_mode=json_mode,
        )
        if not response.tool_calls:
            final = response
            break
        transcript.append(
            {
                "role": "assistant",
                "content": response.text or None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": _json_args(tc.arguments),
                        },
                    }
                    for tc in response.tool_calls
                ],
            }
        )
        for tc in response.tool_calls:
            if tc.name not in tools:
                output = f"ERROR: unknown tool '{tc.name}'"
            else:
                try:
                    output = tools[tc.name](tc.name, tc.arguments)
                except Exception as exc:  # tool errors become tool output
                    output = f"ERROR: {type(exc).__name__}: {exc}"
            transcript.append(
                {"role": "tool", "tool_call_id": tc.id, "content": output}
            )
    else:
        raise LLMError(f"Tool loop exceeded {max_rounds} rounds")

    return final, transcript


def _json_args(args: dict[str, Any]) -> str:
    import json

    return json.dumps(args)
