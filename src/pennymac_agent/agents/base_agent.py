"""Base abstraction shared by every sub-agent.

A sub-agent advertises itself to the LLM as a single callable tool. The
contract is intentionally small: a unique ``name``, a ``description`` that tells
the model *when* to use it, a JSON-Schema ``parameters`` object, and a ``run``
method that returns an :class:`AgentResult`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict

from ..llm.base import ToolSpec


@dataclass
class AgentResult:
    """Outcome of an agent invocation.

    ``data`` holds the machine payload (e.g. a DataFrame) for downstream use,
    while ``summary`` is a compact, model-facing string so large objects are
    never dumped verbatim back into the LLM context.
    """

    ok: bool
    summary: str
    data: Any = None
    meta: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(cls, summary: str, data: Any = None, **meta: Any) -> "AgentResult":
        return cls(ok=True, summary=summary, data=data, meta=meta)

    @classmethod
    def failure(cls, summary: str, **meta: Any) -> "AgentResult":
        return cls(ok=False, summary=summary, data=None, meta=meta)


class BaseAgent(ABC):
    """Abstract specialist agent exposed to the orchestrator as a tool."""

    #: Unique tool name (snake_case), referenced by the LLM in tool calls.
    name: str = "base_agent"
    #: Natural-language description telling the model when to choose this agent.
    description: str = "Base agent. Do not call directly."
    #: JSON Schema describing the ``run`` arguments object.
    parameters: Dict[str, Any] = {"type": "object", "properties": {}}

    @abstractmethod
    def run(self, **kwargs: Any) -> AgentResult:
        """Execute the agent's task and return an :class:`AgentResult`."""
        raise NotImplementedError

    def to_tool_spec(self) -> ToolSpec:
        """Return the provider-agnostic tool schema for this agent."""
        return ToolSpec(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )
