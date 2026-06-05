"""VBA / Process Agent.

Two responsibilities:
1. Trigger an existing VBA macro inside a registered workbook (via xlwings/COM).
2. Generate a new VBA macro and save it as a ``.bas`` file in the scripts dir.

See WORKFLOWS.md, section C for end-to-end usage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

import yaml

from ..config.settings import Settings, get_settings
from ..utils.logging import get_logger
from .base_agent import AgentResult, BaseAgent

logger = get_logger(__name__)


class VBAProcessAgent(BaseAgent):
    name = "vba_process"
    description = (
        "Automate Excel via VBA. Use action='run_macro' to trigger an existing "
        "macro (by name) inside a registered workbook, or action='generate' to "
        "author a new VBA macro and save it as a .bas file for the trader to "
        "import. Good for batch pricing, refreshing data, or exporting reports."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["run_macro", "generate"],
                "description": "Whether to run an existing macro or create one.",
            },
            "model_name": {
                "type": "string",
                "description": (
                    "For run_macro: logical model key whose workbook hosts the "
                    "macro (from models/registry.yaml)."
                ),
            },
            "macro_name": {
                "type": "string",
                "description": "Name of the VBA macro/Sub to run or generate.",
            },
            "args": {
                "type": "array",
                "description": "Positional arguments to pass to the macro.",
                "items": {},
            },
            "vba_code": {
                "type": "string",
                "description": (
                    "For generate: the full VBA source (Sub ... End Sub) to "
                    "write to <macro_name>.bas."
                ),
            },
        },
        "required": ["action"],
        "additionalProperties": False,
    }

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    # --- registry helper ------------------------------------------------------
    def _resolve_workbook(self, model_name: str) -> Path:
        path = self.settings.model_registry_path
        if not path.exists():
            raise FileNotFoundError(f"Model registry not found at {path}")
        models = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get(
            "models", {}
        )
        if model_name not in models:
            raise KeyError(
                f"Model '{model_name}' is not registered. Known: {list(models)}"
            )
        raw_path = Path(models[model_name]["path"])
        if not raw_path.is_absolute():
            raw_path = self.settings.excel_models_dir / raw_path.name
        return raw_path

    # --- actions --------------------------------------------------------------
    def _run_macro(
        self, model_name: str, macro_name: str, args: List[Any]
    ) -> AgentResult:
        if not model_name or not macro_name:
            return AgentResult.failure(
                "run_macro requires both 'model_name' and 'macro_name'."
            )
        try:
            wb_path = self._resolve_workbook(model_name)
        except (FileNotFoundError, KeyError) as exc:
            return AgentResult.failure(str(exc))
        if not wb_path.exists():
            return AgentResult.failure(f"Workbook not found at {wb_path}.")

        try:
            import xlwings as xw

            app = xw.App(visible=self.settings.excel_visible, add_book=False)
            try:
                book = app.books.open(str(wb_path))
                macro = book.macro(macro_name)
                result = macro(*args) if args else macro()
                book.save()
            finally:
                app.quit()
        except ImportError:
            return AgentResult.failure(
                "xlwings is required to run macros but is not available."
            )
        except Exception as exc:  # pragma: no cover - depends on local Excel
            logger.exception("Macro execution failed")
            return AgentResult.failure(f"Macro '{macro_name}' failed: {exc}")

        return AgentResult.success(
            f"Ran macro '{macro_name}' in {wb_path.name}. Return: {result!r}",
            data=result,
            macro=macro_name,
        )

    def _generate(self, macro_name: str, vba_code: str) -> AgentResult:
        if not macro_name or not vba_code:
            return AgentResult.failure(
                "generate requires both 'macro_name' and 'vba_code'."
            )
        scripts_dir = self.settings.vba_scripts_dir
        scripts_dir.mkdir(parents=True, exist_ok=True)
        out_path = scripts_dir / f"{Path(macro_name).name}.bas"
        out_path.write_text(vba_code, encoding="utf-8")
        # TODO (extension point): auto-import the .bas into a target workbook's
        # VBProject via xlwings/COM (requires "Trust access to the VBA project
        # object model" enabled in Excel Trust Center).
        return AgentResult.success(
            f"Wrote VBA macro to {out_path}. Import via Alt+F11 -> File -> "
            "Import File to make it runnable.",
            data=str(out_path),
            path=str(out_path),
        )

    # --- main entrypoint ------------------------------------------------------
    def run(  # type: ignore[override]
        self,
        action: str,
        model_name: Optional[str] = None,
        macro_name: Optional[str] = None,
        args: Optional[List[Any]] = None,
        vba_code: Optional[str] = None,
        **_: Any,
    ) -> AgentResult:
        if action == "run_macro":
            return self._run_macro(model_name or "", macro_name or "", args or [])
        if action == "generate":
            return self._generate(macro_name or "", vba_code or "")
        return AgentResult.failure(
            f"Unknown action '{action}'. Use 'run_macro' or 'generate'."
        )
