"""The triage decision schema: the single definition of a valid decision.

Epic 2 uses `TriageDecision` as the agent's structured output; Epic 3 uses
`validate_decision` for its `valid_schema` check. Allowed values, the
category-to-route table and the one-sentence rule come from
`_bmad-output/specs/spec-epic-1/triage-decision-fields.md`.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
)

Category = Literal["billing", "bug", "access", "performance", "how-to"]
Priority = Literal["P1", "P2", "P3", "P4"]
Route = Literal[
    "billing-team", "bug-team", "access-team", "performance-team", "how-to-team"
]

ROUTE_FOR_CATEGORY: dict[str, str] = {
    "billing": "billing-team",
    "bug": "bug-team",
    "access": "access-team",
    "performance": "performance-team",
    "how-to": "how-to-team",
}

# A second sentence: a sentence end (optionally closed by a quote or bracket)
# followed by whitespace and more text, a sentence end followed directly by a
# letter, or a line break followed by more text. `e.g.` and `vs.` are rejected.
_SECOND_SENTENCE = re.compile(r"[.!?][\"')\]]*\s+\S|[.!?][A-Za-z]|\n\s*\S")


class TriageDecision(BaseModel):
    """A triage decision for one support ticket."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    category: Category = Field(
        description="Ticket category: billing, bug, access, performance or how-to."
    )
    priority: Priority = Field(
        description="Priority from P1 (most urgent) to P4 (least urgent)."
    )
    route: Route = Field(
        description=(
            "The team paired with the category: billing -> billing-team, "
            "bug -> bug-team, access -> access-team, "
            "performance -> performance-team, how-to -> how-to-team."
        )
    )
    rationale: str = Field(
        description="Exactly one sentence explaining the category and priority."
    )

    @field_validator("rationale")
    @classmethod
    def _one_sentence(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("rationale must not be empty")
        if _SECOND_SENTENCE.search(text):
            raise ValueError("rationale must be exactly one sentence")
        return text

    @field_validator("route")
    @classmethod
    def _route_matches_category(cls, value: str, info: ValidationInfo) -> str:
        # Runs only when `route` is itself valid; `category` is present in
        # info.data only when it too was valid, so a bad category never
        # produces a spurious route mismatch.
        category = info.data.get("category")
        if category is not None and ROUTE_FOR_CATEGORY[category] != value:
            raise ValueError(
                f"route {value!r} does not match category {category!r}; "
                f"expected {ROUTE_FOR_CATEGORY[category]!r}"
            )
        return value


class TriageValidationError(ValueError):
    """Raised when a payload is not a valid triage decision.

    `fields` lists every offending field name; the message names them too.
    """

    def __init__(self, message: str, fields: list[str] | None = None) -> None:
        super().__init__(message)
        self.fields: list[str] = fields or []


_NOT_AN_OBJECT = "the decision must be a JSON object"


def validate_decision(payload: dict | str | bytes) -> TriageDecision:
    """Return `payload` as a `TriageDecision`, or raise `TriageValidationError`.

    `payload` may be a dict or JSON text (str or bytes) encoding an object.
    """
    data: Any = payload
    if isinstance(data, (bytes, bytearray)):
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError:
            raise TriageValidationError(_NOT_AN_OBJECT) from None
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (ValueError, RecursionError):
            # ValueError covers JSONDecodeError and over-long integer literals.
            raise TriageValidationError(_NOT_AN_OBJECT) from None
    if not isinstance(data, dict):
        raise TriageValidationError(_NOT_AN_OBJECT)

    try:
        return TriageDecision.model_validate(data)
    except ValidationError as exc:
        fields: list[str] = []
        problems: list[str] = []
        for error in exc.errors():
            name = ".".join(str(part) for part in error["loc"]) or "decision"
            if name not in fields:
                fields.append(name)
            msg = error["msg"].removeprefix("Value error, ")
            problems.append(f"{name}: {msg}")
        message = (
            f"invalid triage decision (bad fields: {', '.join(fields)}): "
            + "; ".join(problems)
        )
        raise TriageValidationError(message, fields) from None
