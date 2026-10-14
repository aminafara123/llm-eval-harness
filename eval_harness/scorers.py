"""Deterministic scorers for eval cases.

Every scorer takes (output, spec) and returns a ScoreResult(passed, detail).
`spec` is the case's `scorer:` block from YAML, e.g. {"type": "contains", "value": "Paris"}.
All scorers here are offline and pure -- they are what the test gate covers.

`llm_judge` is the one exception: it is OPTIONAL, AI-generated, advisory, and never
required for the offline gate. It is routed through `score(..., judge=...)` and returns
a clearly-labelled result.
"""
import json
import re
from collections import namedtuple

try:
    import jsonschema
except ImportError:  # kept importable so non-schema scorers still work without the dep
    jsonschema = None

ScoreResult = namedtuple("ScoreResult", "passed detail")

# Deterministic scorer types (what validation accepts offline). llm_judge is handled
# separately in score() and is intentionally NOT in this set.
DETERMINISTIC_TYPES = frozenset(
    [
        "exact_match",
        "contains",
        "contains_all",
        "contains_any",
        "regex",
        "numeric",
        "json_schema",
        "json_field_equals",
    ]
)
KNOWN_TYPES = DETERMINISTIC_TYPES | {"llm_judge"}


# --- helpers ---------------------------------------------------------------

def _norm(text, case_sensitive):
    return text if case_sensitive else text.lower()


def _first_number(text):
    """First numeric literal in text, thousands-commas ignored.

    ponytail: naive first-number scan; good enough for "give a number" answers.
    Upgrade to a units-aware parser only if cases need it.
    """
    m = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    return float(m.group()) if m else None


def _parse_json(text):
    """Parse a JSON value from model output, tolerating code fences / surrounding prose.

    ponytail: falls back to the outermost {...}/[...] span; a model that emits two
    JSON blobs would confuse it. Fine for "reply with only JSON" cases.
    """
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t).strip()
    try:
        return json.loads(t)
    except ValueError:
        m = re.search(r"[\{\[].*[\}\]]", t, re.S)
        if not m:
            raise
        return json.loads(m.group(0))


def _get_field(obj, path):
    """Walk a dotted path ('a.b.c') through nested dicts; raises KeyError if absent."""
    cur = obj
    for part in path.split("."):
        cur = cur[part]
    return cur


# --- scorers ---------------------------------------------------------------

def exact_match(output, spec):
    cs = spec.get("case_sensitive", False)
    want = str(spec["value"])
    ok = _norm(output.strip(), cs) == _norm(want, cs)
    return ScoreResult(ok, f"exact_match {'==' if ok else '!='} {want!r}")


def contains(output, spec):
    cs = spec.get("case_sensitive", False)
    want = str(spec["value"])
    ok = _norm(want, cs) in _norm(output, cs)
    return ScoreResult(ok, f"{'found' if ok else 'missing'} substring {want!r}")


def contains_all(output, spec):
    cs = spec.get("case_sensitive", False)
    hay = _norm(output, cs)
    missing = [v for v in spec["values"] if _norm(str(v), cs) not in hay]
    return ScoreResult(not missing, "all present" if not missing else f"missing: {missing}")


def contains_any(output, spec):
    cs = spec.get("case_sensitive", False)
    hay = _norm(output, cs)
    hit = next((v for v in spec["values"] if _norm(str(v), cs) in hay), None)
    return ScoreResult(hit is not None, f"matched {hit!r}" if hit is not None else f"none of {spec['values']}")


def regex(output, spec):
    flags = re.IGNORECASE if not spec.get("case_sensitive", False) else 0
    ok = re.search(spec["pattern"], output, flags) is not None
    return ScoreResult(ok, f"regex {'matched' if ok else 'no match'}: {spec['pattern']!r}")


def numeric(output, spec):
    target = float(spec["value"])
    tol = float(spec.get("tolerance", 0))
    got = _first_number(output)
    if got is None:
        return ScoreResult(False, "no number found in output")
    ok = abs(got - target) <= tol
    return ScoreResult(ok, f"got {got}, want {target}+-{tol} (|diff|={abs(got - target):g})")


def json_schema(output, spec):
    if jsonschema is None:
        return ScoreResult(False, "jsonschema not installed")
    try:
        obj = _parse_json(output)
    except ValueError as e:
        return ScoreResult(False, f"output is not valid JSON: {e}")
    try:
        jsonschema.validate(obj, spec["schema"])
    except jsonschema.ValidationError as e:
        return ScoreResult(False, f"schema violation: {e.message}")
    return ScoreResult(True, "valid against schema")


def json_field_equals(output, spec):
    try:
        obj = _parse_json(output)
    except ValueError as e:
        return ScoreResult(False, f"output is not valid JSON: {e}")
    try:
        got = _get_field(obj, spec["field"])
    except (KeyError, TypeError):
        return ScoreResult(False, f"field {spec['field']!r} not found")
    ok = got == spec["value"]
    return ScoreResult(ok, f"{spec['field']}={got!r}, want {spec['value']!r}")


_SCORERS = {
    "exact_match": exact_match,
    "contains": contains,
    "contains_all": contains_all,
    "contains_any": contains_any,
    "regex": regex,
    "numeric": numeric,
    "json_schema": json_schema,
    "json_field_equals": json_field_equals,
}


def _llm_judge(output, spec, judge):
    """Optional, AI-generated, advisory. Requires an injected judge(prompt)->text callable.

    Returns a labelled result. Never part of the offline gate; if no judge is wired,
    the case is reported as skipped (treated as not-passed so it is visible).
    """
    if judge is None:
        return ScoreResult(False, "llm_judge skipped (no judge configured; optional + advisory)")
    criteria = spec["criteria"]
    prompt = (
        "You are grading one model output. Reply with exactly PASS or FAIL on the first line.\n"
        f"Criteria: {criteria}\n\nOutput to grade:\n{output}\n"
    )
    try:
        verdict = judge(prompt).strip()
    except Exception as e:  # noqa: BLE001 -- judge is external; never crash the run
        return ScoreResult(False, f"llm_judge unavailable: {e}")
    passed = verdict.upper().startswith("PASS")
    return ScoreResult(passed, f"[AI-GENERATED, ADVISORY] judge said: {verdict.splitlines()[0][:120]!r}")


def score(output, spec, judge=None):
    """Dispatch to the scorer named by spec['type']. `judge` only used by llm_judge."""
    stype = spec.get("type")
    if stype == "llm_judge":
        return _llm_judge(output, spec, judge)
    fn = _SCORERS.get(stype)
    if fn is None:
        return ScoreResult(False, f"unknown scorer type: {stype!r}")
    try:
        return fn(output, spec)
    except KeyError as e:
        return ScoreResult(False, f"scorer {stype!r} missing required key {e}")
