"""CrewAI tool: drive a registered Excel pricing model (push inputs, read outputs)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import yaml
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..config.settings import Settings, get_settings
from ..utils.logging import get_logger

logger = get_logger(__name__)


class ExcelModelInput(BaseModel):
    model_name: str = Field(
        ..., description="Logical model key from models/registry.yaml."
    )
    inputs: Optional[Dict[str, Any]] = Field(
        None,
        description="Map of friendly input keys to values, e.g. {'coupon': 5.5}.",
    )
    outputs: Optional[List[str]] = Field(
        None,
        description="Friendly output keys to read back; omit to read all.",
    )
    data_file: Optional[str] = Field(
        None,
        description=(
            "Optional path to a CSV (e.g. produced by a SQL tool). When given "
            "and 'inputs' is omitted, the first row's columns that match the "
            "model's input keys are pushed into the model."
        ),
    )
    engine: str = Field(
        "auto", description="Calc engine: 'auto', 'xlwings', or 'openpyxl'."
    )


class ExcelModelTool(BaseTool):
    name: str = "excel_model"
    description: str = (
        "Drive a complex Excel pricing-model workbook: push input values into a "
        "registered model, trigger recalculation, and read back calculated "
        "outputs (price, OAS, duration, ...). Reference the model by its logical "
        "name from models/registry.yaml. Can also load inputs from a CSV file "
        "produced by a data tool via 'data_file'."
    )
    args_schema: Type[BaseModel] = ExcelModelInput
    settings: Optional[Settings] = None

    # --- registry -------------------------------------------------------------
    def _resolve_model(self, s: Settings, model_name: str) -> Dict[str, Any]:
        path = s.model_registry_path
        if not path.exists():
            raise FileNotFoundError(f"Model registry not found at {path}")
        models = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get(
            "models", {}
        )
        if model_name not in models:
            raise KeyError(
                f"Model '{model_name}' is not registered. Known models: "
                f"{list(models)}"
            )
        spec = dict(models[model_name])
        raw_path = Path(spec["path"])
        if not raw_path.is_absolute():
            raw_path = s.excel_models_dir / raw_path.name
        spec["_resolved_path"] = raw_path
        return spec

    @staticmethod
    def _inputs_from_csv(data_file: str, input_map: Dict[str, str]) -> Dict[str, Any]:
        import pandas as pd

        df = pd.read_csv(data_file)
        if df.empty:
            return {}
        row = df.iloc[0].to_dict()
        return {k: row[k] for k in input_map if k in row}

    # --- engines --------------------------------------------------------------
    def _run_xlwings(self, s, wb_path, input_map, inputs, output_map, wanted):
        import xlwings as xw

        app = xw.App(visible=s.excel_visible, add_book=False)
        try:
            book = app.books.open(str(wb_path))
            for key, value in inputs.items():
                if key not in input_map:
                    raise KeyError(f"Input '{key}' not mapped for this model.")
                book.range(input_map[key]).value = value
            app.calculate()
            results: Dict[str, Any] = {}
            for key in wanted:
                if key not in output_map:
                    raise KeyError(f"Output '{key}' not mapped for this model.")
                results[key] = book.range(output_map[key]).value
            book.save()
            return results
        finally:
            app.quit()

    def _run_openpyxl(self, wb_path, input_map, inputs, output_map, wanted):
        from openpyxl import load_workbook

        wb = load_workbook(wb_path, data_only=False)
        for key, value in inputs.items():
            if key not in input_map:
                raise KeyError(f"Input '{key}' not mapped for this model.")
            sheet_name, cell = _split_ref(input_map[key])
            wb[sheet_name][cell] = value
        wb.save(wb_path)

        cached = load_workbook(wb_path, data_only=True)
        results: Dict[str, Any] = {}
        for key in wanted:
            if key not in output_map:
                raise KeyError(f"Output '{key}' not mapped for this model.")
            sheet_name, cell = _split_ref(output_map[key])
            results[key] = cached[sheet_name][cell].value
        return results

    # --- main entrypoint ------------------------------------------------------
    def _run(
        self,
        model_name: str,
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[List[str]] = None,
        data_file: Optional[str] = None,
        engine: str = "auto",
    ) -> str:
        s = self.settings or get_settings()
        try:
            spec = self._resolve_model(s, model_name)
        except (FileNotFoundError, KeyError) as exc:
            return f"Error: {exc}"

        wb_path: Path = spec["_resolved_path"]
        input_map: Dict[str, str] = spec.get("inputs", {})
        output_map: Dict[str, str] = spec.get("outputs", {})
        wanted = outputs if outputs is not None else list(output_map)

        if inputs is None and data_file:
            try:
                inputs = self._inputs_from_csv(data_file, input_map)
            except Exception as exc:
                return f"Error: could not read data_file '{data_file}': {exc}"
        inputs = inputs or {}

        if not wb_path.exists():
            return (
                f"Error: workbook for model '{model_name}' not found at "
                f"{wb_path}. Place the file there or update its registry path."
            )

        use_xlwings = engine in ("auto", "xlwings")
        try:
            if use_xlwings:
                try:
                    results = self._run_xlwings(
                        s, wb_path, input_map, inputs, output_map, wanted
                    )
                except ImportError:
                    if engine == "xlwings":
                        raise
                    logger.warning("xlwings unavailable; falling back to openpyxl")
                    results = self._run_openpyxl(
                        wb_path, input_map, inputs, output_map, wanted
                    )
            else:
                results = self._run_openpyxl(
                    wb_path, input_map, inputs, output_map, wanted
                )
        except Exception as exc:  # pragma: no cover - depends on local Excel
            logger.exception("Excel model run failed")
            return f"Error: Excel run failed: {exc}"

        return (
            f"Model '{model_name}': wrote {len(inputs)} input(s), read "
            f"{len(results)} output(s) -> {results}"
        )


def _split_ref(ref: str) -> tuple[str, str]:
    """Split a 'Sheet!A1' reference into (sheet, cell)."""
    if "!" not in ref:
        raise ValueError(f"Cell reference '{ref}' must be 'Sheet!Cell' form.")
    sheet, cell = ref.split("!", 1)
    return sheet, cell
