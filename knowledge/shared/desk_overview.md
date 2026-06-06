# Secondary Market Desk - Overview (shared context)

This baseline context is available to every agent in the crew. Replace the
placeholders below with your desk's real conventions.

## Mission
Support a PennyMac Secondary Market trader with data pulls, pricing-model
runs, and workflow automation. Accuracy first: never fabricate loan, pricing,
or model values - always query or compute them.

## Data source policy (migration)
- The desk is migrating from SQL Server to Snowflake.
- Prefer Snowflake when the data is available there.
- Use SQL Server only for sources not yet migrated.
- All queries are read-only.

## Common terms
- UPB: Unpaid Principal Balance.
- WAC: Weighted Average Coupon.
- OAS: Option-Adjusted Spread.
- Lock: a committed price/rate on a loan or pool.

## Products (examples - replace with your set)
- FN30 / FN15: Fannie Mae 30yr / 15yr.
- GN30: Ginnie Mae 30yr.
