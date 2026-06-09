# Workflows

Step-by-step guides for extending the agents' repertoire. The most common
changes a trader will make, plus how to add new MCP tools and subagents.

---

## A. Add a new SQL query

Both data agents load named, parameterized queries from disk — a drop-in
operation with no Python changes. Templates are organized **by engine** because
the dialects use different bind-parameter syntax:

| Engine | Folder | Agent / tool | Param style | Row cap |
|--------|--------|--------------|-------------|---------|
| Snowflake | `sql/snowflake/` | `snowflake_query` | `%(name)s` | `LIMIT %(row_limit)s` |
| SQL Server | `sql/sqlserver/` | `sqlserver_query` | `:name` | `TOP (:row_limit)` |

### Snowflake example
1. **Create the file** under `sql/snowflake/`, e.g.
   `sql/snowflake/locked_loans_by_product.sql`.
2. **Use `%(name)s` bind parameters** so values pass safely:

```sql
-- sql/snowflake/locked_loans_by_product.sql
SELECT loan_id, note_rate, upb, lock_date, product
FROM   secondary.locks
WHERE  product = %(product)s
  AND  lock_date >= %(start_date)s
ORDER  BY lock_date DESC
LIMIT  %(row_limit)s;
```

3. **Invoke it**: *"Run locked_loans_by_product for FN30 since 2026-01-01,
   top 50."* → `snowflake_query` with `query_name="locked_loans_by_product"`
   and the parameter dict.

### SQL Server example
1. **Create the file** under `sql/sqlserver/`, e.g.
   `sql/sqlserver/locked_loans_by_product.sql`.
2. **Use `:name` bind parameters and T-SQL `TOP`** (no `LIMIT`):

```sql
-- sql/sqlserver/locked_loans_by_product.sql
SELECT TOP (:row_limit)
       loan_id, note_rate, upb, lock_date, product
FROM   dbo.locks
WHERE  product = :product
  AND  lock_date >= :start_date
ORDER  BY lock_date DESC;
```

3. **Invoke it**: *"Pull locked loans for FN30 from SQL Server."* →
   `sqlserver_query` with `query_name="locked_loans_by_product"` and params.

> Routing tip: the Data Analyst agent prefers Snowflake when the data is
> available there and uses SQL Server for sources not yet migrated (or when you
> ask for SQL Server explicitly).

4. (Optional) **Inline SQL** is supported on both agents via the `sql`
   argument, subject to the read-only guardrail.

> Guardrail: both SQL tools reject `DROP`/`DELETE`/`TRUNCATE`/`UPDATE`/`INSERT`/
> `EXEC` by default. See `assert_read_only` in
> `src/pennymac_agent/tools/_sql_common.py`.

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
   back price and OAS."* The Pricing Model Engineer calls the `excel_model`
   tool with `model_name="fn30_pricing"`, `inputs={...}`, `outputs=["price","oas"]`.
5. **Chained from a query**: the SQL tools save a CSV to `ARTIFACTS_DIR`; pass
   that path as `data_file` and the tool pushes matching columns from the first
   row into the model.

> The `excel_model` tool uses `xlwings` when Excel is available (so formulas
> recalculate live) and falls back to `openpyxl` for headless read/write.

---

## C. Integrate a new VBA script

The Automation Engineer can both **trigger existing macros** and **generate
new ones**.

### Trigger an existing macro
1. Ensure the macro lives in a workbook that is registered in
   `models/registry.yaml` under that model's `macros:` list.
2. Ask: *"Run the BatchPrice macro in fn30_pricing."* The agent calls the
   `run_vba_macro` tool with `model_name="fn30_pricing"`,
   `macro_name="BatchPrice"`, and optional `args`.

### Generate a new VBA script
1. Ask the agent to author a macro, e.g. *"Generate a VBA macro that exports
   the Outputs sheet to a timestamped CSV."*
2. The agent calls the `generate_vba` tool, which writes a `.bas` file into
   `VBA_SCRIPTS_DIR` (default `vba/`), e.g. `vba/ExportOutputsToCsv.bas`.
3. **Import it into Excel** (one-time): in Excel press `Alt+F11` → File →
   Import File → select the generated `.bas`. After import it can be triggered
   like any other macro (see above). Automated import is a documented extension
   point in `src/pennymac_agent/tools/vba_tool.py`.

---

## D. Add a new tool (capability)

1. Write a plain function in `src/pennymac_agent/tools/` (e.g. `my_tool.py`)
   with typed parameters and a clear docstring (FastMCP builds the tool schema
   from these). Return a concise string; persist large data to `ARTIFACTS_DIR`.
2. Export it from `src/pennymac_agent/tools/__init__.py`.
3. Register it in [src/pennymac_agent/mcp_server.py](src/pennymac_agent/mcp_server.py)
   by adding it to the registration loop (`mcp.tool()(my_tool)`).
4. Restart the MCP server in Cursor (or reload) so the new tool is exposed.

## E. Add a new specialist subagent

1. Create a new `.cursor/agents/<name>.md` with frontmatter (`name`,
   `description`, optionally `model`/`readonly`) and a system-prompt body telling
   it which MCP tools to use and the conventions to follow.
2. Reference it from [.cursor/agents/orchestrator.md](.cursor/agents/orchestrator.md)
   so the orchestrator can delegate to it.
3. It's available immediately in Cursor (no code change) — by mention or via the
   orchestrator's Task delegation.

---

## F. Give an agent more context (knowledge + discovery)

You can add reference material the agents evaluate - data dictionaries, model
methodology, runbooks, policies - with no code changes.

### Reference documents (`knowledge/`)
1. Drop a `.md`, `.txt`, `.csv`, `.sql`, `.json`, or `.yaml` file anywhere under
   `knowledge/` (suggested folders: `shared/`, `data_analyst/`, `excel_modeler/`,
   `automation_engineer/`, `legacy_queries/`).
2. Agents read them via the `list_documents` and `read_document` tools (verbatim,
   100% local - nothing is sent to an embedding service).
3. Picked up on the next call - no restart needed. You can also point a
   subagent's system prompt (`.cursor/agents/<name>.md`) at a specific doc.

### Live resources the agents can already evaluate
- **SQL templates**: `list_sql_queries` reports every query in `sql/snowflake/`
  and `sql/sqlserver/` with its header comment. Add a query (section A) and it
  shows up.
- **Excel models**: `describe_excel_models` reports each registered model's
  inputs, outputs, and macros. Register a model (section B) and it shows up.

---

## Quick reference

| I want to... | Edit | Then ask... |
|--------------|------|-------------|
| Add a Snowflake query | new file in `sql/snowflake/` | "Run `<name>` with ..." |
| Add a SQL Server query | new file in `sql/sqlserver/` | "Run `<name>` from SQL Server ..." |
| Point a model at a new file | `models/registry.yaml` `path:` | (no change) |
| Map new model cells | `models/registry.yaml` `inputs/outputs` | "Push ... read back ..." |
| Run an existing macro | `macros:` list in registry | "Run the `<Macro>` macro" |
| Create a macro | (none) | "Generate a VBA macro that ..." |
| Add reference context | file in `knowledge/...` | (read via `read_document`) |
| Add a tool | function in `tools/` + register in `mcp_server.py` | (restart MCP server) |
| Add a subagent | new `.cursor/agents/<name>.md` | mention it / via orchestrator |
