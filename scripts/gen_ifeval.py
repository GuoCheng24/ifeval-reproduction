#!/usr/bin/env python
"""IFEval generation harness for InternScience/Agents-A1-4B (plain transformers, greedy, bf16).

Crash-proof: appends one JSON line per prompt to --out as soon as its batch finishes,
and on restart skips every `key` already present in --out (resume-by-id).
"""
import argparse, json, os, sys, time, math
import torch

SNAPSHOT = os.path.expanduser(
    "~/.cache/huggingface/hub/models--InternScience--Agents-A1-4B/snapshots/945c40a4aa6f534d434a353207b8d42ecf7a5293")

def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)

def strip_think(text: str) -> str:
    # remove a leading <think>...</think> block if present (defensive; with enable_thinking=False
    # the empty think block is part of the prompt, not the generation)
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return text.lstrip("\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-new-tokens", type=int, default=1280)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--enable-thinking", type=int, default=0)
    ap.add_argument("--system", default="template_default",
                    help="'template_default' = no system message (template injects its own); 'none' = empty system; or literal text")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    from transformers import AutoTokenizer, AutoModelForImageTextToText
    tok = AutoTokenizer.from_pretrained(SNAPSHOT)
    tok.padding_side = "left"
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    t0 = time.time()
    model = AutoModelForImageTextToText.from_pretrained(SNAPSHOT, dtype=torch.bfloat16, device_map="cuda")
    model.eval()
    log(f"model loaded in {time.time()-t0:.1f}s; class={type(model).__name__}; dtype={next(model.parameters()).dtype}; "
        f"device={next(model.parameters()).device}; mem_alloc={torch.cuda.memory_allocated()/2**30:.2f}GB")
    eos_ids = model.generation_config.eos_token_id
    log(f"generation_config eos={eos_ids} pad={model.generation_config.pad_token_id}")

    rows = [json.loads(l) for l in open(args.data) if l.strip()]
    if args.limit:
        rows = rows[: args.limit]
    done = set()
    if os.path.exists(args.out):
        for l in open(args.out):
            try:
                done.add(json.loads(l)["key"])
            except Exception:
                pass
    todo = [r for r in rows if r["key"] not in done]
    log(f"total={len(rows)} already_done={len(done)} todo={len(todo)}")

    def build(prompt):
        msgs = []
        if args.system == "none":
            msgs.append({"role": "system", "content": ""})
        elif args.system != "template_default":
            msgs.append({"role": "system", "content": args.system})
        msgs.append({"role": "user", "content": prompt})
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True,
                                       enable_thinking=bool(args.enable_thinking))
    texts = {r["key"]: build(r["prompt"]) for r in todo}
    if todo:
        log("=== example templated prompt (key %s) ===\n%s\n=== end ===" % (todo[0]["key"], texts[todo[0]["key"]]))
    # sort by prompt length so batches have similar padding
    todo.sort(key=lambda r: len(tok(texts[r["key"]]).input_ids))

    gen_kwargs = dict(do_sample=False, max_new_tokens=args.max_new_tokens, temperature=None, top_p=None, top_k=None,
                      repetition_penalty=1.0, pad_token_id=tok.pad_token_id)
    settings = dict(do_sample=False, max_new_tokens=args.max_new_tokens, dtype="bfloat16", seed=args.seed,
                    enable_thinking=bool(args.enable_thinking), system=args.system, batch_size=args.batch_size,
                    snapshot=os.path.basename(SNAPSHOT), decoding="greedy")
    total_new = 0; t_start = time.time(); n_done = 0
    with open(args.out, "a") as fout:
        for b in range(0, len(todo), args.batch_size):
            batch = todo[b: b + args.batch_size]
            enc = tok([texts[r["key"]] for r in batch], return_tensors="pt", padding=True).to("cuda")
            tb = time.time()
            with torch.inference_mode():
                out = model.generate(**enc, **gen_kwargs)
            gen = out[:, enc.input_ids.shape[1]:]
            dt = time.time() - tb
            new_tok_batch = 0
            for i, r in enumerate(batch):
                ids = gen[i].tolist()
                # count real generated tokens (stop at first eos / pad after content)
                n_new = len(ids)
                finished = False
                for j, t in enumerate(ids):
                    if t == tok.pad_token_id or (isinstance(eos_ids, list) and t in eos_ids) or t == eos_ids:
                        n_new = j; finished = True; break
                raw = tok.decode(ids[:n_new], skip_special_tokens=True)
                new_tok_batch += n_new
                rec = dict(key=r["key"], prompt=r["prompt"], instruction_id_list=r["instruction_id_list"], kwargs=r["kwargs"],
                           response=strip_think(raw), raw_response=raw, n_new_tokens=n_new, finished=finished,
                           prompt_tokens=int(enc.attention_mask[i].sum()), seed=args.seed, settings=settings,
                           batch_wall_s=round(dt, 2), ts=time.time())
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fout.flush(); os.fsync(fout.fileno())
            total_new += new_tok_batch; n_done += len(batch)
            el = time.time() - t_start
            log(f"batch {b//args.batch_size+1}/{math.ceil(len(todo)/args.batch_size)} done={n_done}/{len(todo)} "
                f"batch_new_tok={new_tok_batch} batch_tok/s={new_tok_batch/dt:.1f} cum_tok/s={total_new/el:.1f} "
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
