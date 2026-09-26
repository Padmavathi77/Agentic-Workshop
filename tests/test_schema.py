import json
from typing import get_args

import pytest
from pydantic import ValidationError

from triage.schema import (
    ROUTE_FOR_CATEGORY,
    Category,
    Route,
    TriageDecision,
    TriageValidationError,
    validate_decision,
)

VALID = {
    "category": "billing",
    "priority": "P2",
    "route": "billing-team",
    "rationale": "A double charge puts money at stake, so P2 applies.",
}


def with_(**changes):
    decision = dict(VALID)
    decision.update(changes)
    return decision


def rejected(payload) -> TriageValidationError:
    with pytest.raises(TriageValidationError) as info:
        validate_decision(payload)
    assert isinstance(info.value, ValueError)
    return info.value


# --- accepted -------------------------------------------------------------


def test_valid_dict():
    decision = validate_decision(VALID)
    assert isinstance(decision, TriageDecision)
    assert decision.model_dump() == VALID


def test_valid_json_text():
    assert validate_decision(json.dumps(VALID)).model_dump() == VALID


def test_valid_json_bytes():
    assert validate_decision(json.dumps(VALID).encode()).model_dump() == VALID


def test_rationale_without_final_full_stop():
    text = "A double charge puts money at stake, so P2 applies"
    assert validate_decision(with_(rationale=text)).rationale == text


@pytest.mark.parametrize("category", ["bug", "access", "performance", "how-to"])
def test_every_category_route_pair(category):
    decision = validate_decision(with_(category=category, route=f"{category}-team"))
    assert decision.route == f"{category}-team"


def test_decision_is_frozen():
    decision = validate_decision(VALID)
    with pytest.raises(ValidationError):
        decision.priority = "P1"


# --- rejected -------------------------------------------------------------


def test_unknown_category():
    # route stays "billing-team": a bad category must not also report route.
    error = rejected(with_(category="urgent"))
    assert "category" in str(error)
    assert error.fields == ["category"]


@pytest.mark.parametrize("priority", ["P5", 2])
def test_bad_priority(priority):
    error = rejected(with_(priority=priority))
    assert "priority" in str(error)
    assert error.fields == ["priority"]


def test_route_table_matches_allowed_values():
    assert set(ROUTE_FOR_CATEGORY) == set(get_args(Category))
    assert set(ROUTE_FOR_CATEGORY.values()) == set(get_args(Route))


def test_route_mismatch():
    error = rejected(with_(route="bug-team"))
    assert "route" in str(error)
    assert error.fields == ["route"]


def test_missing_key():
    payload = dict(VALID)
    del payload["rationale"]
    error = rejected(payload)
    assert "rationale" in str(error)
    assert error.fields == ["rationale"]


def test_extra_key():
    error = rejected(with_(confidence=0.9))
    assert "confidence" in str(error)
    assert error.fields == ["confidence"]


@pytest.mark.parametrize(
    "rationale",
    [
        "Money is at stake. P2 applies.",
        "Money is at stake! P2 applies.",
        "Is money at stake? Yes, so P2.",
        "Money is at stake\nP2 applies",
        'He said "stop." Then P2.',
        "Money is at stake.P2 applies.",
    ],
)
def test_two_sentences(rationale):
    error = rejected(with_(rationale=rationale))
    assert "rationale" in str(error)
    assert error.fields == ["rationale"]
    assert "Value error" not in str(error)


@pytest.mark.parametrize(
    "rationale",
    ["Enterprise rule, P2 vs. P3 applies.", "Money is at stake, e.g. a refund."],
)
def test_abbreviation_is_rejected(rationale):
    error = rejected(with_(rationale=rationale))
    assert "rationale" in str(error)
    assert error.fields == ["rationale"]


def test_decimal_in_rationale_is_accepted():
    text = "Version 2.3 crashes on login, so P2 applies."
    assert validate_decision(with_(rationale=text)).rationale == text


@pytest.mark.parametrize("rationale", ["", "   "])
def test_empty_rationale(rationale):
    error = rejected(with_(rationale=rationale))
    assert "rationale" in str(error)
    assert error.fields == ["rationale"]


def test_several_problems_in_one_error():
    payload = with_(category="urgent")
    del payload["route"]
    error = rejected(payload)
    message = str(error)
    assert "category" in message and "route" in message
    assert sorted(error.fields) == ["category", "route"]


@pytest.mark.parametrize(
    "payload", ["[1, 2]", "not json", None, b"\xff", 42, "[" * 100000, "1" * 5000]
)
def test_not_an_object(payload):
    error = rejected(payload)
    assert "must be a JSON object" in str(error)


# --- LangChain structured output ------------------------------------------


def test_json_schema_lists_exactly_four_fields_with_allowed_values():
    schema = TriageDecision.model_json_schema()
    props = schema["properties"]
    assert set(props) == {"category", "priority", "route", "rationale"}
    assert set(schema["required"]) == set(props)
    assert schema["additionalProperties"] is False
    assert props["category"]["enum"] == [
        "billing", "bug", "access", "performance", "how-to"
    ]
    assert props["priority"]["enum"] == ["P1", "P2", "P3", "P4"]
    assert set(props["route"]["enum"]) == {
        "billing-team", "bug-team", "access-team", "performance-team", "how-to-team"
    }
    assert all(props[name].get("description") for name in props)
    for category, route in ROUTE_FOR_CATEGORY.items():
        assert f"{category} -> {route}" in props["route"]["description"]
