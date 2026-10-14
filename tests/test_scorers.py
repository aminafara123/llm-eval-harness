"""Every deterministic scorer, pass and fail, incl. numeric tolerance edges and bad JSON."""
import pytest

from eval_harness.scorers import score


def ok(output, spec):
    return score(output, spec).passed


# --- exact_match / contains family ---

def test_exact_match():
    assert ok("Paris", {"type": "exact_match", "value": "paris"})  # case-insensitive default
    assert ok("  H2O ", {"type": "exact_match", "value": "H2O"})   # trimmed
    assert not ok("Paris, France", {"type": "exact_match", "value": "Paris"})
    assert not ok("h2o", {"type": "exact_match", "value": "H2O", "case_sensitive": True})


def test_contains_variants():
    assert ok("The capital is Paris.", {"type": "contains", "value": "paris"})
    assert not ok("London", {"type": "contains", "value": "Paris"})
    assert ok("red, green and blue", {"type": "contains_all", "values": ["red", "green", "blue"]})
    assert not ok("red and green", {"type": "contains_all", "values": ["red", "green", "blue"]})
    assert ok("it is negative", {"type": "contains_any", "values": ["positive", "negative"]})
    assert not ok("unsure", {"type": "contains_any", "values": ["positive", "negative"]})


def test_regex():
    assert ok("landed in 1969.", {"type": "regex", "pattern": r"\b1969\b"})
    assert not ok("landed in 1968.", {"type": "regex", "pattern": r"\b1969\b"})


# --- numeric, including tolerance edges ---

@pytest.mark.parametrize(
    "text,value,tol,expected",
    [
        ("about 100 C", 100, 2, True),
        ("102", 100, 2, True),     # exactly at tolerance edge -> pass (<=)
        ("103", 100, 2, False),    # just past edge -> fail
        ("98", 100, 2, True),
        ("97.9", 100, 2, False),
        ("roughly 299,792 km/s", 299792, 1000, True),  # comma thousands
        ("no digits here", 100, 2, False),             # nothing to parse -> fail
        ("-5 degrees", -5, 0, True),                   # negative, zero tolerance
    ],
)
def test_numeric_tolerance(text, value, tol, expected):
    assert ok(text, {"type": "numeric", "value": value, "tolerance": tol}) is expected


# --- json_schema, valid + invalid ---

SCHEMA = {
    "type": "object",
    "required": ["vendor", "amount"],
    "properties": {"vendor": {"type": "string"}, "amount": {"type": "number"}},
}


def test_json_schema_valid():
    assert ok('{"vendor": "Acme", "amount": 1240.5}', {"type": "json_schema", "schema": SCHEMA})


def test_json_schema_valid_with_code_fence():
    fenced = '```json\n{"vendor": "Acme", "amount": 10}\n```'
    assert ok(fenced, {"type": "json_schema", "schema": SCHEMA})


def test_json_schema_invalid_type():
    # amount is a string, not a number -> schema violation
    assert not ok('{"vendor": "Acme", "amount": "lots"}', {"type": "json_schema", "schema": SCHEMA})


def test_json_schema_missing_field():
    assert not ok('{"vendor": "Acme"}', {"type": "json_schema", "schema": SCHEMA})


def test_json_schema_not_json():
    r = score("sorry, I cannot do that", {"type": "json_schema", "schema": SCHEMA})
    assert not r.passed and "not valid JSON" in r.detail


# --- json_field_equals ---

def test_json_field_equals():
    out = '{"name": "Jane", "email": "jane@example.com"}'
    assert ok(out, {"type": "json_field_equals", "field": "email", "value": "jane@example.com"})
    assert not ok(out, {"type": "json_field_equals", "field": "email", "value": "x@y.com"})


def test_json_field_equals_nested_and_missing():
    out = '{"meta": {"status": "shipped"}}'
    assert ok(out, {"type": "json_field_equals", "field": "meta.status", "value": "shipped"})
    assert not ok(out, {"type": "json_field_equals", "field": "meta.carrier", "value": "x"})


def test_json_field_equals_embedded_json():
    # model wrapped JSON in prose -> parser recovers the object
    out = 'Here you go: {"status": "shipped"} -- let me know!'
    assert ok(out, {"type": "json_field_equals", "field": "status", "value": "shipped"})


# --- dispatch edge cases ---

def test_unknown_scorer_type():
    r = score("x", {"type": "does_not_exist"})
    assert not r.passed and "unknown scorer type" in r.detail


def test_missing_required_key():
    r = score("x", {"type": "contains"})  # no 'value'
    assert not r.passed and "missing required key" in r.detail


def test_llm_judge_skipped_without_judge():
    r = score("some answer", {"type": "llm_judge", "criteria": "is good"})
    assert not r.passed and "skipped" in r.detail


def test_llm_judge_uses_injected_judge():
    r = score("answer", {"type": "llm_judge", "criteria": "ok"}, judge=lambda p: "PASS: looks right")
    assert r.passed and "AI-GENERATED" in r.detail
