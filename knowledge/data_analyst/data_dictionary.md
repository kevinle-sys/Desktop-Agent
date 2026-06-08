# Data dictionary (Data Analyst context)

Replace these placeholders with your real schema. This helps the analyst write
correct queries and choose the right source.

## Snowflake (preferred)
- `secondary.locks` - one row per locked loan.
  - `loan_id`, `note_rate`, `upb`, `lock_date`, `product`
- `secondary.pipeline` - open pipeline snapshot.
  - `loan_id`, `product`, `coupon`, `upb`, `note_rate`, `status`, `as_of_date`

## SQL Server (legacy - only if not yet migrated)
- `dbo.locks` - T-SQL equivalent of `secondary.locks`.

## Conventions
- Dates are `YYYY-MM-DD`.
- Always parameterize (`%(name)s` for Snowflake, `:name` for SQL Server).
- Use the named-query library first (`list_sql_queries`) before writing ad-hoc SQL.

## Legacy query reference (unvalidated)
- A large set of historical queries lives under `legacy_queries/` in the
  knowledge directory (`legacy_queries/sql_queries/` and `legacy_queries/ad_hoc/`).
- Browse with `list_documents subdir="legacy_queries"` and read with
  `read_document`. Use them for table/column hints and patterns only.
- They are UNVALIDATED and may reference outdated schemas - do NOT run them
  verbatim. Adapt and verify, ideally porting good ones into the validated
  `sql/` library.
