# Addendum to PREREG_run3.md — arm 3d, a same-machine repeat

Written **2026-09-23 00:40 (Asia/Shanghai)**, BEFORE arm 3d has been started.

## Stated plainly: this was decided after seeing arm 3c's score

Arm 3c finished and scored 75.42% prompt-level strict against run 1's 76.89% on
the same 541 prompts, the same weights, the same batch size, the same seed and
greedy decoding — a 1.47-point difference whose only intended cause is the GPU
model. `PREREG_run3.md` called that comparison "the clean hardware test" and
said any difference there would be the headline.

It is not clean enough, and the gap in it is mine. Greedy decoding is
deterministic *given the kernels*; it is not guaranteed to be bit-reproducible
across two runs on the same card, because reductions in these kernels need not
be run-to-run stable. Arm 3c therefore cannot, on its own, separate

* a difference between an RTX 4090 and an L40, from
* a difference between any two runs of this model on any one card.

No arm in `PREREG_run3.md` distinguishes those, so the headline it authorises is
not supported. Arm 3d is the missing control.

## Arm 3d

Byte-identical invocation to arm 3c — same script, same 541 prompts, same
`--batch-size 24 --max-new-tokens 1280 --seed 0 --enable-thinking 0`, same
scorer — run a second time on **gpu-03**, on a different idle L40 of the same
model. Nothing else changes.

## Pre-stated interpretation, committed before the result exists

- **If 3d reproduces 3c exactly** (identical per-prompt strict outcomes, and
  ideally identical generated text), then this model's greedy decoding is
  reproducible within a machine, and the 4090-to-L40 difference is attributable
  to hardware and kernels. That is the claim `PREREG_run3.md` wanted.
- **If 3d differs from 3c**, the 4090-to-L40 comparison is **not** attributable
  to hardware, and will not be written as if it were. The reportable quantity
  becomes the run-to-run spread of a benchmark score under a decoder that is
  supposed to have none — which is a more useful number than the one this was
  meant to produce, and it will be reported with the same prominence.
- Either way the comparison is reported as **prompt-level strict accuracy, the
  count of prompts whose strict outcome differs, and the count of prompts whose
  generated text is byte-identical**, with an exact McNemar on the discordant
  pairs. The token-count distribution and the finished/unfinished counts are
  reported alongside.
- Run 1's per-prompt record was not preserved, so the 4090-to-L40 comparison
  remains limited to aggregate metrics however 3d comes out. 3c and 3d can be
  compared prompt by prompt because both now write a per-prompt table.

**No further amendment will be made on the basis of seeing arm 3d's score.**
