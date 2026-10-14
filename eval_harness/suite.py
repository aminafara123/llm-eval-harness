"""Load and validate an eval suite from YAML.

Suite shape:
    name: my-suite
    description: optional text
    cases:
      - id: unique_id
        prompt: "..."          # may use $var placeholders
        system: "..."          # optional system prompt
        vars: {k: v}           # optional, substituted into prompt
        scorer: {type: contains, value: Paris}
"""
from pathlib import Path

import yaml

from .scorers import KNOWN_TYPES


def validate_suite(data):
    """Raise ValueError with a clear message if the suite is malformed. Returns data."""
    if not isinstance(data, dict):
        raise ValueError("suite must be a mapping (got %s)" % type(data).__name__)
    if not data.get("name"):
        raise ValueError("suite missing required 'name'")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("suite must have a non-empty 'cases' list")
    seen = set()
    for i, c in enumerate(cases):
        if not isinstance(c, dict):
            raise ValueError(f"case {i} must be a mapping")
        cid = c.get("id")
        if not cid:
            raise ValueError(f"case {i} missing 'id'")
        if cid in seen:
            raise ValueError(f"duplicate case id: {cid!r}")
        seen.add(cid)
        if "prompt" not in c:
            raise ValueError(f"case {cid!r} missing 'prompt'")
        scorer = c.get("scorer")
        if not isinstance(scorer, dict) or "type" not in scorer:
            raise ValueError(f"case {cid!r} missing 'scorer.type'")
        if scorer["type"] not in KNOWN_TYPES:
            raise ValueError(
                f"case {cid!r} has unknown scorer type {scorer['type']!r}; "
                f"known: {sorted(KNOWN_TYPES)}"
            )
    return data


def load_suite(path):
    data = yaml.safe_load(Path(path).read_text())
    return validate_suite(data)
