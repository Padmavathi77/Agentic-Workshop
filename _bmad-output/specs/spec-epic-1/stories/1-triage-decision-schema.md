---
title: 'Triage decision schema'
type: 'feature'
created: '2026-09-26'
status: 'done'
route: 'dispatch'
baseline_commit: '570c521ab119bc20e46ebcdc69bcaf29b1388cf4'
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/specs/spec-epic-1/SPEC.md', '{project-root}/_bmad-output/specs/spec-epic-1/triage-decision-fields.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Nothing defines what a valid triage decision is, so the Epic 2 agent has no structured output to target and the Epic 3 eval has no `valid_schema` check to run (SPEC CAP-1).

**Approach:** Add one importable schema for a triage decision (category, priority, route, rationale) plus a validate function that accepts a dict or JSON text and either returns the decision or raises one error listing every bad field by name.

## Boundaries & Constraints

**Always:** Exactly four keys. Allowed values, the category→route pairing and the one-sentence rule are those in `triage-decision-fields.md`. Every rejection names the offending field(s). Pure Python, no network, no API keys. The schema must be usable as LangChain structured output (a Pydantic model).

**Never:** No loader, `app.db`, agent, MCP or eval code (other stories/epics). Do not touch `seed/`, `mcp/triage_server.py`, `TRIAGE_POLICY.md` or `run_agent.py`. No new dependencies (Pydantic is already declared).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid dict | `{"category":"billing","priority":"P2","route":"billing-team","rationale":"A double charge puts money at stake, so P2 applies."}` | Returns a `TriageDecision` with those values | N/A |
| Valid JSON text | Same object as a JSON string | Same as above | N/A |
| No final full stop | rationale `A double charge puts money at stake, so P2 applies` | Accepted | N/A |
| Unknown category | `category: "urgent"` | Rejected | Error names `category` |
| Bad priority | `priority: "P5"` or `priority: 2` | Rejected | Error names `priority` |
| Route mismatch | `billing` with `bug-team` | Rejected | Error names `route` |
| Missing key | no `rationale` | Rejected | Error names `rationale` |
| Extra key | adds `"confidence": 0.9` | Rejected | Error names `confidence` |
| Two sentences | `Money is at stake. P2 applies.` | Rejected | Error names `rationale` |
| Abbreviation | `Enterprise rule, P2 vs. P3 applies.` | Rejected (accepted trade-off) | Error names `rationale` |
| Empty rationale | `""` or `"   "` | Rejected | Error names `rationale` |
| Several problems | bad category and missing route | Rejected | One error naming both fields |
| Not an object | `"[1, 2]"`, `"not json"`, `None` | Rejected | Error says the decision must be a JSON object |

</frozen-after-approval>

## Code Map

- `triage/__init__.py` -- new, empty; makes `triage` a package.
- `triage/schema.py` -- new. Public names later stages import (matches the workshop's reference Epic 2/3 code): `TriageDecision`, `TriageValidationError`, `validate_decision`.
- `tests/conftest.py` -- new; puts the repo root on `sys.path` so tests can `import triage` (`pyproject.toml` sets `testpaths = ["tests"]`; no package build).
- `tests/test_schema.py` -- new; one test per I/O matrix row.
- `triage-decision-fields.md` (spec folder) -- source of allowed values, route table and one-sentence examples.
- Do not change: `pyproject.toml`, `run_agent.py`, `mcp/`, `seed/`.

## Tasks & Acceptance

**Execution:**
- [ ] `triage/__init__.py` -- create empty -- package for `triage.schema`.
- [ ] `triage/schema.py` -- define `TriageDecision` (Pydantic, extra keys forbidden, `Literal` types for category/priority/route, rationale validator, model validator enforcing the category→route table), `TriageValidationError(ValueError)`, and `validate_decision(payload: dict | str | bytes) -> TriageDecision` that parses JSON text, rejects non-objects, and re-raises Pydantic errors as one `TriageValidationError` naming each field -- single source of truth for Epics 2 and 3.
- [ ] `tests/conftest.py` -- add repo root to `sys.path` -- lets tests import `triage`.
- [ ] `tests/test_schema.py` -- cover every I/O matrix row, asserting the field name appears in the error message -- proves CAP-1.

**Acceptance Criteria:**
- Given a clean checkout of this branch, when `uv run pytest` runs, then all schema tests pass with no network access and no `.env`.
- Given `TriageDecision`, when it is passed to LangChain as a structured-output schema, then its JSON schema lists exactly the four fields with their allowed values (field descriptions present).
- Given any rejected input, when `validate_decision` raises, then the exception is a `TriageValidationError` (a `ValueError`) and its message names every offending field.

## Implementation Notes

## Spec Change Log

## Review Triage Log

### Review Findings

Code review 2026-09-26 (uncommitted story files vs baseline `570c521`).

- [x] [Review][Patch] One-sentence rule lets some two-sentence rationales through. Decision (2026-09-26, Padmavathi): also reject a line break followed by more text, a sentence end followed by a closing quote/bracket and then whitespace and more text, and a sentence end followed directly by a letter (`stake.P2`). Accepted trade-off: `e.g.` and domain names like `docs.example.com` are now rejected too, like `vs.` [triage/schema.py:39]
- [x] [Review][Patch] `validate_decision` leaks raw `RecursionError` / `ValueError` for pathological JSON text (`"[" * 100000`, a 5000-digit integer), breaking "any rejected input raises `TriageValidationError`" [triage/schema.py:115]
- [x] [Review][Patch] `route` description does not state the category→route pairing, so a structured-output LLM cannot know the rule and will produce avoidable mismatches [triage/schema.py:53]
- [x] [Review][Patch] Route check is a field validator reading `info.data` (story asked for a model validator); it depends on `category` being declared before `route`. Add a test that `category="urgent"` with `route="billing-team"` reports only `category`, which pins the Design Notes rule and guards reordering [tests/test_schema.py:66]
- [x] [Review][Patch] `ROUTE_FOR_CATEGORY` duplicates the `Category`/`Route` Literals with no sync check; a future category added only to the Literal makes validation crash with `KeyError`. Add a test that keys/values equal `get_args(Category)` / `get_args(Route)` [triage/schema.py:30]
- [x] [Review][Patch] `!` and `?` sentence ends are untested; narrowing the regex to `.` would pass the suite. Parametrize `test_two_sentences` [tests/test_schema.py:99]
- [x] [Review][Patch] `test_abbreviation_is_rejected` does not assert `error.fields == ["rationale"]` like its siblings [tests/test_schema.py:105]
- [x] [Review][Patch] Error messages carry Pydantic's `Value error, ` prefix (e.g. `rationale: Value error, rationale must be exactly one sentence`), which Epic 3 will surface [triage/schema.py:130]

**Rejected**

- false: direct `TriageDecision(...)` raises `pydantic.ValidationError`, not `TriageValidationError`. The AC only covers `validate_decision`.
- low: rationale comes back stripped of surrounding whitespace. No caller is harmed.
- low: no `max_length` on rationale. The spec sets no limit, so adding one would change the contract.
- low: UTF-8 BOM bytes are rejected. JSON from the model or a CSV string won't carry one.
- low: duplicate JSON keys resolve to the last value. Unlikely, and the fix adds a parse hook.
- low: a punctuation-only rationale (`"..."`) is accepted. Unlikely in practice.
- low: the `payload` annotation is narrower than the inputs actually handled. Cosmetic.
- low: `fields` is `[]` for "not an object" and no test pins that. The matrix contract is the message, which is tested.
- low: no tests for an unknown route with a valid category, or wrong types on other fields. Pydantic `Literal`/strict behaviour is already exercised by the priority tests.

## Design Notes

One-sentence rule: strip the text; reject if empty, or if a `.`, `!` or `?` is followed by whitespace and more text (regex like `[.!?]\s+\S`). A final `.`/`!`/`?` is allowed. The route check runs only when category and route are each individually valid, so a bad category reports `category`, not a spurious `route` mismatch. Keep the model `frozen=True` so a validated decision cannot be mutated afterwards.

## Verification

**Commands:**
- `uv run pytest` -- expected: all tests pass.
- `uv run python -c "from triage.schema import validate_decision; print(validate_decision({'category':'billing','priority':'P2','route':'billing-team','rationale':'Money is at stake, so P2.'}))"` -- expected: prints the decision.
