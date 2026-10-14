# 60-second demo script

Goal: show the offline gate, a scorecard, and the headline regression diff.

## Setup (before recording)
```bash
make install
```

## Recording (~60s)

1. **The gate runs offline (0-10s).** Say "deterministic core, no network, no API key."
   ```bash
   make test
   ```
   Show: `41 passed`.

2. **Look at a suite (10-20s).** One screenful.
   ```bash
   sed -n '1,20p' suites/json_extraction.yaml
   ```
   Point at `scorer: {type: json_schema ...}` and `json_field_equals`.

3. **Run a suite -> scorecard (20-40s).** With a local ollama up:
   ```bash
   python -m eval_harness run suites/qa.yaml
   ```
   Show the Markdown scorecard + pass rate. (No model handy? Skip to step 4 — it is the
   headline and runs offline.)

4. **Regression diff — the headline (40-60s).**
   ```bash
   make diff
   ```
   Show "Newly failing: `water_formula`", "Newly passing: `boiling_point`", pass-rate
   delta. Say "this is the CI gate — it exits non-zero when something newly breaks."

## One-liner to narrate
"Define evals in YAML, score them with rules not vibes, and diff two runs to catch the
exact case a prompt change broke — before shipping it."
