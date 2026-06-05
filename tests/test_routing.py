"""Smoke tests for agent registration and the orchestrator dispatch loop.

These tests use a fake in-memory LLM provider so they run without any API
keys, network, Snowflake, or Excel.
"""

from typing import List, Optional

from pennymac_agent.agents.base_agent import AgentResult, BaseAgent
from pennymac_agent.llm.base import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    ToolCall,
    ToolSpec,
)
from pennymac_agent.orchestrator.orchestrator import Orchestrator, build_registry
from pennymac_agent.orchestrator.router import AgentRegistry


class EchoAgent(BaseAgent):
    name = "echo"
    description = "Echo back the provided text."
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    def run(self, text: str = "", **_) -> AgentResult:
        return AgentResult.success(f"echo: {text}", data=text)


class ScriptedProvider(LLMProvider):
    """Returns a queued list of responses, one per chat() call."""

    def __init__(self, responses: List[LLMResponse]):
        super().__init__(model="fake", max_tokens=10, temperature=0.0)
        self._responses = list(responses)

    def chat(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolSpec]] = None,
        system: Optional[str] = None,
    ) -> LLMResponse:
        return self._responses.pop(0)


def test_default_registry_has_all_agents():
    registry = build_registry()
    assert set(registry.names) == {
        "snowflake_query",
        "sqlserver_query",
        "excel_model",
        "vba_process",
    }
    specs = registry.tool_specs()
    assert all(isinstance(s, ToolSpec) for s in specs)
    assert len(specs) == 4


def test_registry_rejects_duplicate_names():
    registry = AgentRegistry().register(EchoAgent())
    try:
        registry.register(EchoAgent())
    except ValueError:
        pass
    else:
        raise AssertionError("Expected duplicate registration to raise.")


def test_orchestrator_dispatches_tool_call_then_finishes():
    registry = AgentRegistry().register(EchoAgent())
    provider = ScriptedProvider(
        [
            LLMResponse(
                text="",
                tool_calls=[
                    ToolCall(id="1", name="echo", arguments={"text": "hi"})
                ],
            ),
            LLMResponse(text="Done: echoed hi", tool_calls=[]),
        ]
    )
    orch = Orchestrator(provider=provider, registry=registry)
    result = orch.handle("please echo hi")

    assert result.final_text == "Done: echoed hi"
    assert len(result.tool_invocations) == 1
    inv = result.tool_invocations[0]
    assert inv["tool"] == "echo"
    assert inv["ok"] is True
    assert inv["summary"] == "echo: hi"


def test_orchestrator_handles_unknown_tool():
    registry = AgentRegistry().register(EchoAgent())
    provider = ScriptedProvider(
        [
            LLMResponse(
                text="",
                tool_calls=[ToolCall(id="1", name="nope", arguments={})],
            ),
            LLMResponse(text="handled", tool_calls=[]),
        ]
    )
    orch = Orchestrator(provider=provider, registry=registry)
    result = orch.handle("call a missing tool")
    assert result.tool_invocations[0]["ok"] is False
