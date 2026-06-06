"""CrewAI tools that let agents discover available SQL queries and Excel models."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Type

import yaml
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..config.settings import Settings, get_settings


def _leading_comment(sql_text: str, max_lines: int = 5) -> str:
    """Return the leading `-- ...` comment block of a .sql file, if any."""
    lines = []
    for raw in sql_text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("--"):
            lines.append(stripped.lstrip("-").strip())
        elif stripped == "":
            if lines:
                break
        else:
            break
        if len(lines) >= max_lines:
            break
    return " ".join(lines) if lines else "(no description)"


class ListSQLQueriesInput(BaseModel):
    engine: str = Field(
        "all",
        description="Which library to list: 'snowflake', 'sqlserver', or 'all'.",
    )


class ListSQLQueriesTool(BaseTool):
    name: str = "list_sql_queries"
    description: str = (
        "List the named SQL query templates available to run, with a short "
        "description of each (from its header comment). Use this to discover "
        "what queries exist before running one by name."
    )
    args_schema: Type[BaseModel] = ListSQLQueriesInput
    settings: Optional[Settings] = None

    def _list_dir(self, label: str, sql_dir: Path) -> str:
        if not sql_dir.exists():
            return f"[{label}] directory not found ({sql_dir})."
        files = sorted(sql_dir.glob("*.sql"))
        if not files:
            return f"[{label}] no queries found."
        out = [f"[{label}] queries:"]
        for f in files:
            try:
                desc = _leading_comment(f.read_text(encoding="utf-8"))
            except Exception:
                desc = "(unreadable)"
            out.append(f"  - {f.stem}: {desc}")
        return "\n".join(out)

    def _run(self, engine: str = "all") -> str:
        s = self.settings or get_settings()
        blocks = []
        if engine in ("all", "snowflake"):
            blocks.append(self._list_dir("snowflake", s.sql_dir))
        if engine in ("all", "sqlserver"):
            blocks.append(self._list_dir("sqlserver", s.sql_server_dir))
        if not blocks:
            return f"Unknown engine '{engine}'. Use snowflake, sqlserver, or all."
        return "\n\n".join(blocks)


class DescribeExcelModelsInput(BaseModel):
    model_name: Optional[str] = Field(
        None,
        description="Describe one model by name; omit to list all registered models.",
    )


class DescribeExcelModelsTool(BaseTool):
    name: str = "describe_excel_models"
    description: str = (
        "Describe the Excel pricing models registered in models/registry.yaml: "
        "their input keys, output keys, and available macros. Use this to learn "
        "what models exist and how to drive them before calling excel_model."
    )
    args_schema: Type[BaseModel] = DescribeExcelModelsInput
    settings: Optional[Settings] = None

    def _run(self, model_name: Optional[str] = None) -> str:
        s = self.settings or get_settings()
        path = s.model_registry_path
        if not path.exists():
            return f"Error: model registry not found at {path}."
        models = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get(
            "models", {}
        )
        if not models:
            return "No Excel models are registered."
        if model_name:
            if model_name not in models:
                return (
                    f"Model '{model_name}' is not registered. Known: "
                    f"{list(models)}"
                )
            models = {model_name: models[model_name]}
        out = []
        for name, spec in models.items():
            inputs = list((spec.get("inputs") or {}).keys())
            outputs = list((spec.get("outputs") or {}).keys())
            macros = spec.get("macros") or []
            out.append(
                f"- {name}: inputs={inputs}, outputs={outputs}, macros={macros}"
            )
        return "Registered Excel models:\n" + "\n".join(out)
