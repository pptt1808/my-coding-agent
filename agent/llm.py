"""Model client — single completion + native tool-calling (N1, specs/llm.md).

Only the vendor client library (`openai`) and the model's NATIVE tool calling
are used here — no agent frameworks. The OpenAI-compatible gateway is configurable
via `base_url`, so OpenAI / DeepSeek / Claude-gateway / local models all work.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from .config import Config


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResult:
    """A single model turn: either tool calls, or a final text answer."""
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)


class LLMClient:
    """Thin wrapper over the OpenAI-compatible chat completions API.

    `client` is injectable for tests (a fake OpenAI object); production code
    creates the real `openai.OpenAI(api_key=..., base_url=...)`.

    Model layering: pass `model=` to pick a specific tier (e.g. the eval harness
    passes `config.eval_model_name` for the strong tier); defaults to the
    config's interactive/dev `model`.
    """

    def __init__(self, config: Config, client: Any | None = None, model: str | None = None) -> None:
        self._config = config
        self._model = model or config.model
        self._client = client or OpenAI(api_key=config.api_key, base_url=config.base_url)

    def complete(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResult:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        resp = self._client.chat.completions.create(**kwargs)
        message = resp.choices[0].message

        tool_calls: list[ToolCall] = []
        for tc in message.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            if not isinstance(args, dict):
                args = {}
            tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))

        usage: dict[str, int] = _usage_dict(resp.usage)
        return LLMResult(text=message.content or "", tool_calls=tool_calls, usage=usage)


def _usage_dict(usage: Any) -> dict[str, int]:
    """Normalize usage into a plain dict (real pydantic models, dicts, or test fakes)."""
    if usage is None:
        return {}
    if isinstance(usage, dict):
        return dict(usage)
    if hasattr(usage, "model_dump"):
        return dict(usage.model_dump())
    return dict(vars(usage))
