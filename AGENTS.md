# Agent guide - PennyMac Trading Desktop Agent

This project uses **Cursor Subagents** (in `.cursor/agents/`) as the reasoning
layer, backed by a local **MCP server** (`pennymac_agent.mcp_server`) that
exposes the desk's data, modeling, and automation tools. The subagents run on
your Cursor subscription - no external LLM API key is needed.

## Architecture
- Brains: `.cursor/agents/*.md` - `orchestrator`, `data-analyst`,
  `excel-modeler`, `automation-engineer`.
- Hands: MCP server defined in `src/pennymac_agent/mcp_server.py`, configured in
  `.cursor/mcp.json`. Tool logic lives in `src/pennymac_agent/tools/`.

## MCP tools
| Tool | Purpose |
|------|---------|
| `snowflake_query` | Read-only Snowflake SQL (`%(name)s` binds). |
| `sqlserver_query` | Read-only legacy SQL Server / `qrm_pulsar` T-SQL (`:name` binds, `TOP`). |
| `list_sql_queries` | Discover the named query library. |
| `excel_model` | Push inputs into a registered model, recalc, read outputs. |
| `describe_excel_models` | List model inputs/outputs/macros from the registry. |
| `run_vba_macro` | Trigger an existing VBA macro. |
| `generate_vba` | Author a new `.bas` macro. |
| `list_documents` / `read_document` | Read reference docs in `knowledge/`. |

## Conventions for agents
- Read-only data: the SQL tools reject `INSERT/UPDATE/DELETE/EXEC/...`. The
  `data-analyst` subagent is `readonly: true`.
- Source policy: prefer Snowflake; use SQL Server (`qrm_pulsar`) for un-migrated
  data or when a SQL Server object is named.
- SQL Server pipeline facts: view `qrm_pulsar.dbo.vw_Pipe`; lock date
  `[Lock Date]`; spec type `[SPP_Rule]`; loan size `[Original Loan Amount]`
  (thousands). "Yesterday" = most recent prior market day via
  `(SELECT MAX([Date]) FROM qrm_pulsar.dbo.hist_market WHERE [Date] < CAST(GETDATE() AS date))`.
- The Excel model registry (`models/registry.yaml`) is the source of truth for
  model names and cell mappings - confirm with `describe_excel_models`.
- `knowledge/legacy_queries/` holds ~260 UNVALIDATED historical queries for
  table/column hints only (git-ignored, local). Adapt and verify; never run
  verbatim.

## Setup
1. `pip install -r requirements.txt`
2. Fill `.env` (SQL Server is Windows/trusted by default; add Snowflake creds).
3. In Cursor, the `pennymac-trading` MCP server (`.cursor/mcp.json`) starts
   automatically; the subagents in `.cursor/agents/` are available via the Task
   tool or by mentioning them (e.g. ask the `orchestrator`).

## Validate the MCP server outside Cursor
```powershell
$env:PYTHONPATH="src"; python -c "from pennymac_agent.tools import sqlserver_query; print(sqlserver_query(sql='SELECT 1 AS ok'))"
```

See [README.md](README.md) and [ARCHITECTURE.md](ARCHITECTURE.md) for more.
