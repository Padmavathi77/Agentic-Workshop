---
id: SPEC-epic-1
companions: [triage-decision-fields.md, ../../../mcp/triage_server.py]
sources: [../../../INTENT.md]
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Epic 1: triage data and schema

## Why

The triage agent (Epic 2) and its eval (Epic 3) both need two things that do not exist yet: a strict definition of what a triage decision is, and the seed tickets and customers in the SQLite database `mcp/triage_server.py` already reads. Epic 1 lays that foundation so later epics build on validated data instead of guessing at shapes.

## Capabilities

- **CAP-1**
  - **intent:** Any triage decision can be checked against one schema: category, priority, the route that matches the category, and a one-sentence rationale (see `triage-decision-fields.md`).
  - **success:** A decision such as `billing` / `P2` / `billing-team` with a one-sentence rationale is accepted. A missing field, a wrong type, an extra key, a value outside the allowed set (e.g. category `urgent`, priority `P5`), a route that doesn't match the category (`billing` with `bug-team`), or a rationale of more than one sentence is rejected with an error that names the field.

- **CAP-2**
  - **intent:** One command, `uv run python load_seed.py`, loads `seed/tickets.csv` and `seed/customers.csv` into the local SQLite file `app.db`.
  - **success:** After the command, `app.db` holds a `tickets` table and a `customers` table with the same columns and rows as their CSV files, and `mcp/triage_server.py`'s `get_ticket("T-1042")` returns customer `C-77`.

- **CAP-3**
  - **intent:** Loading is repeatable.
  - **success:** Running `uv run python load_seed.py` twice leaves the same tables, columns and rows as running it once, with no duplicates.

## Constraints

- Python 3.12 or newer, managed with uv.
- Files in `seed/` are read-only.
- No network calls and no API keys in this epic.
- `app.db` sits at the repo root with the table and column names `mcp/triage_server.py` queries: `tickets(ticket_id, customer_id, created_at, text)` and `customers(customer_id, name, plan, open_tickets)`.
- `app.db` is never committed.

## Non-goals

- The agent, the MCP tools, evals and any user interface.
- Changes to `mcp/triage_server.py`.

## Success signal

On a fresh clone, `uv run python load_seed.py` run twice produces an `app.db` that `mcp/triage_server.py` answers from (T-1042 resolves to customer C-77), and the schema accepts a valid `billing` / `P2` / `billing-team` decision while rejecting `category: "urgent"` with an error naming `category`.

## Assumptions

- Keys beyond the four decision fields are rejected; "anything else" is read as covering extra keys.
- "Same database" means the same tables, columns and rows, not a byte-identical file.
- `open_tickets` is stored as an integer so the policy's Enterprise rule (3 or more open tickets) compares numerically; other columns stay text.
