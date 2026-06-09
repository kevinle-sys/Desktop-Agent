# PennyMac Trading Desktop Agent

A **Cursor Subagents + MCP** setup tailored to a PennyMac Secondary Market
Trader's daily workflows: querying loan/pricing data from Snowflake (and legacy
SQL Server during the migration), driving complex Excel pricing models, and
triggering/generating VBA automation.

The reasoning agents run **inside Cursor on your Cursor subscription** — no
external LLM API key or gateway required. They act through a local **MCP
server** that exposes the desk's data/Excel/VBA tools.

```text
You (in Cursor) ──▶ orchestrator subagent (plans + delegates)
                        ├──▶ data-analyst       → snowflake_query / sqlserver_query
                        ├──▶ excel-modeler      → excel_model
                        └──▶ automation-engineer → run_vba_macro / generate_vba
                                   (all tools served by the pennymac-trading MCP server)
```

## Two layers
- **Brains — Cursor Subagents** in [`.cursor/agents/`](.cursor/agents): `orchestrator`,
  `data-analyst`, `excel-modeler`, `automation-engineer`. They reason and
  delegate using your Cursor models.
- **Hands — MCP server** (`pennymac_agent.mcp_server`, configured in
  [`.cursor/mcp.json`](.cursor/mcp.json)) exposing read-only data tools, Excel
  model tools, VBA tools, and document/discovery tools. Logic lives in
  `src/pennymac_agent/tools/`.

See [AGENTS.md](AGENTS.md) for the agent/tool guide.

## MCP tools

| Tool | Purpose | Backed by |
|------|---------|-----------|
| `snowflake_query` | Read-only Snowflake SQL (`%(name)s` binds) | snowflake-connector, pandas |
| `sqlserver_query` | Read-only legacy SQL Server / `qrm_pulsar` T-SQL (`:name`, `TOP`) | pyodbc + SQLAlchemy, pandas |
| `list_sql_queries` | Discover the named query library | — |
| `excel_model` | Push inputs, recalc, read outputs of a registered model | xlwings / openpyxl |
| `describe_excel_models` | List model inputs/outputs/macros | — |
| `run_vba_macro` / `generate_vba` | Run an existing macro / author a `.bas` | xlwings (COM) |
| `list_documents` / `read_document` | Read reference docs in `knowledge/` | — |

> Both SQL tools are **read-only** (mutating statements are blocked). The
> `data-analyst` subagent is `readonly: true`.

## Project layout

```text
.
├── .cursor/
│   ├── agents/                  # Cursor subagents (the brains)
│   └── mcp.json                 # registers the pennymac-trading MCP server
├── AGENTS.md / README.md / ARCHITECTURE.md / WORKFLOWS.md
├── requirements.txt
├── .env.example                 # copy to .env and fill in
├── src/pennymac_agent/
│   ├── mcp_server.py            # FastMCP server (the hands)
│   ├── config/settings.py       # pydantic-settings, loads .env
│   ├── tools/                   # tool functions (snowflake/sqlserver/excel/vba/docs)
│   └── utils/logging.py
├── sql/snowflake/ , sql/sqlserver/   # reusable SQL templates, by engine
├── vba/                         # VBA scripts (existing + generated)
├── models/registry.yaml         # named Excel model paths + cell mappings
├── knowledge/                   # reference docs (read via tools); legacy_queries/ is local-only
├── artifacts/                   # query result CSVs for handoff (gitignored)
└── tests/
```

## Setup

### 1. Prerequisites
- **Python 3.11+** (developed on 3.13)
- **Microsoft Excel** + an **ODBC Driver for SQL Server** (e.g. "ODBC Driver 17
  for SQL Server"; set `SQL_SERVER_DRIVER` to match) for the SQL Server / Excel
  tools.
- Network/VPN to Snowflake and/or SQL Server.

### 2. Install
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Configure
```powershell
Copy-Item .env.example .env
# edit .env: SQL Server is Windows/trusted by default; add Snowflake creds.
```

### 4. Use it in Cursor
- Cursor reads [`.cursor/mcp.json`](.cursor/mcp.json) and starts the
  `pennymac-trading` MCP server automatically.
- The subagents in [`.cursor/agents/`](.cursor/agents) become available — ask
  the **orchestrator** for multi-step requests, or a specialist directly, e.g.:
  - "Ask the data-analyst to show yesterday's locks by spec type using vw_Pipe."
  - "Orchestrator: pull FN30 locks, price them in fn30_pricing, run BatchPrice."

### Validate the tools outside Cursor (optional)
```powershell
$env:PYTHONPATH="src"
python -c "from pennymac_agent.tools import sqlserver_query; print(sqlserver_query(sql='SELECT 1 AS ok'))"
```

## Required environment variables
See [`.env.example`](.env.example). Summary: Snowflake (`SNOWFLAKE_*`), SQL
Server (`SQL_SERVER_*` — Windows/trusted auth needs no password), Excel/VBA
paths (`EXCEL_MODELS_DIR`, `VBA_SCRIPTS_DIR`), and `ARTIFACTS_DIR`. **No LLM
keys** — reasoning runs on your Cursor account.

## Security notes
- `.env`, `artifacts/`, and `knowledge/legacy_queries/` are git-ignored. Never
  commit credentials or internal queries (this repo is public).
- Both data tools enforce **read-only** SQL.
- Prefer Snowflake key-pair/SSO and SQL Server Windows auth over passwords.

## Where to go next
- [AGENTS.md](AGENTS.md) — agent/tool guide and conventions.
- [ARCHITECTURE.md](ARCHITECTURE.md) — how subagents, the MCP server, and tools fit together.
- [WORKFLOWS.md](WORKFLOWS.md) — add a SQL query, register an Excel model, add a VBA script, add a tool or subagent.
