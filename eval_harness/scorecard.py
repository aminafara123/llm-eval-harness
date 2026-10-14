"""Render a run dict as a Markdown scorecard. (JSON output is just the run dict.)"""


def _pct(x):
    return f"{x * 100:.1f}%"


def to_markdown(run):
    uses_judge = any(r["scorer"] == "llm_judge" for r in run["results"])
    lines = [
        f"# Scorecard: {run['suite']}",
        "",
        f"- Generated: {run['generated_at']}",
        f"- Pass rate: **{_pct(run['pass_rate'])}** ({run['passed']}/{run['total']})",
    ]
    if run.get("avg_latency_ms") is not None:
        lines.append(f"- Avg latency: {run['avg_latency_ms']} ms")
    lines += ["", "| Case | Scorer | Result | Detail | Latency |", "|---|---|---|---|---|"]
    for r in run["results"]:
        mark = "PASS" if r["passed"] else "FAIL"
        detail = str(r["detail"]).replace("|", "\\|")
        lines.append(f"| {r['id']} | {r['scorer']} | {mark} | {detail} | {r['latency_ms']} ms |")
    lines += [
        "",
        "> Scores come from deterministic scorers. Any `llm_judge` rows are "
        "**AI-generated and advisory** and a human must review them."
        if uses_judge
        else "> Scores come from deterministic scorers (no AI judgement in this run).",
        "",
    ]
    return "\n".join(lines)
