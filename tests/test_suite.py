"""Suite loading + validation, and that the bundled suites are all valid."""
from pathlib import Path

import pytest

from eval_harness.suite import load_suite, validate_suite

SUITES_DIR = Path(__file__).resolve().parent.parent / "suites"


def test_bundled_suites_load():
    files = sorted(SUITES_DIR.glob("*.yaml"))
    assert files, "no bundled suites found"
    for f in files:
        suite = load_suite(f)
        assert suite["name"]
        assert suite["cases"]


def test_valid_minimal_suite():
    data = {"name": "x", "cases": [{"id": "a", "prompt": "hi", "scorer": {"type": "contains", "value": "y"}}]}
    assert validate_suite(data) is data


@pytest.mark.parametrize(
    "bad,msg",
    [
        ({"cases": []}, "name"),
        ({"name": "x"}, "cases"),
        ({"name": "x", "cases": []}, "cases"),
        ({"name": "x", "cases": [{"prompt": "p", "scorer": {"type": "contains", "value": "v"}}]}, "id"),
        ({"name": "x", "cases": [{"id": "a", "scorer": {"type": "contains", "value": "v"}}]}, "prompt"),
        ({"name": "x", "cases": [{"id": "a", "prompt": "p"}]}, "scorer"),
        ({"name": "x", "cases": [{"id": "a", "prompt": "p", "scorer": {"type": "nope"}}]}, "unknown scorer"),
        (
            {"name": "x", "cases": [
                {"id": "a", "prompt": "p", "scorer": {"type": "contains", "value": "v"}},
                {"id": "a", "prompt": "q", "scorer": {"type": "contains", "value": "w"}},
            ]},
            "duplicate",
        ),
    ],
)
def test_invalid_suites_raise(bad, msg):
    with pytest.raises(ValueError) as e:
        validate_suite(bad)
    assert msg in str(e.value)
