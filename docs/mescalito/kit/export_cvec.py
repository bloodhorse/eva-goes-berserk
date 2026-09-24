# export_cvec.py: one gguf per vector, index s-1, pre-scaled by R (so the runtime scale sweeps xR)
import sys, torch, numpy as np, gguf
bank = torch.load(sys.argv[1]); arch_hint = sys.argv[2]          # "llama" for nemo, "olmo2" for olmo
out = sys.argv[3] if len(sys.argv) > 3 else "cv"                  # one dir per model: a bank never crosses models
il = bank["s"] - 1
for rank, k in enumerate(bank["alpha"].pow(2).argsort(descending=True).tolist()):
    w = gguf.GGUFWriter(f"{out}/{rank:03d}_f{k}.gguf", "controlvector")  # sets general.architecture
    w.add_string("controlvector.model_hint", arch_hint)
    w.add_int32("controlvector.layer_count", 1)
    w.add_tensor(f"direction.{il}", (bank["R"] * bank["V"][:, k]).numpy().astype(np.float32))
    w.write_header_to_file(); w.write_kv_data_to_file(); w.write_tensors_to_file(); w.close()
