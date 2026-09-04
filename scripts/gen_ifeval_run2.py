#!/usr/bin/env python
"""IFEval run 2 harness — the model card's recommended setting, per PREREG_run2.md:
sampling T=0.85 / top_p=0.95 / top_k=20 / presence_penalty=1.1, thinking ON, max_new_tokens=4096, seed 0,
plain transformers generate() (vLLM fallback branch of the pre-registration).

presence_penalty is not a transformers option; it is implemented here as a LogitsProcessor with vLLM/OpenAI
semantics: logits[t] -= 1.1 for every token t already present in the GENERATED output of that sequence.

Crash-proof: appends one JSON line per prompt; on restart skips keys already present (resume-by-id).
"""
import argparse, json, os, time, math
import torch
from transformers import LogitsProcessor, LogitsProcessorList

SNAPSHOT = os.path.expanduser(
    "~/.cache/huggingface/hub/models--InternScience--Agents-A1-4B/snapshots/945c40a4aa6f534d434a353207b8d42ecf7a5293")

def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)

class PresencePenalty(LogitsProcessor):
    """vLLM-style additive presence penalty on tokens present in the generated part of each sequence."""
    def __init__(self, penalty: float, prompt_len: int):
        self.penalty = penalty; self.prompt_len = prompt_len
    def __call__(self, input_ids, scores):
        out = input_ids[:, self.prompt_len:]
        if out.shape[1] == 0:
            return scores
        present = torch.zeros_like(scores, dtype=torch.bool)
        present.scatter_(1, out, True)
        return scores - self.penalty * present.to(scores.dtype)

def split_think(raw: str):
    """Return (answer, closed). Generation starts inside <think> (the prompt ends with '<think>\\n')."""
    if "</think>" in raw:
        return raw.split("</think>", 1)[1].lstrip("\n"), True
    return raw, False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch-size", type=int, default=48)
    ap.add_argument("--max-new-tokens", type=int, default=4096)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--temperature", type=float, default=0.85)
    ap.add_argument("--top-p", type=float, default=0.95)
    ap.add_argument("--top-k", type=int, default=20)
    ap.add_argument("--presence-penalty", type=float, default=1.1)
    args = ap.parse_args()

    torch.manual_seed(args.seed); torch.cuda.manual_seed_all(args.seed)
    from transformers import AutoTokenizer, AutoModelForImageTextToText
    tok = AutoTokenizer.from_pretrained(SNAPSHOT)
    tok.padding_side = "left"
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    t0 = time.time()
    model = AutoModelForImageTextToText.from_pretrained(SNAPSHOT, dtype=torch.bfloat16, device_map="cuda")
    model.eval()
    log(f"model loaded in {time.time()-t0:.1f}s; class={type(model).__name__}; dtype={next(model.parameters()).dtype}; "
        f"mem_alloc={torch.cuda.memory_allocated()/2**30:.2f}GB")
    eos_ids = model.generation_config.eos_token_id
    eos_set = set(eos_ids) if isinstance(eos_ids, list) else {eos_ids}
    log(f"generation_config eos={eos_ids}")

    rows = [json.loads(l) for l in open(args.data) if l.strip()]
    if args.limit:
        rows = rows[: args.limit]
    done = set()
    if os.path.exists(args.out):
        for l in open(args.out):
            try: done.add(json.loads(l)["key"])
            except Exception: pass
    todo = [r for r in rows if r["key"] not in done]
    log(f"total={len(rows)} already_done={len(done)} todo={len(todo)}")

    def build(prompt):
        # no system message -> template injects its own default system prompt; thinking ON = template default
        return tok.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=True)
    texts = {r["key"]: build(r["prompt"]) for r in todo}
    if todo:
        ex = texts[todo[0]["key"]]
        log("=== example templated prompt tail (key %s) ===\n%s\n=== end ===" % (todo[0]["key"], ex[-400:]))
        assert ex.endswith("<think>\n"), "thinking mode expected: prompt should end with '<think>\\n'"
    todo.sort(key=lambda r: len(tok(texts[r["key"]]).input_ids))

    settings = dict(do_sample=True, temperature=args.temperature, top_p=args.top_p, top_k=args.top_k,
                    presence_penalty=args.presence_penalty, presence_penalty_impl="custom LogitsProcessor, vLLM semantics (additive, generated tokens only)",
                    repetition_penalty=1.0, max_new_tokens=args.max_new_tokens, dtype="bfloat16", seed=args.seed,
                    enable_thinking=True, system="template_default", batch_size=args.batch_size,
                    backend=f"transformers generate()", snapshot=os.path.basename(SNAPSHOT), prereg="PREREG_run2.md")
    total_new = 0; t_start = time.time(); n_done = 0
    with open(args.out, "a") as fout:
        for b in range(0, len(todo), args.batch_size):
            batch = todo[b: b + args.batch_size]
            enc = tok([texts[r["key"]] for r in batch], return_tensors="pt", padding=True).to("cuda")
            plen = enc.input_ids.shape[1]
            tb = time.time()
            with torch.inference_mode():
                out = model.generate(**enc, do_sample=True, temperature=args.temperature, top_p=args.top_p, top_k=args.top_k,
                                     repetition_penalty=1.0, max_new_tokens=args.max_new_tokens, pad_token_id=tok.pad_token_id,
                                     logits_processor=LogitsProcessorList([PresencePenalty(args.presence_penalty, plen)]),
                                     logits_to_keep=1)
            gen = out[:, plen:]
            dt = time.time() - tb
            new_tok_batch = 0; n_closed = 0
            for i, r in enumerate(batch):
                ids = gen[i].tolist()
                n_new = len(ids); finished = False
                for j, t in enumerate(ids):
                    if t == tok.pad_token_id or t in eos_set:
                        n_new = j; finished = True; break
                raw = tok.decode(ids[:n_new], skip_special_tokens=True)
                answer, closed = split_think(raw)
                n_closed += closed
                new_tok_batch += n_new
                rec = dict(key=r["key"], prompt=r["prompt"], instruction_id_list=r["instruction_id_list"], kwargs=r["kwargs"],
                           response=answer, raw_response=raw, think_closed=closed, n_new_tokens=n_new, finished=finished,
                           prompt_tokens=int(enc.attention_mask[i].sum()), seed=args.seed, settings=settings,
                           batch_wall_s=round(dt, 2), ts=time.time())
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fout.flush(); os.fsync(fout.fileno())
            total_new += new_tok_batch; n_done += len(batch)
            el = time.time() - t_start
            log(f"batch {b//args.batch_size+1}/{math.ceil(len(todo)/args.batch_size)} done={n_done}/{len(todo)} "
                f"batch_new_tok={new_tok_batch} think_closed={n_closed}/{len(batch)} batch_tok/s={new_tok_batch/dt:.1f} cum_tok/s={total_new/el:.1f} "
                f"cum_prompt/s={n_done/el:.3f} peak_mem={torch.cuda.max_memory_allocated()/2**30:.2f}GB eta_min={(len(todo)-n_done)/(n_done/el)/60:.1f}")
    el = time.time() - t_start
    log(f"DONE n={n_done} new_tokens={total_new} wall_s={el:.1f} tok/s={total_new/max(el,1e-9):.1f} "
        f"peak_mem_GB={torch.cuda.max_memory_allocated()/2**30:.2f} gpu={os.environ.get('CUDA_VISIBLE_DEVICES')}")
    json.dump(dict(n=n_done, new_tokens=total_new, wall_s=el, tok_per_s=total_new/max(el,1e-9),
                   peak_mem_GB=torch.cuda.max_memory_allocated()/2**30, gpu=os.environ.get("CUDA_VISIBLE_DEVICES"),
                   settings=settings, gpu_name=torch.cuda.get_device_name(0)),
              open(args.out + ".runstats.json", "a"), indent=1)

if __name__ == "__main__":
    main()
