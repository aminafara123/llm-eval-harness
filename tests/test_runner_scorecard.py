"""Runner with a mocked model (no network), aggregation, and scorecard rendering."""
from eval_harness import scorecard
from eval_harness.runner import aggregate, render, run_suite

SUITE = {
    "name": "mini",
    "cases": [
        {"id": "c1", "prompt": "capital of France?", "scorer": {"type": "contains", "value": "Paris"}},
        {"id": "c2", "prompt": "2+2?", "scorer": {"type": "numeric", "value": 4, "tolerance": 0}},
        {"id": "c3", "prompt": "say hi", "scorer": {"type": "contains", "value": "nope"}},
    ],
}

# Deterministic fake model: answers keyed by prompt substring.
FAKE = {"France": "The capital is Paris.", "2+2": "4", "hi": "hello there"}


def fake_chat(prompt, system=None):
    for k, v in FAKE.items():
        if k in prompt:
            return v
    return ""


def test_run_suite_scores_each_case():
    run = run_suite(SUITE, chat_fn=fake_chat)
    by_id = {r["id"]: r for r in run["results"]}
    assert by_id["c1"]["passed"] is True
    assert by_id["c2"]["passed"] is True
    assert by_id["c3"]["passed"] is False
    assert run["total"] == 3 and run["passed"] == 2 and run["failed"] == 1
    assert run["pass_rate"] == round(2 / 3, 4)


def test_model_failure_is_per_case_not_crash():
    def boom(prompt, system=None):
        raise ConnectionError("connection refused")

    run = run_suite(SUITE, chat_fn=boom)
    assert run["passed"] == 0 and run["failed"] == 3
    for r in run["results"]:
        assert r["passed"] is False
        assert "model call failed" in r["detail"]
        assert r["error"] and "ConnectionError" in r["error"]


def test_render_templating():
    assert render("Hi $name", {"name": "Al"}) == "Hi Al"
    # JSON braces survive (Template uses $, not {})
    assert render('return {"a": 1} for $x', {"x": "y"}) == 'return {"a": 1} for y'
    assert render("no vars", None) == "no vars"


def test_aggregate_empty():
    run = aggregate("empty", [])
    assert run["total"] == 0 and run["pass_rate"] == 0.0 and run["avg_latency_ms"] is None


def test_scorecard_markdown():
    run = run_suite(SUITE, chat_fn=fake_chat)
    md = scorecard.to_markdown(run)
    assert "# Scorecard: mini" in md
    assert "Pass rate" in md and "PASS" in md and "FAIL" in md
    assert "| c1 |" in md
    # No llm_judge in this run -> the no-AI note is shown.
    assert "no AI judgement" in md
