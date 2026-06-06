# Knowledge directory

Reference material the agents can use. Two tiers:

- `shared/` - baseline context attached to the **whole crew** (every agent).
- `<specialist_key>/` - context for **one specialist** only. Keys:
  - `data_analyst/`
  - `excel_modeler/`
  - `automation_engineer/`

## How it is used
- RAG: supported files (`.md`, `.txt`, `.pdf`, `.csv`) are embedded and
  retrieved automatically at run time (requires an embedding API key; see
  `EMBEDDING_*` in `.env.example`). Toggle with `ENABLE_KNOWLEDGE`.
- Verbatim: agents can also list/read these files exactly via the
  `list_documents` and `read_document` tools (no embeddings needed).

Drop a Markdown/PDF/CSV file in the relevant folder and the agents pick it up on
the next run - no code changes required. See `WORKFLOWS.md` section F.
