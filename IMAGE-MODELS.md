# image models — a temporary sheet

Where a picture for the dream stream could come from. **Temporary**: bekh hasn't decided, and is
willing to try them all first; when he has, what survives moves into `BRIEF.md` and this file
goes. Everything below was checked against live pages by opus research agents on 2026-09-19,
not by hand; *unverified* means the agent could not confirm it. Prices are per 1024×1024 image.

bekh's lean: **the old models are fair game and he rather prefers them** — retro bastards over
corporate polish — and a **distillation** of the dream is probably a better prompt than the whole
text anyway: it's a drawing model, not a reading model. So the token limits below are a fact to
know, not a filter.

## Already tried

- **Codex headless (GPT image, on the ChatGPT subscription).** Works bare: `codex exec
  --skip-git-repo-check -s workspace-write - < brief.md`, `image_generation` is a stable enabled
  feature, the file lands in `~/.codex/generated_images/` and codex copies it where told. About
  one to two minutes and 17–36k codex tokens a plate, plus one generation from the ChatGPT image
  allowance (not readable from here). Reads the whole text. Costs limits, not money.
- **OpenRouter** has only OpenAI and Google image models. Costs money. Not where the weird is.

## Free or nearly free

| host | models | cost | entry | catch |
|---|---|---|---|---|
| **Cloudflare Workers AI** | `@cf/stabilityai/stable-diffusion-xl-base-1.0`, `@cf/lykon/dreamshaper-8-lcm`, `@cf/black-forest-labs/flux-1-schnell` | $0 per step on the first two | free daily allowance (10k neurons), no card, plain REST + bearer | flux endpoint **rejects** prompts over 2048 chars |
| **ImageRouter** | `qwen/qwen-image:free`, `black-forest-labs/FLUX-1-schnell:free`, `stabilityai/sdxl-turbo:free`, `Tongyi-MAI/Z-Image-Turbo:free` | $0 | free account for a key | daily free cap *unverified* |
| **AI Horde** | `stable_diffusion` (SD 1.5), `Deliberate`, `Dreamshaper`, `AlbedoBase XL`, 165 in all | $0, crowdsourced | anonymous key `0000000000` | anonymous is refused above 671px; a real queue (hundreds waiting) |
| **Pollinations** | keyless: one low-res model; free key: flux schnell, dreamshaper | ~$0 | none / free registration | keyless pins everything to 768px |

## Cents

| host | models | per image | entry |
|---|---|---|---|
| **NanoGPT** | `chroma` $0.0255, `qwen-image` $0.02, `fast-sdxl` $0.0051, `playground-v25` $0.0085, `flux-schnell` $0.0085; 233 image models incl. uncensored community SDXL checkpoints | see left | **$0.10 minimum deposit**, card or crypto |
| **Venice** | `chroma`, `venice-sd35`, `z-image-turbo` $0.01; `qwen-image` $0.03 | see left | pay as you go, minimum *unverified*; prompt cap 7500 chars; `safe_mode: false` |
| **DeepInfra** | `stabilityai/sdxl-turbo` $0.0002, `CompVis/stable-diffusion-v1-4`, `XpucT/Deliberate`, `FLUX-1-schnell` $0.002 | see left | $5 |
| **Replicate** | `stability-ai/stable-diffusion` (SD 1.5) ~$0.0025, `ai-forever/kandinsky-2.2` $0.021, `flux-schnell` $0.003 | see left | no minimum |
| **Dezgo** | SD 1.5 with 100+ community checkpoints $0.0019 @512, flux $0.0029, sdxl lightning $0.0032 | see left | $10 minimum deposit |
| **SiliconFlow** | flux schnell $0.0014 (single source), flux dev $0.014, qwen-image $0.02 | see left | $1 free credits; image urls expire in an hour |
| **WaveSpeed** | flux schnell $0.003, flux dev $0.012, qwen-image $0.02 | see left | $1 free credits, no card; async api |

## How much of a prompt each model actually reads

The cut is silent: the request succeeds and the tail of the prompt was dropped inside the model.
No host exposes the knob.

| reads | models |
|---|---|
| ~1000 tokens (a whole 400-word block) | Qwen-Image, HunyuanImage-2.1 |
| 512 | Chroma (T5 only, no CLIP branch at all), Flux dev, Wan |
| 256–300 | Flux schnell, SD 3.5, PixArt-Sigma |
| 128 | Kandinsky 3 |
| **77** | SD 1.x, SDXL and every checkpoint built on them, Playground v2.5, Kandinsky 2.2 |

## Dead or not a fit

Hyperbolic (image api decommissioned), Fireworks (image pricing deleted from docs), getimg
(free tier and SD catalog gone), Together (dropped flux schnell), BFL (dropped flux schnell),
Hugging Face providers for SD 1.5 and Kandinsky (none), Prodia / ModelsLab / Freepik
(subscription only), Runware ($20 in the door), Civitai (card purchases dead, crypto only).
The cheap hosts "recommended" on reddit were astroturf; none survived a look at the real site.
