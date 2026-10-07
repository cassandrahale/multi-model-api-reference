"""Print the README model tables from models.json, so the README never drifts from the data.

    python scripts/readme_table.py
"""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SHORT = {"/v1/responses": "R", "/v1/chat/completions": "C", "/v1/messages": "M"}


def money(value) -> str:
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return f"${text}"


def tokens(n) -> str:
    return f"{n:,}" if n else "—"


def off(model) -> str:
    return f"{round(model['discount_vs_list'] * 100)}%" if model["discount_vs_list"] is not None else "—"


def chat_table(models) -> list[str]:
    rows = ["| Model ID | Provider | Context | Max out | Endpoints | Input / output per 1M | Cached input | List price (in / out) | Off list |",
            "|---|---|---:|---:|---|---:|---:|---:|---:|"]
    for m in models:
        if m["category"] != "chat":
            continue
        p, lp = m["price"], m["list_price"]
        eps = " ".join(SHORT[e] + ("*" if e == m["recommended_endpoint"] else "") for e in
                       sorted(m["endpoints"], key=list(SHORT).index))
        rows.append(f"| `{m['id']}` | {m['provider']} | {tokens(m['context_tokens'])} | {tokens(m['max_output_tokens'])} | {eps} "
                    f"| {money(p['input'])} / {money(p['output'])} | {money(p['cached_input']) if 'cached_input' in p else '—'} "
                    f"| {money(lp['input'])} / {money(lp['output'])} | {off(m)} |")
    return rows


def tier_table(models, category: str, unit: str) -> list[str]:
    rows = [f"| Model ID | Provider | Price {unit} by tier | List price | Off list |", "|---|---|---|---|---:|"]
    for m in models:
        if m["category"] != category:
            continue
        tiers = ", ".join(f"{t['tier']} {money(t['usd'])}" for t in m["price"]["tiers"])
        listed = ", ".join(f"{t['tier']} {money(t['usd'])}" for t in m["list_price"]["tiers"]) if m["list_price"] else "not shown"
        rows.append(f"| `{m['id']}` | {m['provider']} | {tiers} | {listed} | {off(m)} |")
    return rows


def render() -> str:
    with open(os.path.join(ROOT, "models.json"), encoding="utf-8") as handle:
        models = json.load(handle)["models"]
    parts = ["### Text models", "", *chat_table(models), "",
             "### Image models", "", *tier_table(models, "image", "per image"), "",
             "### Video models", "", *tier_table(models, "video", "per output second")]
    return "\n".join(parts)


if __name__ == "__main__":
    print(render())
