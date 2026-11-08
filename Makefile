PY ?= python
DATA ?= ../../03_Resources/datasets/collusion-wiki
OUT ?= results

.PHONY: test run report all

test:
	$(PY) -m pytest -q tests

run:
	PYTHONPATH=src $(PY) -m sord.run_all --data "$(DATA)" --out $(OUT)

report:
	PYTHONPATH=src $(PY) -m sord.report --out $(OUT)

all: test run report
