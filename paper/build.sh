#!/usr/bin/env bash
# Regenerate every number and table from both studies' result files, then compile main.pdf.
set -euo pipefail
cd "$(dirname "$0")"
python make_numbers.py
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
