"""Model client — single completion + native tool-calling (N1, specs/llm.md).

Only the vendor client library (`openai`) and the model's NATIVE tool calling
are used here — no agent frameworks. The OpenAI-compatible gateway is configurable
via `base_url`, so OpenAI / DeepSeek / Claude-gateway / local models all work.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError

from .config import Config

_RETRYABLE = (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError)
_MAX_RETRIES = 3


def _create_with_retry(client: Any, **kwargs: Any) -> Any:
    """Call the chat completions endpoint with retries on transient network errors."""
    last_err: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return client.chat.completions.create(**kwargs)
        except _RETRYABLE as exc:
            last_err = exc
            if attempt < _MAX_RETRIES - 1:
                time.sleep(1.5 * (attempt + 1))
    raise last_err  # type: ignore[misc]


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

        resp = _create_with_retry(self._client, **kwargs)
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

    def stream_complete(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        on_delta: Any | None = None,
    ) -> LLMResult:
        """Streaming variant of `complete` (R11/C9).

        Text tokens are delivered to `on_delta` as they arrive; tool-call
        arguments (which arrive in fragments) are accumulated by index and
        assembled into `ToolCall`s. Usage is captured if the gateway sends it
        on the final chunk (otherwise {}).
        """
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        try:
            stream = _create_with_retry(self._client, **kwargs, stream_options={"include_usage": True})
        except TypeError:
            stream = _create_with_retry(self._client, **kwargs)

        text_parts: list[str] = []
        tool_accum: dict[int, dict[str, Any]] = {}
        usage: dict[str, int] = {}
        for chunk in stream:
            if getattr(chunk, "usage", None):
                usage = _usage_dict(chunk.usage)
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if getattr(delta, "content", None):
                text_parts.append(delta.content)
                if on_delta:
                    on_delta(delta.content)
            for tc in getattr(delta, "tool_calls", None) or []:
                entry = tool_accum.setdefault(tc.index, {"id": "", "name": "", "args": []})
                if getattr(tc, "id", None):
                    entry["id"] = tc.id
                fn = getattr(tc, "function", None)
                if fn:
                    if getattr(fn, "name", None):
                        entry["name"] = fn.name
                    if getattr(fn, "arguments", None):
                        entry["args"].append(fn.arguments)

        tool_calls: list[ToolCall] = []
        for index in sorted(tool_accum):
            entry = tool_accum[index]
            try:
                args = json.loads("".join(entry["args"]) or "{}")
            except json.JSONDecodeError:
                args = {}
            if not isinstance(args, dict):
                args = {}
            tool_calls.append(ToolCall(id=entry["id"] or f"call_{index}", name=entry["name"], arguments=args))
        return LLMResult(text="".join(text_parts), tool_calls=tool_calls, usage=usage)


def _usage_dict(usage: Any) -> dict[str, int]:
    """Normalize usage into a plain dict (real pydantic models, dicts, or test fakes)."""
    if usage is None:
        return {}
    if isinstance(usage, dict):
        return dict(usage)
    if hasattr(usage, "model_dump"):
        return dict(usage.model_dump())
    return dict(vars(usage))
