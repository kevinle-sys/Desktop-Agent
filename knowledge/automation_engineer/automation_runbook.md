# Automation runbook (Process Automation Engineer context)

Replace with your real macro inventory and standards.

## Existing macros (examples)
- `BatchPrice` (fn30_pricing): prices the whole batch loaded in the Inputs sheet.
- `RefreshMarketData` (fn30_pricing): pulls latest market data into the model.
- `ExportOutputsToCsv`: exports the Outputs sheet to a timestamped CSV.

## Standards for generated VBA
- One `Sub` per task; prefix names with the workflow (e.g. `Export...`).
- Avoid hard-coded paths; use `ThisWorkbook.Path`.
- Saved as `.bas` in the VBA scripts dir for the trader to import (Alt+F11).
