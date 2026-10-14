"""Regression diff between two run JSONs -- the headline feature.

Deterministic: given run A (baseline) and run B (new), report which cases newly fail,
which newly pass, which were added/removed, and the pass-rate delta. No model involved.
"""


def diff_runs(run_a, run_b):
    a = {r["id"]: bool(r["passed"]) for r in run_a["results"]}
    b = {r["id"]: bool(r["passed"]) for r in run_b["results"]}
    common = a.keys() & b.keys()
    return {
        "suite": run_b.get("suite", run_a.get("suite")),
        "newly_failing": sorted(i for i in common if a[i] and not b[i]),
        "newly_passing": sorted(i for i in common if not a[i] and b[i]),
        "added": sorted(b.keys() - a.keys()),
        "removed": sorted(a.keys() - b.keys()),
        "pass_rate_a": run_a.get("pass_rate", 0.0),
        "pass_rate_b": run_b.get("pass_rate", 0.0),
        "pass_rate_delta": round(run_b.get("pass_rate", 0.0) - run_a.get("pass_rate", 0.0), 4),
    }


def to_markdown(d):
    def _lst(items):
        return ", ".join(f"`{i}`" for i in items) if items else "_none_"

    arrow = "+" if d["pass_rate_delta"] >= 0 else ""
    return "\n".join(
        [
            f"# Regression diff: {d['suite']}",
            "",
            f"- Pass rate: {d['pass_rate_a'] * 100:.1f}% -> {d['pass_rate_b'] * 100:.1f}% "
            f"(**{arrow}{d['pass_rate_delta'] * 100:.1f} pts**)",
            f"- Newly failing ({len(d['newly_failing'])}): {_lst(d['newly_failing'])}",
            f"- Newly passing ({len(d['newly_passing'])}): {_lst(d['newly_passing'])}",
            f"- Added cases: {_lst(d['added'])}",
            f"- Removed cases: {_lst(d['removed'])}",
            "",
        ]
    )
