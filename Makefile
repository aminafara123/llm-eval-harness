PY ?= python3
VENV = .venv
BIN = $(VENV)/bin

.PHONY: install test run diff clean

install:
	$(PY) -m venv $(VENV)
	$(BIN)/pip install -U pip
	$(BIN)/pip install -r requirements.txt

test:
	$(BIN)/pytest -q

# Run an eval suite against the model under test (needs a reachable LLM; default = local ollama).
run:
	$(BIN)/python -m eval_harness run suites/qa.yaml

# Regression diff of the two bundled example runs -- works offline, no model needed.
diff:
	$(BIN)/python -m eval_harness diff examples/run_baseline.json examples/run_new.json

clean:
	rm -rf $(VENV) .pytest_cache runs **/__pycache__
