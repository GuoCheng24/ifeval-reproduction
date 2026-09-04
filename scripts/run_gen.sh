#!/bin/bash
# Detached launcher: resume-safe (gen_ifeval.py skips keys already in generations.jsonl)
cd "$(dirname "$0")"
export CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
V=$VENV
exec $V/bin/python gen_ifeval.py --data data/input_data.jsonl --out generations.jsonl --batch-size 24 --max-new-tokens 1280 --seed 0 --enable-thinking 0 --system template_default
