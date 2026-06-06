"""Crew/agent wiring tests that build objects but never call kickoff().

A dummy API key is set so agent/LLM construction succeeds without any network
call (kickoff is what would hit the provider, and we never call it).
"""

from pennymac_agent.agents import build_manager, build_specialists
from pennymac_agent.config.settings import Settings
from pennymac_agent.crew import (
    available_specialists,
    build_hierarchical_crew,
    build_specialist_crew,
)


def _settings() -> Settings:
    # Knowledge disabled so the test isolates tool/agent wiring (no embeddings).
    return Settings(
        LLM_PROVIDER="openai",
        OPENAI_API_KEY="sk-test-not-real",
        ENABLE_KNOWLEDGE=False,
    )


def _tool_names(agent) -> set:
    return {t.name for t in getattr(agent, "tools", [])}


def test_specialists_built_with_expected_tools():
    specialists = build_specialists(_settings())
    assert set(specialists) == {
        "data_analyst",
        "excel_modeler",
        "automation_engineer",
    }
    # Data + discovery + doc tools.
    assert {"snowflake_query", "sqlserver_query", "list_sql_queries"} <= _tool_names(
        specialists["data_analyst"].agent
    )
    assert {"excel_model", "describe_excel_models"} <= _tool_names(
        specialists["excel_modeler"].agent
    )
    assert {"run_vba_macro", "generate_vba", "describe_excel_models"} <= _tool_names(
        specialists["automation_engineer"].agent
    )
    # Every specialist can read reference documents.
    for s in specialists.values():
        assert {"list_documents", "read_document"} <= _tool_names(s.agent)


def test_specialists_do_not_delegate():
    specialists = build_specialists(_settings())
    for s in specialists.values():
        assert s.agent.allow_delegation is False


def test_manager_can_delegate():
    manager = build_manager(_settings())
    assert manager.allow_delegation is True


def test_available_specialists_list():
    assert available_specialists() == [
        "data_analyst",
        "excel_modeler",
        "automation_engineer",
    ]


def test_hierarchical_crew_wiring():
    crew = build_hierarchical_crew("test prompt", _settings())
    assert len(crew.agents) == 3
    assert crew.manager_agent is not None
    assert len(crew.tasks) == 1


def test_specialist_crew_wiring():
    crew = build_specialist_crew("excel_modeler", "test prompt", _settings())
    assert len(crew.agents) == 1
    assert len(crew.tasks) == 1
