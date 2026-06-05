# SQL query library

Each `.sql` file here is a named, reusable query the Snowflake/SQL agent can
run by filename (without extension). Use `%(name)s` bind parameters so values
are passed safely instead of string-formatted.

See [`../WORKFLOWS.md`](../WORKFLOWS.md) section A for how to add a new query.

The example files (`locked_loans_by_product.sql`, `pipeline_summary_by_coupon.sql`)
reference placeholder table names (`secondary.locks`, `secondary.pipeline`) —
replace them with your actual Snowflake objects.
