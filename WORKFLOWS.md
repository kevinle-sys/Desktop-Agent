# Workflows

Step-by-step guides for extending the agent's repertoire. These are the three
most common changes a trader will make.

---

## A. Add a new SQL query

The Snowflake agent loads named, parameterized queries from the `sql/`
directory. Adding a query is a drop-in operation — no Python changes required.

1. **Create the file** under `sql/`, named after the query, e.g.
   `sql/locked_loans_by_product.sql`.
2. **Use named bind parameters** with `%(name)s` style so values are passed
   safely (never string-formatted):

```sql
-- sql/locked_loans_by_product.sql
-- Locked loans for a given agency product, most recent lock first.
SELECT loan_id,
       note_rate,
       upb,
       lock_date,
       product
FROM   secondary.locks
WHERE  product = %(product)s
  AND  lock_date >= %(start_date)s
ORDER  BY lock_date DESC
LIMIT  %(row_limit)s;
```

3. **Invoke it** by asking the agent naturally, e.g.
   *"Run locked_loans_by_product for FN30 since 2026-01-01, top 50."*
   The LLM maps this to a `snowflake_query` tool call with
   `query_name="locked_loans_by_product"` and the parameter dict.

4. (Optional) **Inline SQL** is also supported for ad-hoc analysis via the
   `sql` argument, subject to the read-only guardrail.

> Guardrail: the agent rejects `DROP`/`DELETE`/`TRUNCATE`/`UPDATE`/`INSERT` by
> default. See `agents/snowflake_agent.py` (`_assert_read_only`).

---

## B. Register or update an Excel model path

Excel models are referenced by a **logical name** in `models/registry.yaml`, so
file paths and cell mappings live in config — not in code.

1. **Place the workbook** in your models directory (default
   `models/workbooks/`, configurable via `EXCEL_MODELS_DIR`).
2. **Register it** in `models/registry.yaml`:

```yaml
models:
  fn30_pricing:
    path: workbooks/FN30_Pricing_Model.xlsm
    sheet: Inputs
    # Map a friendly input key -> target cell / named range.
    inputs:
      coupon:        Inputs!C4
      upb:           Inputs!C5
      settle_date:   Inputs!C6
    # Map a friendly output key -> source cell / named range to read back.
    outputs:
      price:         Outputs!B2
      oas:           Outputs!B3
      duration:      Outputs!B4
    # Optional: macros this workbook exposes (used by the VBA agent).
    macros:
      - BatchPrice
      - RefreshMarketData
```

3. **Update a path** by editing the `path:` value — no redeploy needed.
4. **Use it**: *"Push coupon 5.5 and UPB 1,000,000 into fn30_pricing and read
   back price and OAS."* → `excel_model` tool call with
   `model_name="fn30_pricing"`, `inputs={...}`, `outputs=["price","oas"]`.

> The Excel agent uses `xlwings` when Excel is available (so formulas
> recalculate live) and falls back to `openpyxl` for headless read/write.

---

## C. Integrate a new VBA script

The VBA agent can both **trigger existing macros** and **generate new ones**.

### Trigger an existing macro
1. Ensure the macro lives in a workbook that is registered in
   `models/registry.yaml` under that model's `macros:` list.
2. Ask: *"Run the BatchPrice macro in fn30_pricing."* →
   `vba_macro` tool call with `model_name="fn30_pricing"`,
   `macro_name="BatchPrice"`, and optional `args`.

### Generate a new VBA script
1. Ask the agent to author a macro, e.g. *"Generate a VBA macro that exports
   the Outputs sheet to a timestamped CSV."*
2. The agent writes a `.bas` file into `VBA_SCRIPTS_DIR` (default `vba/`), e.g.
   `vba/ExportOutputsToCsv.bas`.
3. **Import it into Excel** (one-time): in Excel press `Alt+F11` → File →
   Import File → select the generated `.bas`. After import it can be triggered
   like any other macro (see above). Automated import is a documented extension
   point in `agents/vba_agent.py`.

---

## D. Add a brand-new sub-agent (advanced)

1. Create `src/pennymac_agent/agents/my_agent.py` subclassing `BaseAgent`;
   define `name`, `description`, `parameters` (JSON Schema), and `run()`.
2. Register it in `orchestrator` setup (where the other three agents are added
   to the registry).
3. It is automatically advertised to the LLM as a tool by `router.py` — no
   prompt edits required.

---

## Quick reference

| I want to... | Edit | Then ask... |
|--------------|------|-------------|
| Add a SQL query | new file in `sql/` | "Run `<name>` with ..." |
| Point a model at a new file | `models/registry.yaml` `path:` | (no change) |
| Map new model cells | `models/registry.yaml` `inputs/outputs` | "Push ... read back ..." |
| Run an existing macro | `macros:` list in registry | "Run the `<Macro>` macro" |
| Create a macro | (none) | "Generate a VBA macro that ..." |
