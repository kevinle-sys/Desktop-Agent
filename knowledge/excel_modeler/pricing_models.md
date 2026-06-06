# Pricing models (Pricing Model Engineer context)

Replace with your real model notes. Use `describe_excel_models` for the live
input/output/macro mappings from the registry.

## fn30_pricing (example)
- Purpose: price FN30 pools/loans.
- Inputs: `coupon`, `upb`, `settle_date`.
- Outputs: `price`, `oas`, `duration`.
- Macros: `BatchPrice`, `RefreshMarketData`.
- Notes: run `RefreshMarketData` before pricing if market data is stale.

## Conventions
- Always confirm the model name with `describe_excel_models` first.
- For chained workflows, the analyst saves query results to a CSV; pass that
  path as `data_file` to load inputs from the first row.
