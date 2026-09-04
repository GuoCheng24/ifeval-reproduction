# Pre-registration: IFEval run 2 (the model card's recommended setting)

Written 2026-09-04 12:40, BEFORE run 2 is started, AFTER run 1 (plain setting) scored 76.9 prompt-strict.
Purpose: a fair comparison against the card's 94.8. Run 1 deviated from the card in decoding and thinking
mode; run 2 removes those deviations. Nothing below may be changed after generation starts.

## Fixed settings
- Model: same snapshot as run 1 (sha256 in env.txt). Same 541 prompts (google-research input_data.jsonl).
- Decoding: EXACTLY the card's recommendation — temperature 0.85, top_p 0.95, top_k 20, presence_penalty 1.1.
- Thinking: ON (the template's default), max_new_tokens 4096 so <think> has room; the answer scored is
  the text AFTER the closing </think> tag (raw_response kept for audit). If a response has no closing tag,
  it is scored as-is and counted as "unclosed".
- Seed: 0 for the sampler (single seed; a second seed only if the first lands within 2 points of 94.8).
- Backend: vLLM 0.10.1.1 in envs/vllm010 if the install succeeds and `import vllm` works with CUDA;
  otherwise transformers generate() as in run 1 (slower, same settings). Backend recorded in RESULTS.
- Scorer: identical vendored official code, run 1 time (its non-determinism is documented; report run 1).

## Pre-stated interpretation
- If run 2 prompt-strict >= 91.8 (within 3 of the card): the card's number reproduces under its own
  recommended setting; run 1's gap is a decoding/thinking effect. Report both, no "inflation" claim.
- If run 2 lands in 82-91.8: partially reproduces; report the gap and the two settings side by side.
- If run 2 < 82: the card's number does not reproduce under the card's own setting on this hardware.
  Even then the honest sentence is "we could not reproduce 94.8 under the stated recommendation";
  NOT "the number is fabricated" — thinking budget, vLLM version and sampling seed remain uncontrolled.
- Controls from run 1 (empty / echo / compliant) are re-used unchanged.
- Cost cap: if the run exceeds 3 hours or 20 GB, stop and report partial with the prompt count.
