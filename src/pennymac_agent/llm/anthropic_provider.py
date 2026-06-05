"""Anthropic implementation of the LLMProvider contract."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .base import ChatMessage, LLMProvider, LLMResponse, ToolCall, ToolSpec


class AnthropicProvider(LLMProvider):
    """Adapter over the Anthropic Messages API (tools / tool_use blocks)."""

    def __init__(self, api_key: str, model: str, **kwargs: Any):
        super().__init__(model=model, **kwargs)
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)

    # --- translation helpers -------------------------------------------------
    @staticmethod
    def _tools_to_wire(tools: Optional[List[ToolSpec]]) -> Optional[List[dict]]:
        if not tools:
            return None
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]

    @staticmethod
    def _messages_to_wire(messages: List[ChatMessage]) -> List[dict]:
        """Translate neutral messages into Anthropic content-block messages."""
        wire: List[dict] = []
        for m in messages:
            if m.role == "tool":
                wire.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": m.tool_call_id,
                                "content": m.content,
                            }
                        ],
                    }
                )
            elif m.role == "assistant" and m.tool_calls:
                blocks: List[dict] = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": tc.arguments,
                        }
                    )
                wire.append({"role": "assistant", "content": blocks})
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
            "messages": self._messages_to_wire(messages),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        if system:
            kwargs["system"] = system
        wire_tools = self._tools_to_wire(tools)
        if wire_tools:
            kwargs["tools"] = wire_tools

        resp = self._client.messages.create(**kwargs)

        text_parts: List[str] = []
        tool_calls: List[ToolCall] = []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                args = block.input if isinstance(block.input, dict) else {}
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=args)
                )

        return LLMResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            raw=resp,
        )
