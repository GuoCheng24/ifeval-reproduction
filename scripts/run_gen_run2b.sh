#!/bin/bash
# Run 2b (PREREG_run2b.md, amendment to PREREG_run2.md): n=80 subsample, thinking ON, 16384-token budget.
# Detached, resume-safe (skips keys already in generations_run2b.jsonl).
# batch size 8 chosen from measured KV cost (~1.0 GB/seq at 16384 tok) to hold the 20 GB cap.
cd "$(dirname "$0")"
export CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
V=$VENV
exec $V/bin/python gen_ifeval_run2.py --data data/input_data_run2b.jsonl --out generations_run2b.jsonl --batch-size 8 --max-new-tokens 16384 --seed 0 --temperature 0.85 --top-p 0.95 --top-k 20 --presence-penalty 1.1
