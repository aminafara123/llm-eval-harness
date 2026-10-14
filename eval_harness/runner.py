"""Run a suite against the model under test and collect scored results.

The runner is deterministic given (suite, chat_fn outputs): it renders prompts,
calls the model, scores each output, and aggregates. A model failure on one case is
recorded as a failed case -- it never aborts the run.
"""
import time
from datetime import datetime, timezone
from string import Template

from . import llm
from .scorers import score


def render(prompt, vars):
    """Substitute $var placeholders. Uses Template so JSON braces in prompts are safe."""
    if not vars:
        return prompt
    return Template(prompt).safe_substitute(vars)


def run_suite(suite, chat_fn=None, judge_fn=None):
    """Execute every case and return a run dict (ready to save as JSON / render as md).

    chat_fn(prompt, system=None) -> str. Defaults to the thin llm.chat client.
    judge_fn(prompt) -> str is only used by optional llm_judge scorers.
    """
    chat_fn = chat_fn or llm.chat
    results = []
    for case in suite["cases"]:
        prompt = render(case["prompt"], case.get("vars"))
        output, error = "", None
        t0 = time.perf_counter()
        try:
            output = chat_fn(prompt, system=case.get("system"))
        except Exception as e:  # noqa: BLE001 -- model is external; one bad case != dead run
            error = f"{type(e).__name__}: {e}"
        latency_ms = round((time.perf_counter() - t0) * 1000)

        if error is not None:
            passed, detail = False, f"model call failed: {error}"
        else:
            sr = score(output, case["scorer"], judge=judge_fn)
            passed, detail = sr.passed, sr.detail

        results.append(
            {
                "id": case["id"],
                "scorer": case["scorer"]["type"],
                "passed": passed,
                "detail": detail,
                "prompt": prompt,
                "output": output,
                "latency_ms": latency_ms,
                "error": error,
            }
        )
    return aggregate(suite["name"], results)


def aggregate(suite_name, results):
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    latencies = [r["latency_ms"] for r in results if r["error"] is None]
    return {
        "suite": suite_name,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else None,
        "results": results,
    }
