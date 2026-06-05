# SQL query library

Named, reusable queries the data agents run by filename (without extension).
Templates are organized by engine because the two dialects use different
bind-parameter syntax:

| Folder | Agent | Tool name | Param style | Row cap |
|--------|-------|-----------|-------------|---------|
| `snowflake/` | Snowflake/SQL agent | `snowflake_query` | `%(name)s` | `LIMIT %(row_limit)s` |
| `sqlserver/` | SQL Server agent | `sqlserver_query` | `:name` | `TOP (:row_limit)` |

Always use bind parameters (never string-format values into the SQL).

See [`../WORKFLOWS.md`](../WORKFLOWS.md) section A for how to add a new query.

The example files reference placeholder objects (`secondary.locks`,
`secondary.pipeline` on Snowflake; `dbo.locks` on SQL Server) — replace them
with your actual tables.

## Which engine?
The desk is migrating from SQL Server to Snowflake. Add new queries under
`snowflake/` when the data is available there; keep/extend `sqlserver/` only
for sources that still live exclusively in SQL Server.
