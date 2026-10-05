import json
import os
import shutil
import sys

import torch
from transformers import GPT2Config, GPT2LMHeadModel, LlamaConfig, LlamaForCausalLM

ckpt, run = sys.argv[1], sys.argv[2]
state = torch.load(ckpt, map_location="cpu", weights_only=False)
out = os.path.join(run, f"hf-{state['step']}")
if state["arch"] == "gpt2":
    model = GPT2LMHeadModel(GPT2Config.from_dict(state["config"]))
else:
    model = LlamaForCausalLM(LlamaConfig.from_dict(state["config"]))
model.load_state_dict(state["model"])
model.config.use_cache = True
os.makedirs(out, exist_ok=True)
model.save_pretrained(out)
tok_dir = state["meta"]["tokenizer"]
for f in os.listdir(tok_dir):
    shutil.copy(os.path.join(tok_dir, f), os.path.join(out, f))
cfg_path = os.path.join(out, "tokenizer_config.json")
with open(cfg_path) as f:
    tcfg = json.load(f)
tcfg["add_bos_token"] = True
with open(cfg_path, "w") as f:
    json.dump(tcfg, f, indent=1)
print(f"exported step {state['step']} ({state['tokens']:,} tokens, eval {state.get('last_eval')}) to {out}", file=sys.stderr)
print(out)
