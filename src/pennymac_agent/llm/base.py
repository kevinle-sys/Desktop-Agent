"""Provider-agnostic LLM contract.

The Orchestrator depends only on these neutral types. Each concrete provider
(OpenAI, Anthropic) translates them to/from its own wire format so the rest of
the codebase is vendor-independent.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolSpec:
    """A tool/function the model may call, in JSON-Schema form."""

    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema for the arguments object.


@dataclass
class ToolCall:
    """A structured request from the model to invoke a tool."""

    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ChatMessage:
    """A single message in the conversation.

    ``role`` is one of: "system", "user", "assistant", "tool".
    For tool-result messages, set ``tool_call_id`` and put the result text in
    ``content``.
    """

    role: str
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class LLMResponse:
    """Normalized response from a provider chat completion."""

    text: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    raw: Any = None

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


class LLMProvider(ABC):
    """Abstract chat provider supporting native tool calling."""

    def __init__(self, model: str, max_tokens: int = 4096, temperature: float = 0.0):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    @abstractmethod
    def chat(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolSpec]] = None,
        system: Optional[str] = None,
    ) -> LLMResponse:
        """Send a chat request and return a normalized response."""
        raise NotImplementedError
