"""The Orchestrator: the only component that talks to the LLM.

It advertises each registered sub-agent as a callable tool, sends the trader's
request to the configured provider, and runs a dispatch loop: every structured
tool call from the model is routed to the matching agent, executed, and the
result is fed back until the model produces a final answer (or max_iterations
is reached).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ..agents import (
    ExcelModelingAgent,
    SnowflakeAgent,
    VBAProcessAgent,
)
from ..agents.base_agent import AgentResult
from ..config.settings import Settings, get_settings
from ..llm.base import ChatMessage, LLMProvider, ToolCall
from ..llm.factory import build_provider
from ..utils.logging import get_logger
from .router import AgentRegistry

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are the Orchestrator for a PennyMac Secondary Market Trader's desktop "
    "agent. Interpret the trader's request and accomplish it by calling the "
    "available specialist tools (Snowflake/SQL data, Excel pricing models, and "
    "VBA automation). Chain tools when a task needs several steps (e.g. query "
    "data, push it into a model, then run a macro). Use tools for any real "
    "data, calculation, or automation; never fabricate loan, pricing, or model "
    "values. When done, give a concise, trader-friendly summary of what you "
    "did and the key results."
)


@dataclass
class OrchestratorResult:
    """Outcome of a full orchestration run."""

    final_text: str
    tool_invocations: List[dict] = field(default_factory=list)


class Orchestrator:
    """Routes trader requests to sub-agents via LLM tool calling."""

    def __init__(
        self,
        provider: LLMProvider,
        registry: AgentRegistry,
        system_prompt: str = SYSTEM_PROMPT,
        max_iterations: int = 8,
    ) -> None:
        self.provider = provider
        self.registry = registry
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations

    def _dispatch(self, call: ToolCall) -> AgentResult:
        """Execute a single tool call against its agent."""
        if call.name not in self.registry:
            return AgentResult.failure(f"Unknown tool '{call.name}'.")
        agent = self.registry.get(call.name)
        logger.info("Dispatching to %s with %s", call.name, call.arguments)
        try:
            return agent.run(**call.arguments)
        except Exception as exc:  # defensive: agents also catch internally
            logger.exception("Agent '%s' raised", call.name)
            return AgentResult.failure(f"Agent '{call.name}' error: {exc}")

    def handle(self, user_request: str) -> OrchestratorResult:
        """Run the full tool-calling loop for a single request."""
        messages: List[ChatMessage] = [
            ChatMessage(role="user", content=user_request)
        ]
        tools = self.registry.tool_specs()
        invocations: List[dict] = []

        for _ in range(self.max_iterations):
            response = self.provider.chat(
                messages=messages, tools=tools, system=self.system_prompt
            )

            if not response.wants_tools:
                return OrchestratorResult(
                    final_text=response.text or "(no response)",
                    tool_invocations=invocations,
                )

            # Record the assistant's tool-call turn.
            messages.append(
                ChatMessage(
                    role="assistant",
                    content=response.text,
                    tool_calls=response.tool_calls,
                )
            )

            # Execute each requested tool and append results.
            for call in response.tool_calls:
                result = self._dispatch(call)
                invocations.append(
                    {
                        "tool": call.name,
                        "arguments": call.arguments,
                        "ok": result.ok,
                        "summary": result.summary,
                    }
                )
                messages.append(
                    ChatMessage(
                        role="tool",
                        tool_call_id=call.id,
                        name=call.name,
                        content=result.summary,
                    )
                )

        return OrchestratorResult(
            final_text=(
                "Reached the maximum number of tool iterations "
                f"({self.max_iterations}) without a final answer."
            ),
            tool_invocations=invocations,
        )

    # --- dry-run (no LLM / no credentials) -----------------------------------
    def describe_capabilities(self) -> str:
        """Human-readable list of registered tools (used in dry-run mode)."""
        lines = ["Registered specialist agents:"]
        for spec in self.registry.tool_specs():
            lines.append(f"  - {spec.name}: {spec.description}")
        return "\n".join(lines)


def build_registry(settings: Optional[Settings] = None) -> AgentRegistry:
    """Register the three standard sub-agents."""
    settings = settings or get_settings()
    return (
        AgentRegistry()
        .register(SnowflakeAgent(settings))
        .register(ExcelModelingAgent(settings))
        .register(VBAProcessAgent(settings))
    )


def build_default_orchestrator(
    settings: Optional[Settings] = None,
) -> Orchestrator:
    """Build an Orchestrator with the configured provider and standard agents."""
    settings = settings or get_settings()
    provider = build_provider(settings)
    registry = build_registry(settings)
    return Orchestrator(provider=provider, registry=registry)
