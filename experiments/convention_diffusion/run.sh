#!/usr/bin/env bash
# Study 2 full run: one resumable process per model (each writes only results/<model>/), then the analysis.
# Usage (from the repo root):  bash experiments/convention_diffusion/run.sh
# Re-running skips finished trials. Keys come from the env file (REVRES_VLLM_KEY); override with ENV_FILE=...
set -u
cd "$(dirname "$0")/../.."
EXP=experiments/convention_diffusion
ENV_FILE="${ENV_FILE:-../revoked-not-forgotten/.env}"
MODELS="${MODELS:-gemma-4-31b-it qwen3.8-27b ministral-3-14b gpt-oss-120b}"
SEEDS="${SEEDS:-48}"
for m in $MODELS; do
  PYTHONPATH=src python -m sord_exp.run --model "modal:$m" --seeds "$SEEDS" --workers 12 \
    --out "$EXP/results/$m" --env-file "$ENV_FILE" > "$EXP/results/$m.stdout" 2>&1 &
done
wait
PYTHONPATH=src python -m sord_exp.analyze --exp "$EXP"
