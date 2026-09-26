# Triage decision fields

A triage decision is a JSON object with exactly these four keys. Any other key, a missing key, a wrong type or a value outside the allowed set is rejected with an error that names the offending field.

| Field | Type | Allowed values |
|---|---|---|
| `category` | string | `billing`, `bug`, `access`, `performance`, `how-to` |
| `priority` | string | `P1`, `P2`, `P3`, `P4` |
| `route` | string | The one route paired with `category` (table below) |
| `rationale` | string | Exactly one sentence |

## Category to route

From `TRIAGE_POLICY.md`. A route that does not match the category is rejected with an error naming `route`.

| Category | Route |
|---|---|
| `billing` | `billing-team` |
| `bug` | `bug-team` |
| `access` | `access-team` |
| `performance` | `performance-team` |
| `how-to` | `how-to-team` |

## One sentence

Rejected: empty or whitespace-only text, and text where a sentence end (`.`, `!` or `?`) is followed by more text. A mid-text abbreviation such as `vs.` is therefore rejected too.

| Rationale | Result |
|---|---|
| `A double charge puts money at stake, so P2 applies.` | accepted |
| `A double charge puts money at stake, so P2 applies` | accepted |
| `Money is at stake. P2 applies.` | rejected |
| `""` or `"   "` | rejected |

## Example of a valid decision

```json
{"category": "billing", "priority": "P2", "route": "billing-team", "rationale": "A double charge puts money at stake, so P2 applies."}
```
