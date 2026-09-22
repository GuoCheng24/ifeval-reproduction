#!/bin/bash
# Run 3c (PREREG_run3.md): thinking OFF, greedy, all 541 prompts, 1280-token budget, batch size 24.
# Byte-identical settings to run 1; the only change is RTX 4090 -> L40. Greedy, so no sampling noise.
cd "$(dirname "$0")/.."
export CUDA_VISIBLE_DEVICES=3 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
V=$VENV   # a1eval: torch 2.10.0+cu128, transformers 5.16.1, nltk 3.8.1 (see results/env.txt)
exec $VENV/bin/python scripts/gen_ifeval.py --data data/input_data.jsonl --out generations_run3d_full541.jsonl \
  --batch-size 24 --max-new-tokens 1280 --seed 0 --enable-thinking 0 --system template_default
