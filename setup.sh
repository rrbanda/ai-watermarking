#!/usr/bin/env bash
# Create .venv at the repo root with the vLLM build the recipes were verified on.
set -euo pipefail
cd "$(dirname "$0")"

uv venv .venv --python 3.12
uv pip install --python .venv/bin/python "vllm==0.32.0"
.venv/bin/python -c "import vllm; print('vLLM', vllm.__version__)"
