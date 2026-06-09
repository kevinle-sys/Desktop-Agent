"""Discovery tools (plain functions): list SQL queries, describe Excel models."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from ..config.settings import get_settings


def _leading_comment(sql_text: str, max_lines: int = 5) -> str:
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


def _list_dir(label: str, sql_dir: Path) -> str:
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


def list_sql_queries(engine: str = "all") -> str:
    """List named SQL query templates with a short description of each.

    Use this to discover what queries exist before running one by name with
    snowflake_query or sqlserver_query.

    Args:
        engine: Which library to list: 'snowflake', 'sqlserver', or 'all'.
    """
    s = get_settings()
    blocks = []
    if engine in ("all", "snowflake"):
        blocks.append(_list_dir("snowflake", s.sql_dir))
    if engine in ("all", "sqlserver"):
        blocks.append(_list_dir("sqlserver", s.sql_server_dir))
    if not blocks:
        return f"Unknown engine '{engine}'. Use snowflake, sqlserver, or all."
    return "\n\n".join(blocks)


def describe_excel_models(model_name: Optional[str] = None) -> str:
    """Describe registered Excel pricing models: inputs, outputs, and macros.

    Use this to learn what models exist and how to drive them before calling
    excel_model or run_vba_macro.

    Args:
        model_name: Describe one model by name; omit to list all.
    """
    s = get_settings()
    path = s.model_registry_path
    if not path.exists():
        return f"Error: model registry not found at {path}."
    models = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("models", {})
    if not models:
        return "No Excel models are registered."
    if model_name:
        if model_name not in models:
            return f"Model '{model_name}' is not registered. Known: {list(models)}"
        models = {model_name: models[model_name]}
    out = []
    for name, spec in models.items():
        inputs = list((spec.get("inputs") or {}).keys())
        outputs = list((spec.get("outputs") or {}).keys())
        macros = spec.get("macros") or []
        out.append(f"- {name}: inputs={inputs}, outputs={outputs}, macros={macros}")
    return "Registered Excel models:\n" + "\n".join(out)
