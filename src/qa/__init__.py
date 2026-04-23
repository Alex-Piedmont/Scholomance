"""Migration QA tooling.

Audit DB records against Discovery UI rendering surfaces. Read-only by contract:
this package never writes to `technologies`, `raw_data`, or any scraper-managed
table. See `docs/plans/2026-04-23-002-fix-migration-qa-drawer-parity-plan.md`.
"""
