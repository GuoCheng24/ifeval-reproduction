#!/bin/bash
# Run 3a (PREREG_run3.md): thinking ON, card sampling, the 80 pre-registered keys, 16384-token budget.
# Arms 3a and 3b are identical except for batch size (16 vs 8) - that is the manipulated variable.
# machine-b, one L40, no memory cap and no time cap. Resume-safe by key.
cd "$(dirname "$0")/.."
export CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
V=$VENV   # a1eval: torch 2.10.0+cu128, transformers 5.16.1, nltk 3.8.1 (see results/env.txt)
exec $VENV/bin/python scripts/gen_ifeval_run2.py --data data/input_data_run3_n80.jsonl --out generations_run3a_n80_bs16.jsonl \
  --batch-size 16 --max-new-tokens 16384 --seed 0 --temperature 0.85 --top-p 0.95 --top-k 20 --presence-penalty 1.1
