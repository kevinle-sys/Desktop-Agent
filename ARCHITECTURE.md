# Architecture

This project has two layers:

- **Brains — Cursor Subagents** (`.cursor/agents/*.md`): autonomous reasoners
  that run inside Cursor on your Cursor subscription (no external API key).
- **Hands — an MCP server** (`pennymac_agent.mcp_server`): a local stdio server
  exposing deterministic tools that connect to Snowflake, SQL Server, Excel, and
  VBA. Tool logic is plain Python in `src/pennymac_agent/tools/`.

Cursor connects to the MCP server via `.cursor/mcp.json`; subagents call the
tools through that connection.

---

## 1. Components

```mermaid
flowchart TD
    User[Trader in Cursor] --> Orch["orchestrator subagent"]
    Orch -. delegates via Task .-> DA["data-analyst (readonly)"]
    Orch -. delegates .-> EM["excel-modeler"]
    Orch -. delegates .-> AE["automation-engineer"]
    subgraph mcp [pennymac-trading MCP server]
        T1[snowflake_query]
        T2[sqlserver_query]
        T3[list_sql_queries]
        T4[excel_model]
        T5[describe_excel_models]
        T6[run_vba_macro]
        T7[generate_vba]
        T8[list_documents / read_document]
    end
    DA --> T1
    DA --> T2
    DA --> T3
    DA --> T8
    EM --> T4
    EM --> T5
    AE --> T6
    AE --> T7
    T1 --> SF[(Snowflake)]
    T2 --> MS[("SQL Server / qrm_pulsar")]
    T4 --> WB["Excel workbooks"]
    T6 --> MAC["VBA macros"]
```

---

## 2. Request flow

```mermaid
sequenceDiagram
    participant U as Trader (Cursor)
    participant O as orchestrator subagent
    participant S as specialist subagent
    participant M as MCP server (tool)
    U->>O: multi-step request
    O->>O: plan steps + pick specialists
    O->>S: delegate (Task tool, parallel when independent)
    S->>M: call tool (e.g. sqlserver_query)
    M-->>S: result summary + saved CSV path
    S-->>O: findings
    O-->>U: synthesized answer (+ artifacts)
```

Independent steps fan out in parallel; dependent steps chain by passing a saved
CSV path from the data-analyst to the excel-modeler.

---

## 3. Why this design
- **No LLM key/gateway**: reasoning runs on the user's Cursor plan — this is the
  main reason we moved off a standalone Python agent framework.
- **Deterministic, auditable tools**: the MCP tools are plain functions with a
  read-only SQL guardrail; the model can't run destructive SQL.
- **Same domain logic**: connections, named-query libraries, the Excel registry,
  and the knowledge docs carry over unchanged — only the orchestration/LLM layer
  changed.
- **Constraint**: subagents run interactively inside Cursor, not as a headless
  service.

---

## 4. Module map

| Path | Responsibility |
|------|----------------|
| [.cursor/agents/orchestrator.md](.cursor/agents/orchestrator.md) | Master agent: plan + delegate + synthesize. |
| [.cursor/agents/data-analyst.md](.cursor/agents/data-analyst.md) | Read-only data specialist (Snowflake + SQL Server). |
| [.cursor/agents/excel-modeler.md](.cursor/agents/excel-modeler.md) | Drives Excel pricing models. |
| [.cursor/agents/automation-engineer.md](.cursor/agents/automation-engineer.md) | Runs/authors VBA. |
| [.cursor/mcp.json](.cursor/mcp.json) | Registers the `pennymac-trading` MCP server. |
| [src/pennymac_agent/mcp_server.py](src/pennymac_agent/mcp_server.py) | FastMCP server; registers tool functions over stdio. |
| `src/pennymac_agent/tools/snowflake_tool.py` | `snowflake_query`. |
| `src/pennymac_agent/tools/sqlserver_tool.py` | `sqlserver_query`. |
| `src/pennymac_agent/tools/excel_tool.py` | `excel_model`. |
| `src/pennymac_agent/tools/vba_tool.py` | `run_vba_macro`, `generate_vba`. |
| `src/pennymac_agent/tools/discovery_tool.py` | `list_sql_queries`, `describe_excel_models`. |
| `src/pennymac_agent/tools/docs_tool.py` | `list_documents`, `read_document`. |
| `src/pennymac_agent/tools/_sql_common.py` | Read-only guardrail, named-query loading, result persistence. |
| [src/pennymac_agent/config/settings.py](src/pennymac_agent/config/settings.py) | Settings (Snowflake, SQL Server, Excel/VBA, paths). No LLM keys. |

---

## 5. Agent context
Agents get context from:
- **Reference docs** in `knowledge/` (read via `list_documents`/`read_document`),
  including the local, git-ignored `legacy_queries/` library (~260 historical
  queries) for table/column hints.
- **Discovery tools** (`list_sql_queries`, `describe_excel_models`) for live
  resources.
- **Subagent system prompts** in `.cursor/agents/*.md` (role, conventions, the
  `vw_Pipe`/`SPP_Rule` facts, source policy).
