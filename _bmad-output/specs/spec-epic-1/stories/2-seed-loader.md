---
title: 'Seed loader'
type: 'feature'
created: '2026-09-26'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/specs/spec-epic-1/SPEC.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `mcp/triage_server.py` reads `app.db`, but nothing creates it, so the agent's tools fail with "app.db not found" (SPEC CAP-2, CAP-3).

**Approach:** Add `load_seed.py` at the repo root. `uv run python load_seed.py` rebuilds the `tickets` and `customers` tables in `app.db` from `seed/tickets.csv` and `seed/customers.csv` in one transaction (drop, create, insert). The tables and columns are the CSV headers, `open_tickets` is an INTEGER and every other column is TEXT. Running it twice gives the same tables, columns and rows, and `get_ticket("T-1042")` returns customer `C-77`. Pure standard library, no network, no API keys; `seed/` is only read and `mcp/triage_server.py` is not changed.

</frozen-after-approval>

## Implementation Notes

- `load_seed.py` -- new; `load(db_path, seed_dir)` does the work so tests can point it at a temp directory; `main()` loads into the repo-root `app.db` and prints the row counts.
- `tests/test_load_seed.py` -- new; covers the CSV-to-table match, the INTEGER `open_tickets`, loading twice, and `get_ticket("T-1042")` through `mcp/triage_server.py` loaded by file path with `DB_PATH` pointed at the temp database (the repo's `mcp/` folder shares its name with the installed `mcp` package, so it is not imported as a package).
- Review fixes: CSVs are read before connecting, so a missing seed file leaves no empty `app.db`; `ROLLBACK` runs only when a transaction is open, so it cannot mask the original error. Added tests for a failed load keeping the previous data, a missing seed file creating no database, and the exact set of customers with 3 or more open tickets.

## Review Triage Log

Blind Hunter, 2026-09-26:

- low, patched: an empty `app.db` was left behind when a seed file was missing, which hid the MCP server's "Load the data first" message. The CSVs are now read before connecting.
- low, patched: `ROLLBACK` could raise "no transaction is active" and mask the original error. It is now guarded by `conn.in_transaction`.
- low, patched: no test covered the all-or-nothing load. Added a failed-load test and a missing-seed test.
- low, patched: the open-tickets test only checked `C-05`. It now compares the full set against the CSV.
- low, rejected: headers are not checked against the MCP columns. `seed/` is read-only, and `test_column_names_match_mcp_server` pins the names.
- low, rejected: a BOM in a CSV would break the first column. The seed files are read-only and have no BOM.
- low, rejected: malformed rows or a non-numeric `open_tickets` give poor errors. The seed data is fixed and every value is valid.
- low, rejected: no `PRIMARY KEY` on the ID columns. The seed IDs are unique (checked), and the table shape stays exactly the CSV columns.
- low, rejected: header text goes into SQL unescaped. The headers are trusted, read-only seed data.
- low, rejected: `main()` is untested. It is a two-line wrapper, and running `uv run python load_seed.py` twice was verified by hand.
- false: "the story lacks ACs and verification steps". The oneshot route keeps only the Intent and Implementation Notes by design, and the status is set to done here.
