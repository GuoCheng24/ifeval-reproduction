#!/bin/bash
# Run 2 (PREREG_run2.md): detached, resume-safe (skips keys already in generations_run2.jsonl)
cd "$(dirname "$0")"
export CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
V=$VENV
exec $V/bin/python gen_ifeval_run2.py --data data/input_data.jsonl --out generations_run2.jsonl --batch-size 24 --max-new-tokens 4096 --seed 0 --temperature 0.85 --top-p 0.95 --top-k 20 --presence-penalty 1.1
