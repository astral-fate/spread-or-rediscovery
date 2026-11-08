PY ?= python
DATA ?= ../../03_Resources/datasets/collusion-wiki
OUT ?= results

.PHONY: test run poscontrol report all

test:
	$(PY) -m pytest -q tests

run:
	PYTHONPATH=src $(PY) -m sord.run_all --data "$(DATA)" --out $(OUT)

poscontrol:
	PYTHONPATH=src $(PY) -m sord.poscontrol --data "$(DATA)" --out $(OUT) --reps 200

report:
	PYTHONPATH=src $(PY) -m sord.report --out $(OUT)

all: test run poscontrol report
