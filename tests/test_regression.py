"""Regression diff: two synthetic runs -> expected newly-failing/passing + delta."""
import json
from pathlib import Path

from eval_harness.regression import diff_runs, to_markdown

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _run(pass_rate, results):
    return {"suite": "s", "pass_rate": pass_rate,
            "results": [{"id": i, "passed": p} for i, p in results]}


def test_diff_synthetic():
    a = _run(0.5, [("keep_pass", True), ("regressed", True), ("keep_fail", False), ("fixed", False), ("gone", True)])
    b = _run(0.75, [("keep_pass", True), ("regressed", False), ("keep_fail", False), ("fixed", True), ("added", True)])
    d = diff_runs(a, b)
    assert d["newly_failing"] == ["regressed"]
    assert d["newly_passing"] == ["fixed"]
    assert d["added"] == ["added"]
    assert d["removed"] == ["gone"]
    assert d["pass_rate_delta"] == 0.25


def test_diff_no_changes():
    a = _run(1.0, [("x", True), ("y", True)])
    d = diff_runs(a, a)
    assert d["newly_failing"] == [] and d["newly_passing"] == []
    assert d["added"] == [] and d["removed"] == [] and d["pass_rate_delta"] == 0.0


def test_diff_bundled_examples():
    a = json.loads((EXAMPLES / "run_baseline.json").read_text())
    b = json.loads((EXAMPLES / "run_new.json").read_text())
    d = diff_runs(a, b)
    assert d["newly_failing"] == ["water_formula"]
    assert d["newly_passing"] == ["boiling_point"]
    assert d["added"] == ["mountain_height"]
    md = to_markdown(d)
    assert "Regression diff" in md and "water_formula" in md
