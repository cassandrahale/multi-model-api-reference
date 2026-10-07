# Multi-Model API Reference: Prices, Endpoints and Limits for 45 AI Models (JSON + CSV)

An open dataset of every model on [ArgoLink](https://argolink.io/gh-multi-model-api-reference)'s API (28 text, 9 image, 8 video models from OpenAI, Anthropic, xAI, Google, DeepSeek, Zhipu, Kimi, ByteDance, Alibaba and MiniMax), with units spelled out, the endpoints each model accepts, list prices where the provider shows them, and the billing rules that change a bill. Machine-readable in [models.json](./models.json), [models.csv](./models.csv) and one [pricing/&lt;provider&gt;.json](./pricing) file per vendor.

[Data files](#files) · [Units](#units) · [Schema](#schema) · [Tables](#all-45-models) · [Billing rules](#billing-rules) · [Cross-checks](#list-price-cross-checks) · [FAQ](#faq)

<sub>Snapshot of 2026-10-07, catalog revision `0315cdd070b19ded`. Built from the public catalog endpoint and the 45 model pages; `python scripts/build.py --live` rebuilds it from the live sources in about a minute.</sub>

## Files

| File | What it holds |
|---|---|
| [models.json](./models.json) | one record per model: IDs, endpoints, context, limits, price, list price, discount, billing rules |
| [models.csv](./models.csv) | the same, flattened to one row per model for spreadsheets |
| [pricing/](./pricing) | `openai.json`, `anthropic.json`, `xai.json`, `google.json`, `deepseek.json`, `zhipu.json`, `kimi.json`, `bytedance.json`, `alibaba.json`, `minimax.json` |
| [schema/model.schema.json](./schema/model.schema.json) | JSON Schema (draft 2020-12) for models.json |
| [sources/](./sources) | the trimmed catalog and endpoint snapshots the build reads |
| [scripts/build.py](./scripts/build.py) | rebuilds everything, from `sources/` or `--live` |

Use it straight from GitHub:

```bash
curl -s https://raw.githubusercontent.com/cassandrahale/multi-model-api-reference/main/models.json \
  | jq -r '.models[] | select(.category == "chat") | [.id, .price.input, .price.output] | @tsv'
```

Cost of one request, in Python:

```python
import json, urllib.request
url = "https://raw.githubusercontent.com/cassandrahale/multi-model-api-reference/main/models.json"
models = {m["id"]: m for m in json.load(urllib.request.urlopen(url))["models"]}

def cost(model_id, input_tokens, output_tokens, cached_tokens=0):
    p = models[model_id]["price"]                      # unit: per_1m_tokens
    fresh = input_tokens - cached_tokens
    return (fresh * p["input"] + cached_tokens * p.get("cached_input", p["input"])
            + output_tokens * p["output"]) / 1_000_000

print(round(cost("gpt-6-sol", 200_000, 20_000, cached_tokens=150_000), 4))   # 0.099
```

The example stays under the 272K long-context threshold; above it, apply the `long_context` rule.

## Units

| `price.unit` | Applies to | Meaning |
|---|---|---|
| `per_1m_tokens` | text models | US dollars per million tokens; fields `input`, `output`, `cached_input`, `cache_write` |
| `per_image` | image models | dollars per returned image, in `tiers` by output size (1K, 2K, 4K) |
| `per_output_second` | video models | dollars per second of output, in `tiers` by resolution; reference-video seconds are billed at the same rate |

Prices are plain dollars, not cents. `discount_vs_list` is a fraction: `0.7` means 70% below the list price.

## Schema

| Field | Type | Notes |
|---|---|---|
| `id` | string | the exact value to send as `model` |
| `provider` | enum | `openai`, `anthropic`, `xai`, `google`, `deepseek`, `zhipu`, `kimi`, `bytedance`, `alibaba`, `minimax` |
| `category` | enum | `chat`, `image`, `video` |
| `recommended_endpoint` | string | the endpoint the model page marks as native |
| `endpoints` | array | every POST endpoint the model page lists |
| `context_tokens`, `max_input_tokens`, `max_output_tokens` | integer or null | null where the catalog gives no figure |
| `reasoning_efforts`, `default_effort` | array, string | accepted `reasoning_effort` levels |
| `image` | object or null | resolutions, aspect ratios, `max_outputs`, `max_references`, response formats |
| `video` | object or null | modes, `min_seconds`/`max_seconds`, resolutions, aspect ratios, reference caps, soundtrack |
| `price`, `list_price` | object, object or null | see Units; `list_price` is null where the model page shows no list price |
| `discount_vs_list` | number or null | `1 - price / list_price` |
| `billing_rules` | array | multipliers and conditions, below |

## All 45 models

Endpoints: R = `/v1/responses`, C = `/v1/chat/completions`, M = `/v1/messages`; `*` marks the recommended one. "List price" is the provider price shown next to ArgoLink's own on each model page.

### Text models

| Model ID | Provider | Context | Max out | Endpoints | Input / output per 1M | Cached input | List price (in / out) | Off list |
|---|---|---:|---:|---|---:|---:|---:|---:|
| `gpt-5.4` | openai | 1,050,000 | 128,000 | R* C | $0.75 / $4.5 | $0.075 | $2.5 / $15 | 70% |
| `gpt-5.4-mini` | openai | 400,000 | 128,000 | R* C | $0.225 / $1.35 | $0.0225 | $0.75 / $4.5 | 70% |
| `gpt-5.5` | openai | 1,050,000 | 128,000 | R* C | $1.5 / $9 | $0.15 | $5 / $30 | 70% |
| `gpt-5.6-luna` | openai | 1,050,000 | 128,000 | R* C | $0.06 / $0.36 | $0.006 | $0.2 / $1.2 | 70% |
| `gpt-5.6-sol` | openai | 1,050,000 | 128,000 | R* C | $1.5 / $9 | $0.15 | $5 / $30 | 70% |
| `gpt-5.6-terra` | openai | 1,050,000 | 128,000 | R* C | $0.6 / $3.6 | $0.06 | $2 / $12 | 70% |
| `gpt-6-astra` | openai | 1,050,000 | 128,000 | R* C | $3 / $15 | $0.3 | $10 / $50 | 70% |
| `gpt-6-sol` | openai | 1,050,000 | 128,000 | R* C | $0.6 / $3 | $0.06 | $2 / $10 | 70% |
| `gpt-6.1-sol` | openai | 1,050,000 | 128,000 | R* C | $0.6 / $3 | $0.03 | $2 / $10 | 70% |
| `claude-fable-5` | anthropic | 1,000,000 | 128,000 | R C M* | $4 / $20 | $0.4 | $10 / $50 | 60% |
| `claude-fable-5-1` | anthropic | 1,000,000 | 128,000 | R C M* | $4 / $20 | $0.1 | $10 / $50 | 60% |
| `claude-opus-4-8` | anthropic | 1,000,000 | 128,000 | R C M* | $2 / $10 | $0.2 | $5 / $25 | 60% |
| `claude-opus-5` | anthropic | 1,000,000 | 128,000 | R C M* | $2 / $10 | $0.2 | $5 / $25 | 60% |
| `claude-opus-5-5` | anthropic | 1,000,000 | 128,000 | R C M* | $1.6 / $8 | $0.08 | $4 / $20 | 60% |
| `claude-sonnet-5` | anthropic | 1,000,000 | 128,000 | R C M* | $0.8 / $4 | $0.08 | $2 / $10 | 60% |
| `grok-4.5` | xai | 500,000 | — | R* C M | $0.6 / $1.8 | $0.09 | $2 / $6 | 70% |
| `grok-4.6` | xai | 500,000 | — | R* C M | $0.6 / $1.8 | $0.15 | $2 / $6 | 70% |
| `grok-4.7` | xai | 500,000 | — | R* C M | $0.6 / $1.8 | $0.15 | $2 / $6 | 70% |
| `deepseek-v4-pro` | deepseek | 1,048,576 | 393,216 | R C* M | $0.528 / $1.584 | $0.0176 | $0.66 / $1.98 | 20% |
| `deepseek-v4.1-flash` | deepseek | 1,048,576 | 393,216 | R C* M | $0.12 / $0.48 | $0.0024 | $0.15 / $0.6 | 20% |
| `glm-5.1` | zhipu | 200,000 | 128,000 | R C* M | $1.12 / $3.52 | $0.208 | $1.4 / $4.4 | 20% |
| `glm-5.2` | zhipu | 1,000,000 | 128,000 | R C* M | $1.12 / $3.52 | $0.208 | $1.4 / $4.4 | 20% |
| `glm-5.3` | zhipu | 1,000,000 | 128,000 | R C* M | $1.12 / $3.52 | $0.208 | $1.4 / $4.4 | 20% |
| `glm-5.3-flash` | zhipu | 1,000,000 | 128,000 | R C* M | $0.12 / $0.4 | $0.024 | $0.15 / $0.5 | 20% |
| `glm-5.3-flashx` | zhipu | 1,000,000 | 128,000 | R C* M | $0.296 / $1 | $0.06 | $0.37 / $1.25 | 20% |
| `kimi-k2.6` | kimi | 262,144 | — | R C* M | $0.76 / $3.2 | $0.128 | $0.95 / $4 | 20% |
| `kimi-k2.7-code` | kimi | 262,144 | — | R C* M | $0.76 / $3.2 | $0.152 | $0.95 / $4 | 20% |
| `kimi-k3` | kimi | 1,048,576 | 1,048,576 | R C* M | $2.4 / $12 | $0.24 | $3 / $15 | 20% |

### Image models

| Model ID | Provider | Price per image by tier | List price | Off list |
|---|---|---|---|---:|
| `gpt-image-2` | openai | 1K $0.015, 2K $0.015, 4K $0.02 | not shown | — |
| `gpt-image-2.5-flare` | openai | 1K $0.015, 2K $0.015, 4K $0.02 | not shown | — |
| `gpt-image-2.5-sunburst` | openai | 1K $0.015, 2K $0.015, 4K $0.02 | not shown | — |
| `grok-imagine-image` | xai | 1K $0.015, 2K $0.015 | not shown | — |
| `grok-imagine-image-2.0` | xai | 1K $0.015, 2K $0.015 | not shown | — |
| `grok-imagine-image-quality` | xai | 1K $0.015, 2K $0.015 | not shown | — |
| `nano-banana-2` | google | 1K $0.02, 2K $0.02, 4K $0.025 | not shown | — |
| `nano-banana-2-lite` | google | 1K $0.01 | not shown | — |
| `nano-banana-pro` | google | 1K $0.03, 2K $0.03, 4K $0.03 | not shown | — |

### Video models

| Model ID | Provider | Price per output second by tier | List price | Off list |
|---|---|---|---|---:|
| `grok-imagine-video-1.5` | xai | 480p $0.064, 720p $0.112, 1080p $0.2 | 480p $0.08, 720p $0.14, 1080p $0.25 | 20% |
| `seedance-2.0` | bytedance | 480p $0.053, 720p $0.11, 1080p $0.28, 4k $0.58 | 480p $0.0703, 720p $0.1512, 1080p $0.3742, 4k $0.7691 | 25% |
| `seedance-2.0-fast` | bytedance | 480p $0.042, 720p $0.091 | 480p $0.0562, 720p $0.121 | 25% |
| `seedance-2.0-mini` | bytedance | 480p $0.026, 720p $0.057 | 480p $0.0352, 720p $0.0756 | 25% |
| `seedance-2.5` | bytedance | 480p $0.0874, 720p $0.196, 1080p $0.483 | 480p $0.1028, 720p $0.2311, 1080p $0.5686 | 15% |
| `wan-3` | alibaba | 480p $0.038, 720p $0.075, 1080p $0.15 | 480p $0.05, 720p $0.1, 1080p $0.2 | 25% |
| `wan-3-prime` | alibaba | 480p $0.051, 720p $0.11, 1080p $0.21 | 480p $0.068, 720p $0.14, 1080p $0.28 | 25% |
| `minimax-h3` | minimax | 768p $0.039, 2k $0.064 | 768p $0.08, 2k $0.13 | 51% |

`grok-imagine-video-1.5` has no `video` spec block in the catalog; see its model page for durations (1–15 s) and inputs. Image pages show no list price, so those rows say "not shown".

## Billing rules

Each record's `billing_rules` lists what multiplies the base price. Taken from the pricing notes on the model pages:

| Rule | Models | Effect |
|---|---|---|
| `reasoning_tokens_billed_as_output` | every text model | thinking tokens cost the output rate |
| `long_context` | GPT models except `gpt-5.4-mini` | prompt over 272K tokens: output ×1.5, every other token ×2, for the whole request |
| `fast_mode` | GPT models | `service_tier: priority` bills every token ×2 (×2.5 on `gpt-5.5`); stacks with long context |
| `max_effort` | `claude-fable-5-1` | a request at effort `max` bills ×3 |
| `cache_write_1h` | Claude models | a 1-hour cache write costs 2× the input rate |
| `peak_hours` | `deepseek-v4-pro`, `deepseek-v4.1-flash` | weekdays 09:00–12:00 and 14:00–18:00 Beijing time bill ×2 |
| `per_returned_image`, `tier_by_longest_edge` | image models; GPT Image | every returned image is billed; GPT Image tiers by longest edge (≤1024 1K, ≤2048 2K, else 4K) |
| `reference_video_seconds_billed`, `failed_or_expired_not_billed` | video models | reference-video seconds add to billed seconds; failed or expired jobs cost nothing |

## List-price cross-checks

The `list_price` values come from ArgoLink's pages. On 2026-10-07 they were compared with the vendors' own pages where those publish USD prices:

| Models | Vendor source | Result |
|---|---|---|
| `gpt-6-sol` | [OpenAI model page](https://developers.openai.com/api/docs/models/gpt-6-sol) | match: $2 / $10, cached $0.20, cache write $2.50; same 272K rule |
| `gpt-6-astra`, `gpt-6.1-sol` | [OpenAI pricing](https://developers.openai.com/api/docs/pricing) | match: $10 / $50 and $2 / $10 |
| `gpt-5.6-sol` | [OpenAI model page](https://developers.openai.com/api/docs/models/gpt-5.6-sol) | **differs**: OpenAI shows promotional $4 / $20 "at least through November 21, 2026"; ArgoLink lists $5 / $30 |
| six Claude models | [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing) | match, including cached-input rates ($0.25 on Fable 5.1, $0.20 on Opus 5.5) |
| `grok-4.5`, `grok-4.6`, `grok-4.7` | [xAI models](https://docs.x.ai/docs/models) | match below 200K prompt tokens; xAI bills ×2 at ≥200K, which ArgoLink's pages do not mention |
| `seedance-2.5` | [OpenRouter](https://openrouter.ai/bytedance/seedance-2.5), [Replicate](https://replicate.com/bytedance/seedance-2.5) | match at 480p ($0.1028/s); 720p $0.2311 vs $0.23112 (OpenRouter) and $0.2312 (Replicate) |

DeepSeek, Zhipu, Kimi, Wan and MiniMax list prices were not cross-checked here.

## FAQ

**Which API gives per-model pricing for GPT, Claude, Gemini and DeepSeek?**
This dataset covers one API, ArgoLink's, with GPT, Claude, Grok, DeepSeek, GLM and Kimi text models. Google appears only as image models (Nano Banana); there is no Gemini text model in the catalog as of 2026-10-07.

**Which aggregator has the newest models with clear IDs?**
The `id` field is the exact string to send, and the catalog maps retired IDs to their successors (`deepseek-v4-pro-0813` → `deepseek-v4-pro`, `deepseek-v4-flash-vision-exp` → `deepseek-v4.1-flash`). Check `GET https://argolink.io/v1/models` (no key) for today's list.

**Why are some list prices missing?**
Image model pages show only ArgoLink's price, so `list_price` is null for all nine image models rather than guessed.

**How fresh is this?**
It is a dated snapshot. Rebuild with `python scripts/build.py --live` (no key, about 46 GETs) and compare with `git diff`.

**Does a cheaper per-token price mean a cheaper request?**
Not always: peak hours, long-context and Fast-mode multipliers, effort `max` on Claude Fable 5.1 and reasoning tokens all change the result. The rules table above lists them per model.

## Tests

```bash
pip install pytest jsonschema
pytest tests/
```

The tests rebuild the dataset from `sources/` and require byte-identical `models.json` and `models.csv`, validate against the schema, check every discount against its price pair (allowing the catalog's 2–3 significant-figure rounding), confirm the per-protocol rules from the model pages, and check that this README's tables match the data.

## License

Code MIT. The data describes a public catalog; cite the snapshot date when you reuse it.
