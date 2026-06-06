# PennyMac Trading Desktop Agent

A **CrewAI** multi-agent framework tailored to a PennyMac Secondary Market
Trader's daily workflows: querying loan/pricing data from Snowflake (and legacy
SQL Server during the migration), driving complex Excel pricing models, and
triggering/generating VBA automation.

You prompt the desk, and **autonomous reasoning agents** decide how to get the
job done with their tools. Run a **manager-led crew** that plans and delegates
across specialists, or call a **single specialist** directly.

```text
"Pull last night's locked loans for FN30, push them into the pricing model,
 then run the BatchPrice macro."
        │
        ▼
  Manager (plans + delegates, hierarchical)
        ├──▶ Data Analyst        → snowflake_query / sqlserver_query
        ├──▶ Pricing Model Eng.  → excel_model
        └──▶ Automation Engineer → run_vba_macro / generate_vba
```

---

## Agents and their tools

Agents are the **brains** (they reason and choose actions); tools are the
**hands** (deterministic Python that does the work, with guardrails).

| Specialist agent | Tools | Backed by |
|------------------|-------|-----------|
| **Data Analyst** | `snowflake_query`, `sqlserver_query`, `list_sql_queries`, doc tools | `snowflake-connector-python`, `pyodbc`+`SQLAlchemy`, `pandas` |
| **Pricing Model Engineer** | `excel_model`, `describe_excel_models`, doc tools | `xlwings` (live) / `openpyxl` (headless) |
| **Process Automation Engineer** | `run_vba_macro`, `generate_vba`, `describe_excel_models`, doc tools | `xlwings` (COM) |
| **Chief of Staff** (manager) | delegates to the above | hierarchical process |

Every specialist also has `list_documents` / `read_document` to consult the
reference material in `knowledge/` (see "Giving agents context" below).

> The desk is migrating from SQL Server to Snowflake. The Data Analyst prefers
> Snowflake and falls back to SQL Server for sources that still live only there.
> Both SQL tools are **read-only** (mutating statements are blocked).

The LLM layer is **provider-agnostic** via CrewAI/LiteLLM: switch between
**OpenAI** and **Anthropic** with one env var (`LLM_PROVIDER`).

---

## Project layout

```text
.
├── README.md / ARCHITECTURE.md / WORKFLOWS.md
├── requirements.txt
├── .env.example                 # copy to .env and fill in
├── src/pennymac_agent/
│   ├── main.py                  # CLI: crew / agent / info
│   ├── crew.py                  # hierarchical + direct run modes
│   ├── agents.py                # specialist + manager agent builders
│   ├── llm.py                   # crewai.LLM construction (OpenAI/Anthropic)
│   ├── config/settings.py       # pydantic-settings, loads .env
│   ├── tools/                   # CrewAI tools (snowflake/sqlserver/excel/vba)
│   └── utils/logging.py
├── sql/snowflake/ , sql/sqlserver/   # reusable SQL templates, by engine
├── vba/                         # VBA scripts (existing + generated)
├── models/registry.yaml         # named Excel model paths + cell mappings
├── knowledge/                   # reference docs: shared/ + per-agent (RAG)
├── artifacts/                   # query result CSVs for agent handoff (gitignored)
└── tests/
```

---

## Setup

### 1. Prerequisites
- **Python 3.11+** (developed on 3.13)
- **Microsoft Excel** installed locally (required by `xlwings` for live
  workbooks and VBA macros). `openpyxl` works headless without Excel.
- Network access / VPN to your Snowflake account.
- For the SQL Server agent: a **Microsoft ODBC Driver for SQL Server**
  (e.g. "ODBC Driver 17 for SQL Server"); set `SQL_SERVER_DRIVER` to match.

### 2. Create a virtual environment & install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Configure credentials

```powershell
Copy-Item .env.example .env
# then edit .env with your real values
```

### 4. Run

```powershell
# Manager-led crew (plans + delegates across specialists)
python -m pennymac_agent crew "Show me the top 20 locked loans by note rate for FN30"

# A single specialist directly
python -m pennymac_agent agent data_analyst "Pull the open pipeline summary by coupon"

# Show config, agents, and tools
python -m pennymac_agent info
```

> Without an API key for the selected provider, the CLI prints a dry-run notice
> instead of calling the model. `info` always works.

---

## Required environment variables

See [`.env.example`](.env.example) for the full annotated list. Summary:

### LLM (CrewAI / LiteLLM)
| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` | `openai` or `anthropic` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | OpenAI credentials & model |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | Anthropic credentials & model |
| `MANAGER_MODEL` | Optional manager-LLM override for the hierarchical crew |
| `CREW_VERBOSE` / `AGENT_MAX_ITER` | Console tracing & per-agent iteration cap |
| `ENABLE_KNOWLEDGE` | Turn the knowledge/ RAG context on/off |
| `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL` / `EMBEDDING_API_KEY` | Embeddings for knowledge (key falls back to `OPENAI_API_KEY`) |

### Snowflake
| Variable | Purpose |
|----------|---------|
| `SNOWFLAKE_ACCOUNT` | Account identifier (e.g. `xy12345.us-east-1`) |
| `SNOWFLAKE_USER` | Service / personal user |
| `SNOWFLAKE_PASSWORD` **or** `SNOWFLAKE_PRIVATE_KEY_PATH` | Auth (password or key-pair) |
| `SNOWFLAKE_ROLE` / `SNOWFLAKE_WAREHOUSE` | Execution role & compute |
| `SNOWFLAKE_DATABASE` / `SNOWFLAKE_SCHEMA` | Default namespace |
| `SNOWFLAKE_AUTHENTICATOR` | Optional, e.g. `externalbrowser` for SSO |

### SQL Server (legacy)
| Variable | Purpose |
|----------|---------|
| `SQL_SERVER_HOST` | Server, e.g. `db-prod` or `db-prod\\INSTANCE` |
| `SQL_SERVER_PORT` | Optional TCP port |
| `SQL_SERVER_DATABASE` | Database name |
| `SQL_SERVER_TRUSTED_CONNECTION` | `true` for Windows/integrated auth |
| `SQL_SERVER_USER` / `SQL_SERVER_PASSWORD` | SQL login (if not trusted) |
| `SQL_SERVER_DRIVER` | Installed ODBC driver name |
| `SQL_SERVER_ENCRYPT` / `SQL_SERVER_TRUST_SERVER_CERTIFICATE` | TLS options |

### Excel / VBA
| Variable | Purpose |
|----------|---------|
| `EXCEL_MODELS_DIR` | Folder holding pricing-model workbooks |
| `EXCEL_VISIBLE` | `true`/`false` — show Excel while automating |
| `VBA_SCRIPTS_DIR` | Folder for existing/generated VBA scripts |
| `ARTIFACTS_DIR` | Where query-result CSVs are written for agent handoff |

---

## How autonomy works
Each specialist runs CrewAI's ReAct-style loop (bounded by `AGENT_MAX_ITER`):
once prompted, it reasons about which of its tools to call, calls them, observes
results, and iterates until it can answer. In the hierarchical crew, the manager
agent does the planning and delegation; tasks are not pre-assigned.

## Giving agents context
Add reference material the agents can evaluate - data dictionaries, model
methodology, runbooks, policy docs - under `knowledge/`:

```text
knowledge/
  shared/                 # baseline context for the whole crew
  data_analyst/           # context only the Data Analyst sees
  excel_modeler/
  automation_engineer/
```

Two complementary mechanisms:
- **RAG (knowledge)**: `.md`, `.txt`, `.pdf`, `.csv` files are embedded and
  retrieved automatically at run time. Needs an embedding key (`EMBEDDING_*`);
  toggle with `ENABLE_KNOWLEDGE`.
- **Verbatim (tools)**: agents can `list_documents` and `read_document` to read a
  file exactly - no embeddings required.

The crew also has **discovery tools** so agents can evaluate live resources:
`list_sql_queries` (the SQL template library) and `describe_excel_models` (the
model registry's inputs/outputs/macros). Drop a file in `knowledge/`, add a SQL
template, or register a model and the agents pick it up on the next run - no
code changes. See [`WORKFLOWS.md`](WORKFLOWS.md) section F.

## Security notes
- `.env` and key files are git-ignored. **Never commit credentials.**
- Both data tools enforce **read-only** SQL (`DROP`/`DELETE`/`UPDATE`/`INSERT`/
  `EXEC`/... are blocked), so agent autonomy cannot mutate data.
- Prefer Snowflake key-pair/SSO and SQL Server Windows auth over passwords.

## Where to go next
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — agents vs tools, hierarchical vs direct
  flows, module map.
- [`WORKFLOWS.md`](WORKFLOWS.md) — add a SQL query, register an Excel model, add
  a VBA script, or add a new tool/agent.
