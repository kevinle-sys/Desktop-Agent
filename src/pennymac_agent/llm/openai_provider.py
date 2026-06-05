"""OpenAI implementation of the LLMProvider contract."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .base import ChatMessage, LLMProvider, LLMResponse, ToolCall, ToolSpec


class OpenAIProvider(LLMProvider):
    """Adapter over the OpenAI Chat Completions API (tools / tool_calls)."""

    def __init__(self, api_key: str, model: str, **kwargs: Any):
        super().__init__(model=model, **kwargs)
        # Imported lazily so the package can be installed/used without OpenAI.
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)

    # --- translation helpers -------------------------------------------------
    @staticmethod
    def _tools_to_wire(tools: Optional[List[ToolSpec]]) -> Optional[List[dict]]:
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

    @staticmethod
    def _messages_to_wire(
        messages: List[ChatMessage], system: Optional[str]
    ) -> List[dict]:
        wire: List[dict] = []
        if system:
            wire.append({"role": "system", "content": system})
        for m in messages:
            if m.role == "tool":
                wire.append(
                    {
                        "role": "tool",
                        "tool_call_id": m.tool_call_id,
                        "content": m.content,
                    }
                )
            elif m.role == "assistant" and m.tool_calls:
                wire.append(
                    {
                        "role": "assistant",
                        "content": m.content or None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments),
                                },
                            }
                            for tc in m.tool_calls
                        ],
                    }
                )
            else:
                wire.append({"role": m.role, "content": m.content})
        return wire

    # --- main entrypoint ------------------------------------------------------
    def chat(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolSpec]] = None,
        system: Optional[str] = None,
    ) -> LLMResponse:
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": self._messages_to_wire(messages, system),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        wire_tools = self._tools_to_wire(tools)
        if wire_tools:
            kwargs["tools"] = wire_tools
            kwargs["tool_choice"] = "auto"

        resp = self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0].message

        tool_calls: List[ToolCall] = []
        for tc in choice.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(
                ToolCall(id=tc.id, name=tc.function.name, arguments=args)
            )

        return LLMResponse(
            text=choice.content or "",
            tool_calls=tool_calls,
            raw=resp,
        )
