"""CLI: run an eval suite, or diff two runs for regressions.

    python -m eval_harness run suites/qa.yaml
    python -m eval_harness run suites/qa.yaml -o runs/qa.json
    python -m eval_harness diff runs/baseline.json runs/new.json

`run` saves <out>.json + <out>.md and prints the scorecard. If the model is
unreachable, affected cases are marked FAIL (the run still completes).
"""
import argparse
import json
import sys
from pathlib import Path

from . import llm, regression, scorecard
from .runner import run_suite
from .suite import load_suite


def _cmd_run(args):
    suite = load_suite(args.suite)
    judge = llm.chat if args.judge else None  # optional, advisory; off by default
    run = run_suite(suite, judge_fn=judge)

    out = Path(args.out) if args.out else Path("runs") / f"{suite['name']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(run, indent=2))
    md = scorecard.to_markdown(run)
    out.with_suffix(".md").write_text(md)

    print(md)
    print(f"Saved: {out} and {out.with_suffix('.md')}")
    return 0 if run["failed"] == 0 else 1


def _cmd_diff(args):
    run_a = json.loads(Path(args.run_a).read_text())
    run_b = json.loads(Path(args.run_b).read_text())
    d = regression.diff_runs(run_a, run_b)
    print(regression.to_markdown(d))
    # Exit non-zero if anything newly broke -- handy as a CI gate.
    return 1 if d["newly_failing"] else 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="eval_harness", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run an eval suite -> scorecard")
    r.add_argument("suite", help="path to a suite YAML")
    r.add_argument("-o", "--out", help="output JSON path (default runs/<name>.json)")
    r.add_argument("--judge", action="store_true",
                   help="enable optional llm_judge scorers (AI-generated, advisory)")
    r.set_defaults(func=_cmd_run)

    d = sub.add_parser("diff", help="compare two run JSONs for regressions")
    d.add_argument("run_a", help="baseline run JSON")
    d.add_argument("run_b", help="new run JSON")
    d.set_defaults(func=_cmd_diff)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
