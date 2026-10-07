"""Build models.json, models.csv and pricing/<provider>.json from the ArgoLink catalog.

Standard library only (Python 3.9+).

    python scripts/build.py              # rebuild from the snapshots in sources/
    python scripts/build.py --live       # refresh sources/ from the live catalog and model pages, then rebuild

The live mode reads two public, key-free sources:
  * https://argolink.io/api/catalog/v1/models?page_size=100   (prices, limits, categories)
  * https://argolink.io/en/models/<id>                         (the endpoints each model accepts)
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CATALOG_URL = "https://argolink.io/api/catalog/v1/models?page_size=100"
PAGE_URL = "https://argolink.io/en/models/{id}"
# The API's CDN rejects urllib's default "Python-urllib/x.y" agent with 403 (error 1010).
HEADERS = {"User-Agent": "multi-model-api-reference/1.0 (+https://github.com/cassandrahale/multi-model-api-reference)"}
CATEGORY_ORDER = {"chat": 0, "image": 1, "video": 2}
PROVIDER_ORDER = ["openai", "anthropic", "xai", "google", "deepseek", "zhipu", "kimi", "bytedance", "alibaba", "minimax"]
PEAK_WINDOW = "Mon-Fri 09:00-12:00 and 14:00-18:00 Asia/Shanghai"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def refresh_sources(day: str) -> None:
    """Download the catalog and every model page; write trimmed snapshots to sources/."""
    catalog = json.loads(fetch(CATALOG_URL))
    items, endpoints = [], {}
    for model in catalog["items"]:
        item = {k: model[k] for k in ("id", "display_name", "provider_id", "category", "endpoint")}
        for key in ("text", "image", "video"):
            if key in model:
                item[key] = model[key]
        pricing = model["pricing"]
        item["pricing"] = {"effective": pricing["effective"]}
        # Model pages show an "Official price" column only for percentage-of-official pricing.
        if re.fullmatch(r"official-\d+", str(pricing.get("policy_id", ""))):
            item["pricing"]["official"] = pricing["official"]
            item["pricing"]["multiplier"] = pricing["multiplier"]
        note = (model.get("note") or {}).get("en", "")
        if "Weekdays" in note:
            item["note_en"] = note
        items.append(item)
        page = fetch(PAGE_URL.format(id=model["id"])).decode("utf-8", "replace")
        endpoints[model["id"]] = page_endpoints(page)
    with open(os.path.join(ROOT, "sources", f"catalog-{day}.json"), "w", encoding="utf-8") as handle:
        json.dump({"source": CATALOG_URL, "fetched": day, "revision": catalog.get("revision"),
                   "comment": "Trimmed: descriptive text dropped; official prices kept only where the model page shows them.",
                   "items": items}, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    with open(os.path.join(ROOT, "sources", f"endpoints-{day}.json"), "w", encoding="utf-8") as handle:
        json.dump({"source": "https://argolink.io/en/models/{id} (Endpoints section)", "fetched": day,
                   "endpoints": dict(sorted(endpoints.items()))}, handle, indent=1)
        handle.write("\n")


def page_endpoints(page_html: str) -> list[str]:
    """POST paths listed in a model page's Endpoints section (labels and paths are adjacent once tags go)."""
    text = re.sub(r"<(script|style)[\s\S]*?</\1>", "", page_html)
    text = re.sub(r"<[^>]+>", " ", text)
    return sorted(set(re.findall(r"POST[A-Za-z ]*?\s*(/v1/[a-z_]+(?:/[a-z_]+)?)", text)))


def latest(prefix: str) -> str:
    names = sorted(n for n in os.listdir(os.path.join(ROOT, "sources")) if n.startswith(prefix))
    if not names:
        sys.exit(f"no sources/{prefix}*.json; run with --live")
    return os.path.join(ROOT, "sources", names[-1])


def token_price(p: dict | None) -> dict | None:
    if not p:
        return None
    out = {"currency": "USD", "unit": "per_1m_tokens", "input": p["input_per_million"], "output": p["output_per_million"]}
    if p.get("cached_input_per_million") is not None:
        out["cached_input"] = p["cached_input_per_million"]
    if p.get("cache_write_per_million"):
        out["cache_write"] = p["cache_write_per_million"]
    return out


def tier_price(p: dict | None, unit: str) -> dict | None:
    if not p:
        return None
    return {"currency": "USD", "unit": unit, "tiers": [{"tier": t["label"], "usd": t["price"]} for t in p["tiers"]]}


def rules_for(item: dict) -> list[dict]:
    rules: list[dict] = []
    text = item.get("text") or {}
    if item["category"] == "chat":
        rules.append({"rule": "reasoning_tokens_billed_as_output"})
        if text.get("long_context"):
            lc = text["long_context"]
            rules.append({"rule": "long_context", "prompt_tokens_over": lc["threshold_tokens"],
                          "input_multiplier": lc["input_multiplier"], "output_multiplier": lc["output_multiplier"]})
        if text.get("fast_multiplier"):
            rules.append({"rule": "fast_mode", "request_field": "service_tier: priority", "multiplier": text["fast_multiplier"]})
        if text.get("max_effort_multiplier"):
            rules.append({"rule": "max_effort", "multiplier": text["max_effort_multiplier"]})
        if item["provider_id"] == "anthropic":
            rules.append({"rule": "cache_write_1h", "multiplier_of_input": 2})
        if "Weekdays" in item.get("note_en", ""):
            rules.append({"rule": "peak_hours", "window": PEAK_WINDOW, "multiplier": 2})
    elif item["category"] == "image":
        rules.append({"rule": "per_returned_image"})
        if (item.get("image") or {}).get("frame") == "size":
            rules.append({"rule": "tier_by_longest_edge", "1K": "<=1024", "2K": "1025-2048", "4K": ">2048"})
    else:
        rules.append({"rule": "per_output_second"})
        if item.get("video"):
            rules.append({"rule": "reference_video_seconds_billed"})
        rules.append({"rule": "failed_or_expired_not_billed"})
    return rules


def image_spec(image: dict | None) -> dict | None:
    if not image:
        return None
    ratios = image.get("aspect_ratios") or [s["aspect_ratio"] for s in image.get("sizes", [])]
    spec = {"resolutions": image.get("resolutions"), "aspect_ratios": ratios,
            "size_field": "size" if image.get("frame") == "size" else "aspect_ratio + resolution",
            "max_outputs": image.get("max_outputs"), "max_references": image.get("max_references"),
            "response_formats": image.get("response_formats")}
    return {k: v for k, v in spec.items() if v is not None}


def video_spec(item: dict) -> dict | None:
    video = item.get("video")
    if not video:
        return None
    modes = video.get("modes", [])
    reference = next((m for m in modes if m["mode"] == "multimodal_reference"), {})
    spec = {
        "modes": [m["mode"] for m in modes],
        "min_seconds": min(m["min_duration"] for m in modes if "min_duration" in m),
        "max_seconds": max(m["max_duration"] for m in modes if "max_duration" in m),
        "default_seconds": video.get("default_duration"),
        "resolutions": [t["label"] for t in item["pricing"]["effective"]["tiers"]],
        "default_resolution": video.get("default_resolution"),
        "aspect_ratios": sorted({r for m in modes for r in m.get("aspect_ratios", [])}, key=_ratio_key),
        "max_reference_images": reference.get("max_images"),
        "max_reference_videos": reference.get("max_videos"),
        "max_reference_audios": reference.get("max_audios"),
        "max_reference_assets": reference.get("max_assets"),
        "soundtrack": {"switch": "on unless generate_audio is false", "always": "always generated"}.get(video.get("generate_audio")),
        "max_prompt_chars": video.get("max_prompt_chars"),
        "seed": video.get("seed"),
    }
    return {k: v for k, v in spec.items() if v is not None}


def _ratio_key(ratio: str):
    if ratio == "adaptive":
        return (1, 0)
    w, h = ratio.split(":")
    return (0, -float(w) / float(h))


def normalise(item: dict, endpoints: dict) -> dict:
    text = item.get("text") or {}
    pricing = item["pricing"]
    unit = {"chat": None, "image": "per_image", "video": "per_output_second"}[item["category"]]
    price = token_price(pricing["effective"]) if unit is None else tier_price(pricing["effective"], unit)
    official = pricing.get("official")
    list_price = (token_price(official) if unit is None else tier_price(official, unit)) if official else None
    record = {
        "id": item["id"],
        "name": item["display_name"],
        "provider": item["provider_id"],
        "category": item["category"],
        "recommended_endpoint": item["endpoint"],
        "endpoints": endpoints.get(item["id"], [item["endpoint"]]),
        "model_page": PAGE_URL.format(id=item["id"]),
        "context_tokens": text.get("context_tokens"),
        "max_input_tokens": text.get("max_input_tokens"),
        "max_output_tokens": text.get("max_output_tokens"),
        "reads_images": text.get("images") if item["category"] == "chat" else None,
        "reasoning_efforts": text.get("efforts"),
        "default_effort": text.get("default_effort"),
        "image": image_spec(item.get("image")),
        "video": video_spec(item),
        "price": price,
        "list_price": list_price,
        "discount_vs_list": round(1 - pricing["multiplier"], 4) if official else None,
        "billing_rules": rules_for(item),
    }
    return record


def build(catalog_path: str, endpoints_path: str) -> dict:
    with open(catalog_path, encoding="utf-8") as handle:
        catalog = json.load(handle)
    with open(endpoints_path, encoding="utf-8") as handle:
        endpoints = json.load(handle)["endpoints"]
    models = [normalise(item, endpoints) for item in catalog["items"]]
    models.sort(key=lambda m: (CATEGORY_ORDER[m["category"]], PROVIDER_ORDER.index(m["provider"]), m["id"]))
    return {"schema": "schema/model.schema.json", "source": catalog["source"], "fetched": catalog["fetched"],
            "catalog_revision": catalog["revision"], "count": len(models), "models": models}


def csv_rows(models: list[dict]):
    header = ["id", "name", "provider", "category", "recommended_endpoint", "endpoints", "context_tokens",
              "max_output_tokens", "price_unit", "price_input", "price_output", "price_cached_input",
              "price_tiers", "list_input", "list_output", "list_tiers", "discount_vs_list", "model_page"]
    yield header
    for m in models:
        price, listed = m["price"], m["list_price"] or {}
        tiers = lambda p: ";".join(f"{t['tier']}={t['usd']}" for t in p.get("tiers", []))  # noqa: E731
        yield [m["id"], m["name"], m["provider"], m["category"], m["recommended_endpoint"], " ".join(m["endpoints"]),
               m["context_tokens"] or "", m["max_output_tokens"] or "", price["unit"], price.get("input", ""),
               price.get("output", ""), price.get("cached_input", ""), tiers(price), listed.get("input", ""),
               listed.get("output", ""), tiers(listed), m["discount_vs_list"] if m["discount_vs_list"] is not None else "",
               m["model_page"]]


def write_outputs(data: dict) -> None:
    with open(os.path.join(ROOT, "models.json"), "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    with open(os.path.join(ROOT, "models.csv"), "w", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerows(csv_rows(data["models"]))
    os.makedirs(os.path.join(ROOT, "pricing"), exist_ok=True)
    for provider in PROVIDER_ORDER:
        rows = {m["id"]: {k: m[k] for k in ("category", "price", "list_price", "discount_vs_list", "billing_rules")}
                for m in data["models"] if m["provider"] == provider}
        if rows:
            with open(os.path.join(ROOT, "pricing", f"{provider}.json"), "w", encoding="utf-8") as handle:
                json.dump({"provider": provider, "fetched": data["fetched"], "models": rows}, handle, indent=1)
                handle.write("\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--live", action="store_true", help="refresh sources/ from the live catalog first")
    args = parser.parse_args(argv)
    if args.live:
        refresh_sources(dt.date.today().isoformat())
    data = build(latest("catalog-"), latest("endpoints-"))
    write_outputs(data)
    print(f"{data['count']} models, catalog revision {data['catalog_revision']}, fetched {data['fetched']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
