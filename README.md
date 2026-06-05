# PennyMac Trading Desktop Agent

A hierarchical **Orchestrator + Sub-Agent** framework tailored to a PennyMac
Secondary Market Trader's daily workflows: querying loan/pricing data from
Snowflake, driving complex Excel pricing models, and triggering/generating VBA
automation.

A single natural-language request (typed into the CLI) is interpreted by an
**Orchestrator Agent** that uses an LLM's native **tool-calling** to route the
work to the right specialist sub-agent and then synthesizes the result.

```text
"Pull last night's locked loans for FN30 and push them into the pricing model,
 then run the BatchPrice macro."
        │
        ▼
  Orchestrator ──tool_call──▶ Snowflake/SQL Agent ──▶ DataFrame
        │
        ├──tool_call──▶ Excel Modeling Agent ──▶ writes inputs, reads outputs
        │
        └──tool_call──▶ VBA/Process Agent ──▶ runs BatchPrice macro
```

---

## Capabilities

| Sub-Agent | Responsibility | Key Libraries |
|-----------|----------------|---------------|
| **Snowflake/SQL Data Agent** | Secure DB connections, parameterized SQL for loan/pricing data, returns `pandas.DataFrame` | `snowflake-connector-python`, `pandas` |
| **Excel Modeling Agent** | Push inputs into pricing-model workbooks, trigger recalculation, extract calculated results | `xlwings` (live) / `openpyxl` (headless) |
| **VBA/Process Agent** | Trigger existing Excel VBA macros, generate new `.bas` scripts | `xlwings` (COM) |

The LLM layer is **provider-agnostic** and config-driven: switch between
**OpenAI** and **Anthropic** with a single environment variable.

---

## Project layout

```text
.
├── README.md / ARCHITECTURE.md / WORKFLOWS.md
├── requirements.txt
├── .env.example                 # copy to .env and fill in
├── src/pennymac_agent/
│   ├── main.py                  # CLI entry point
│   ├── config/settings.py       # pydantic-settings, loads .env
│   ├── llm/                     # pluggable provider layer (openai / anthropic)
│   ├── agents/                  # base_agent + 3 sub-agents
│   ├── orchestrator/            # routing + dispatch loop
│   └── utils/logging.py
├── sql/                         # library of reusable SQL templates
├── vba/                         # library of VBA scripts (existing + generated)
├── models/registry.yaml         # named Excel model paths + cell mappings
└── tests/
```

---

## Setup

### 1. Prerequisites
- **Python 3.11+** (developed on 3.13)
- **Microsoft Excel** installed locally (required by `xlwings` for live
  workbooks and VBA macros). `openpyxl` works headless without Excel.
- Network access / VPN to your Snowflake account.

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
# Interactive REPL
python -m pennymac_agent

# One-shot request
python -m pennymac_agent run "Show me the top 20 locked loans by note rate for FN30"
```

> First run with no `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` set will start in a
> safe **dry-run** mode that prints the resolved routing without calling the LLM
> or external systems.

---

## Required environment variables

See [`.env.example`](.env.example) for the full annotated list. Summary:

### LLM
| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` | `openai` or `anthropic` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | OpenAI credentials & model |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | Anthropic credentials & model |
| `LLM_MAX_TOKENS` / `LLM_TEMPERATURE` | Shared generation settings |

### Snowflake
| Variable | Purpose |
|----------|---------|
| `SNOWFLAKE_ACCOUNT` | Account identifier (e.g. `xy12345.us-east-1`) |
| `SNOWFLAKE_USER` | Service / personal user |
| `SNOWFLAKE_PASSWORD` **or** `SNOWFLAKE_PRIVATE_KEY_PATH` | Auth (password or key-pair) |
| `SNOWFLAKE_ROLE` / `SNOWFLAKE_WAREHOUSE` | Execution role & compute |
| `SNOWFLAKE_DATABASE` / `SNOWFLAKE_SCHEMA` | Default namespace |
| `SNOWFLAKE_AUTHENTICATOR` | Optional, e.g. `externalbrowser` for SSO |

### Excel / VBA
| Variable | Purpose |
|----------|---------|
| `EXCEL_MODELS_DIR` | Folder holding pricing-model workbooks |
| `EXCEL_VISIBLE` | `true`/`false` — show Excel while automating |
| `VBA_SCRIPTS_DIR` | Folder for existing/generated VBA scripts |

---

## Security notes
- `.env` and all key files are git-ignored. **Never commit credentials.**
- Prefer Snowflake **key-pair auth** or `externalbrowser` SSO over passwords.
- The Snowflake agent rejects obviously destructive statements
  (`DROP`/`DELETE`/`TRUNCATE`/`UPDATE`/`INSERT`) by default — it is built for
  **read-only analytics**. Loosen this only deliberately.

---

## Where to go next
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — how the orchestrator and sub-agents
  communicate, module by module.
- [`WORKFLOWS.md`](WORKFLOWS.md) — how to add a new SQL query, register an Excel
  model, or wire in a VBA script.
