"""CrewAI specialist and manager agents for the trading desk.

Each specialist is an autonomous, reasoning agent that owns a set of tools and
decides on its own how to accomplish a task once prompted. The manager agent is
used in the hierarchical crew to plan and delegate across specialists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .config.settings import Settings, get_settings
from .knowledge import agent_sources
from .llm import build_llm, build_manager_llm
from .tools import (
    DescribeExcelModelsTool,
    ExcelModelTool,
    GenerateVBATool,
    ListDocumentsTool,
    ListSQLQueriesTool,
    ReadDocumentTool,
    RunMacroTool,
    SnowflakeQueryTool,
    SQLServerQueryTool,
)


def _doc_tools(settings: Settings) -> list:
    """Reference-document tools available to every specialist."""
    return [ListDocumentsTool(settings=settings), ReadDocumentTool(settings=settings)]


@dataclass
class Specialist:
    """A named specialist agent plus the human-facing summary of its remit."""

    key: str
    title: str
    agent: object  # crewai.Agent


def _agent(settings: Settings, knowledge_key: str, **kwargs):
    from crewai import Agent

    sources = agent_sources(knowledge_key, settings)
    if sources:
        kwargs["knowledge_sources"] = sources
    return Agent(
        llm=build_llm(settings),
        allow_delegation=False,
        verbose=settings.crew_verbose,
        max_iter=settings.agent_max_iter,
        **kwargs,
    )


def build_specialists(settings: Optional[Settings] = None) -> Dict[str, Specialist]:
    """Build the specialist agents, keyed by a short CLI-friendly name."""
    settings = settings or get_settings()

    data_analyst = _agent(
        settings,
        "data_analyst",
        role="Secondary Market Data Analyst",
        goal=(
            "Pull accurate loan and pricing data for the trading desk, choosing "
            "Snowflake when the data is available there and SQL Server for "
            "sources not yet migrated. Always use read-only queries."
        ),
        backstory=(
            "You are a meticulous mortgage capital-markets analyst who lives in "
            "SQL. You know the desk is migrating from SQL Server to Snowflake, "
            "so you prefer Snowflake but fall back to SQL Server when needed. "
            "You never guess numbers; you query for them and cite row counts. "
            "You consult the data dictionary and the named-query library before "
            "writing SQL. A large set of UNVALIDATED legacy queries is available "
            "under legacy_queries/ (via list_documents/read_document) for "
            "table/column hints and patterns - never run them verbatim; adapt "
            "and verify first."
        ),
        tools=[
            SnowflakeQueryTool(settings=settings),
            SQLServerQueryTool(settings=settings),
            ListSQLQueriesTool(settings=settings),
            *_doc_tools(settings),
        ],
    )

    excel_modeler = _agent(
        settings,
        "excel_modeler",
        role="Pricing Model Engineer",
        goal=(
            "Push inputs into the desk's Excel pricing models, recalculate, and "
            "extract results like price, OAS, and duration accurately."
        ),
        backstory=(
            "You are an Excel power user who maintains the desk's pricing "
            "workbooks. You know the model registry maps logical names to "
            "workbooks and cells, and you can load inputs from data files "
            "produced by the analyst. You check describe_excel_models before "
            "driving a model."
        ),
        tools=[
            ExcelModelTool(settings=settings),
            DescribeExcelModelsTool(settings=settings),
            *_doc_tools(settings),
        ],
    )

    automation_engineer = _agent(
        settings,
        "automation_engineer",
        role="Process Automation Engineer",
        goal=(
            "Automate repetitive desk workflows by running existing Excel VBA "
            "macros or authoring new ones to save the trader time."
        ),
        backstory=(
            "You are a VBA specialist who has automated countless pricing and "
            "reporting chores. You can trigger existing macros or write new, "
            "well-structured ones for the trader to import. You consult the "
            "model registry to find which macros a workbook exposes."
        ),
        tools=[
            RunMacroTool(settings=settings),
            GenerateVBATool(settings=settings),
            DescribeExcelModelsTool(settings=settings),
            *_doc_tools(settings),
        ],
    )

    return {
        "data_analyst": Specialist(
            "data_analyst", "Secondary Market Data Analyst", data_analyst
        ),
        "excel_modeler": Specialist(
            "excel_modeler", "Pricing Model Engineer", excel_modeler
        ),
        "automation_engineer": Specialist(
            "automation_engineer", "Process Automation Engineer", automation_engineer
        ),
    }


def build_manager(settings: Optional[Settings] = None):
    """Build the manager agent for the hierarchical crew."""
    from crewai import Agent

    settings = settings or get_settings()
    return Agent(
        role="Trading Desk Chief of Staff",
        goal=(
            "Understand the trader's request, break it into steps, and delegate "
            "each step to the best specialist (data, Excel modeling, or VBA "
            "automation). Validate results and produce a concise, accurate, "
            "trader-friendly final answer."
        ),
        backstory=(
            "You coordinate a small team of expert agents for a PennyMac "
            "Secondary Market trader. You plan the work, delegate, review "
            "outputs for correctness, and never fabricate data."
        ),
        llm=build_manager_llm(settings),
        allow_delegation=True,
        verbose=settings.crew_verbose,
    )


def specialist_agents(specialists: Dict[str, Specialist]) -> List[object]:
    """Return the underlying crewai.Agent objects from a specialist mapping."""
    return [s.agent for s in specialists.values()]
