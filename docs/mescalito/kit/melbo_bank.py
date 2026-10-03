# melbo_bank.py: exponential DCT (OGI) bank of residual steering vectors, hooks-only.
# theta is added to the residual stream at the INPUT of HF layer s (== hidden_states[s]),
# the change is read at the OUTPUT of layer t-1 (== hidden_states[t]), last `--last` positions.
import argparse, json, torch, torch.nn.functional as F
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

p = argparse.ArgumentParser()
p.add_argument("--model", required=True); p.add_argument("--revision", default=None)
p.add_argument("--seeds", nargs="+", required=True)   # seed .txt files, 8-12 of them
p.add_argument("--s", type=int, default=10); p.add_argument("--t", type=int, default=20)
p.add_argument("--m", type=int, default=256); p.add_argument("--iters", type=int, default=10)
p.add_argument("--chunk", type=int, default=32); p.add_argument("--last", type=int, default=3)
p.add_argument("--R", type=float, default=None); p.add_argument("--lam", type=float, default=0.5)
p.add_argument("--bits", type=int, default=16); p.add_argument("--bos", type=int, default=1)
p.add_argument("--budget", type=int, default=0); p.add_argument("--slice", type=int, default=0)
p.add_argument("--out", default="bank.pt")
p.add_argument("--device", default="cuda")             # "mps"/"cpu" for a dry run on the mac with a toy model
a = p.parse_args()
dev = torch.device(a.device)

cfg = AutoConfig.from_pretrained(a.model, revision=a.revision)
tc = getattr(cfg, "text_config", cfg)                  # Mistral3 keeps the LM under text_config
tc.num_hidden_layers = a.t                             # never load layers >= t: halves the memory
if getattr(tc, "layer_types", None): tc.layer_types = tc.layer_types[:a.t]
kw = dict(revision=a.revision, config=cfg, torch_dtype=torch.bfloat16, device_map="cpu" if a.slice else a.device)
if a.bits == 4:
    from transformers import BitsAndBytesConfig
    kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                   bnb_4bit_compute_dtype=torch.bfloat16)
model = AutoModelForCausalLM.from_pretrained(a.model, **kw).eval()   # Mistral3: use its own class
model.requires_grad_(False)
if (a.budget or a.slice) and hasattr(model, "lm_head"): model.lm_head = torch.nn.Identity()
tok =AutoTokenizer.from_pretrained(a.model, revision=a.revision)
cands = [(n, mod) for n, mod in model.named_modules()
         if isinstance(mod, torch.nn.ModuleList) and n.endswith("layers") and "vision" not in n]
layers = cands[0][1]; d = tc.hidden_size

class Stop(Exception): pass
st = {"theta": None, "z": None, "hn": []}
def pre(mod, args, kwargs):                            # add theta to the residual entering layer s
    h = args[0] if args else kwargs["hidden_states"]
    st["hn"].append(h[:, 1:].float().norm(dim=-1).median().item())   # skip BOS: massive activations
    if st["theta"] is not None:
        h = h + st["theta"][:, None, :].to(h.dtype)
        if args: args = (h,) + tuple(args[1:])
        else: kwargs["hidden_states"] = h
    return args, kwargs
def post(mod, args, out):                              # grab layer t-1's output, stop the forward
    st["z"] = out[0] if isinstance(out, tuple) else out
    raise Stop
if not a.slice:
    layers[a.s].register_forward_pre_hook(pre, with_kwargs=True)
    layers[a.t - 1].register_forward_hook(post)

def enc(path):
    ids = tok(open(path).read(), return_tensors="pt", add_special_tokens=bool(a.bos)).input_ids
    return ids.to(dev)                                # tokenize exactly as the server will (BOS!)
seeds = [enc(f) for f in a.seeds]

types = getattr(tc, "layer_types", None)
kind = lambda j: types[j] if types else ""
KW = {}
if a.slice:
    trunk = model.get_submodule(cands[0][0].rpartition(".")[0])
    for _, mod in trunk.named_children():
        if mod is not layers: mod.to(dev)
    for j in range(a.s): layers[j].to(dev)
    def grab(j):
        def hook(mod, args, kwargs):
            st["kw"].setdefault(kind(j), {k: v for k, v in kwargs.items() if k != "hidden_states"})
            if j == a.s:
                st["h"] = args[0] if args else kwargs["hidden_states"]
                raise Stop
        return hook
    hooks = [layers[j].register_forward_pre_hook(grab(j), with_kwargs=True) for j in range(a.s + 1)]
    cache = []
    with torch.no_grad():
        for ids in seeds:
            st["kw"] = {}
            try: model(input_ids=ids, use_cache=False)
            except Stop: pass
            assert all(kind(j) in st["kw"] for j in range(a.s, a.t)), "a layer type after s never seen before it"
            cache.append(st["h"]); KW[id(st["h"])] = st["kw"]
    for hk in hooks: hk.remove()
    for j in range(a.s): layers[j].to("cpu")
    for j in range(a.s, a.t): layers[j].to(dev)
    if dev.type == "cuda": torch.cuda.empty_cache()
    st["hn"] = [h[:, 1:].float().norm(dim=-1).median().item() for h in cache]
    seeds = cache

def run(ids, theta):
    if a.slice:
        h = ids.expand(theta.shape[0], -1, -1) + theta[:, None, :].to(ids.dtype)
        kws = KW[id(ids)]
        for j in range(a.s, a.t):
            out = layers[j](h, **kws[kind(j)])
            h = out[0] if isinstance(out, tuple) else out
        return h[:, -a.last:, :].float()
    st["theta"] = theta
    try: model(input_ids=ids.expand(theta.shape[0], -1), use_cache=False)
    except Stop: pass
    return st["z"][:, -a.last:, :].float()             # [k, last, d]

with torch.no_grad():
    base = [run(ids, torch.zeros(1, d, device=dev)) for ids in seeds]
hnorm = sorted(st["hn"])[len(st["hn"]) // 2]

def step(ids, k):
    return max(1, a.budget // ids.shape[1]) if a.budget else k

def delta(theta):                                      # mean over seeds and positions -> [k, d]
    k = theta.shape[0]
    return sum(torch.cat([(run(i, theta[j:j + step(i, k)]) - b).mean(1) for j in range(0, k, step(i, k))])
               for i, b in zip(seeds, base)) / len(seeds)

def delta_grad(v, u):
    k = v.shape[0]; D, g = torch.zeros_like(u), torch.zeros_like(v)
    for i, b in zip(seeds, base):
        n = step(i, k)
        for j in range(0, k, n):
            vj = v[j:j + n].clone().requires_grad_(True)
            Dj = (run(i, R * vj) - b).mean(1) / len(seeds)
            gj, = torch.autograd.grad((Dj * u[j:j + n]).sum(), vj)
            D[j:j + n] += Dj.detach(); g[j:j + n] += gj
    return D, g

@torch.no_grad()
def calibrate(n=16):                                   # DCT: nonlinear/linear response ratio == lam
    v = F.normalize(torch.randn(n, d, device=dev), dim=1)
    h = 0.02 * hnorm                                   # central difference, cubic error only
    Jv = (delta(h * v) - delta(-h * v)) / (2 * h)
    def ratio(R):
        return ((delta(R * v) - R * Jv).pow(2).sum(1) / (R * Jv).pow(2).sum(1)).mean().sqrt().item()
    lo, hi = 0.01 * hnorm, 3.0 * hnorm
    for _ in range(25):                                # bisection in log space
        mid = (lo * hi) ** 0.5
        lo, hi = (mid, hi) if ratio(mid) < a.lam else (lo, mid)
    return (lo * hi) ** 0.5

R = a.R or calibrate()
print(f"R={R:.3f}  median|h_s|={hnorm:.2f}  R/|h_s|={R / hnorm:.4f}", flush=True)

V = F.normalize(torch.randn(d, a.m, device=dev), dim=0)
U = F.normalize(torch.randn(d, a.m, device=dev), dim=0)
for it in range(a.iters):                              # OGI (DCT algorithm 3)
    V, _ = torch.linalg.qr(V)                          # orthogonalize inputs only
    GU, GV, obj = torch.empty_like(U), torch.empty_like(V), 0.0
    for c in range(0, a.m, a.chunk):
        u = U[:, c:c + a.chunk].T
        D, gv = delta_grad(V[:, c:c + a.chunk].T, u)
        GU[:, c:c + a.chunk], GV[:, c:c + a.chunk], obj = D.T, gv.T, obj + (D * u).sum().item()
    U, V = F.normalize(GU, dim=0), F.normalize(GV, dim=0)
    print(f"iter {it}  causal objective {obj:.2f}", flush=True)

with torch.no_grad():                                  # factor strengths alpha, as in exp_dct.rank()
    D = torch.cat([delta(R * V[:, c:c + a.chunk].T) for c in range(0, a.m, a.chunk)]).T
    K = (U.T @ U) * torch.expm1(V.T @ V)
    alpha = torch.linalg.solve(K, (D * U).sum(0))
torch.save(dict(V=V.cpu(), U=U.cpu(), alpha=alpha.cpu(), R=R, hnorm=hnorm, s=a.s, t=a.t,
                model=a.model, revision=a.revision, seeds=a.seeds), a.out)
json.dump(dict(R=R, hnorm=hnorm, order=alpha.pow(2).argsort(descending=True).tolist()),
          open(a.out + ".json", "w"))
