"""Agent registry and tool-schema construction.

The registry holds the set of sub-agents available to the orchestrator and
exposes them to the LLM as a list of provider-agnostic ToolSpecs.
"""

from __future__ import annotations

from typing import Dict, List

from ..agents.base_agent import BaseAgent
from ..llm.base import ToolSpec


class AgentRegistry:
    """A name -> agent map that also produces LLM tool schemas."""

    def __init__(self) -> None:
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> "AgentRegistry":
        if agent.name in self._agents:
            raise ValueError(f"Agent name '{agent.name}' already registered.")
        self._agents[agent.name] = agent
        return self

    def get(self, name: str) -> BaseAgent:
        if name not in self._agents:
            raise KeyError(f"No agent registered under '{name}'.")
        return self._agents[name]

    def __contains__(self, name: str) -> bool:
        return name in self._agents

    @property
    def names(self) -> List[str]:
        return list(self._agents)

    def tool_specs(self) -> List[ToolSpec]:
        """Return tool schemas for every registered agent."""
        return [agent.to_tool_spec() for agent in self._agents.values()]
