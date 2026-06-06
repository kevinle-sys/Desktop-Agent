"""Crew assembly and execution.

Two run modes:
- ``run_crew``: a hierarchical crew where a manager agent plans and delegates
  across all specialists.
- ``run_specialist``: a single specialist agent handling a task directly, using
  its own tools and reasoning.
"""

from __future__ import annotations

from typing import List, Optional

from .agents import build_manager, build_specialists, specialist_agents
from .config.settings import Settings, get_settings
from .knowledge import build_embedder, shared_sources
from .utils.logging import get_logger

logger = get_logger(__name__)

_FINAL_OUTPUT = (
    "A concise, accurate, trader-friendly answer summarizing what was done and "
    "the key results (numbers, file paths, model outputs, or macro status)."
)


def available_specialists() -> List[str]:
    """Return the specialist keys without constructing LLM-backed agents."""
    return ["data_analyst", "excel_modeler", "automation_engineer"]


def _knowledge_kwargs(settings: Settings) -> dict:
    """Crew kwargs for shared knowledge + embedder, when knowledge is available."""
    kwargs: dict = {}
    embedder = build_embedder(settings)
    if embedder is None:
        return kwargs
    sources = shared_sources(settings)
    if sources:
        kwargs["knowledge_sources"] = sources
    kwargs["embedder"] = embedder
    return kwargs


def build_hierarchical_crew(prompt: str, settings: Optional[Settings] = None):
    """Assemble a hierarchical crew (manager + all specialists) for one prompt."""
    from crewai import Crew, Process, Task

    settings = settings or get_settings()
    specialists = build_specialists(settings)
    manager = build_manager(settings)

    task = Task(
        description=prompt,
        expected_output=_FINAL_OUTPUT,
        # No agent assigned: the manager decides who handles it.
    )
    crew_kwargs = _knowledge_kwargs(settings)
    return Crew(
        agents=specialist_agents(specialists),
        tasks=[task],
        process=Process.hierarchical,
        manager_agent=manager,
        verbose=settings.crew_verbose,
        **crew_kwargs,
    )


def build_specialist_crew(
    specialist_key: str, prompt: str, settings: Optional[Settings] = None
):
    """Assemble a single-specialist sequential crew for one prompt."""
    from crewai import Crew, Process, Task

    settings = settings or get_settings()
    specialists = build_specialists(settings)
    if specialist_key not in specialists:
        raise KeyError(
            f"Unknown specialist '{specialist_key}'. Available: "
            f"{list(specialists)}"
        )
    specialist = specialists[specialist_key]
    task = Task(
        description=prompt,
        expected_output=_FINAL_OUTPUT,
        agent=specialist.agent,
    )
    crew_kwargs = _knowledge_kwargs(settings)
    return Crew(
        agents=[specialist.agent],
        tasks=[task],
        process=Process.sequential,
        verbose=settings.crew_verbose,
        **crew_kwargs,
    )


def run_crew(prompt: str, settings: Optional[Settings] = None) -> str:
    """Run the hierarchical, manager-led crew and return the final answer."""
    crew = build_hierarchical_crew(prompt, settings)
    return str(crew.kickoff())


def run_specialist(
    specialist_key: str, prompt: str, settings: Optional[Settings] = None
) -> str:
    """Run a single specialist directly and return its final answer."""
    crew = build_specialist_crew(specialist_key, prompt, settings)
    return str(crew.kickoff())
