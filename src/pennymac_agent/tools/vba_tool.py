"""CrewAI tools: run an existing Excel VBA macro, or generate a new .bas script."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional, Type

import yaml
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..config.settings import Settings, get_settings
from ..utils.logging import get_logger

logger = get_logger(__name__)


def _resolve_workbook(s: Settings, model_name: str) -> Path:
    path = s.model_registry_path
    if not path.exists():
        raise FileNotFoundError(f"Model registry not found at {path}")
    models = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get(
        "models", {}
    )
    if model_name not in models:
        raise KeyError(f"Model '{model_name}' is not registered. Known: {list(models)}")
    raw_path = Path(models[model_name]["path"])
    if not raw_path.is_absolute():
        raw_path = s.excel_models_dir / raw_path.name
    return raw_path


class RunMacroInput(BaseModel):
    model_name: str = Field(
        ..., description="Logical model key whose workbook hosts the macro."
    )
    macro_name: str = Field(..., description="Name of the VBA macro/Sub to run.")
    args: Optional[List[Any]] = Field(
        None, description="Positional arguments to pass to the macro."
    )


class RunMacroTool(BaseTool):
    name: str = "run_vba_macro"
    description: str = (
        "Trigger an existing VBA macro by name inside a registered workbook "
        "(via xlwings/COM). Use for batch pricing, refreshing market data, or "
        "exporting reports. Requires Excel installed."
    )
    args_schema: Type[BaseModel] = RunMacroInput
    settings: Optional[Settings] = None

    def _run(
        self,
        model_name: str,
        macro_name: str,
        args: Optional[List[Any]] = None,
    ) -> str:
        s = self.settings or get_settings()
        if not model_name or not macro_name:
            return "Error: run_vba_macro requires 'model_name' and 'macro_name'."
        try:
            wb_path = _resolve_workbook(s, model_name)
        except (FileNotFoundError, KeyError) as exc:
            return f"Error: {exc}"
        if not wb_path.exists():
            return f"Error: workbook not found at {wb_path}."

        args = args or []
        try:
            import xlwings as xw

            app = xw.App(visible=s.excel_visible, add_book=False)
            try:
                book = app.books.open(str(wb_path))
                macro = book.macro(macro_name)
                result = macro(*args) if args else macro()
                book.save()
            finally:
                app.quit()
        except ImportError:
            return "Error: xlwings is required to run macros but is not available."
        except Exception as exc:  # pragma: no cover - depends on local Excel
            logger.exception("Macro execution failed")
            return f"Error: macro '{macro_name}' failed: {exc}"

        return f"Ran macro '{macro_name}' in {wb_path.name}. Return: {result!r}"


class GenerateVBAInput(BaseModel):
    macro_name: str = Field(..., description="Name for the macro / output .bas file.")
    vba_code: str = Field(
        ..., description="Full VBA source (Sub ... End Sub) to write."
    )


class GenerateVBATool(BaseTool):
    name: str = "generate_vba"
    description: str = (
        "Author a new VBA macro and save it as a .bas file in the VBA scripts "
        "directory for the trader to import (Alt+F11 -> File -> Import File). "
        "Use when asked to create automation that does not yet exist."
    )
    args_schema: Type[BaseModel] = GenerateVBAInput
    settings: Optional[Settings] = None

    def _run(self, macro_name: str, vba_code: str) -> str:
        s = self.settings or get_settings()
        if not macro_name or not vba_code:
            return "Error: generate_vba requires 'macro_name' and 'vba_code'."
        scripts_dir = s.vba_scripts_dir
        scripts_dir.mkdir(parents=True, exist_ok=True)
        out_path = scripts_dir / f"{Path(macro_name).name}.bas"
        out_path.write_text(vba_code, encoding="utf-8")
        return (
            f"Wrote VBA macro to {out_path}. Import via Alt+F11 -> File -> "
            "Import File to make it runnable."
        )
