"""Offline checks: the committed data is reproducible and internally consistent.

    pip install pytest            # optional: jsonschema
    pytest tests/
"""
import csv
import json
import os
import sys
from decimal import Decimal

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build  # noqa: E402


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as handle:
        return json.load(handle)


DATA = load("models.json")
MODELS = {m["id"]: m for m in DATA["models"]}


def test_committed_files_match_a_fresh_build():
    fresh = build.build(build.latest("catalog-"), build.latest("endpoints-"))
    assert fresh == DATA
    with open(os.path.join(ROOT, "models.csv"), encoding="utf-8") as handle:
        assert list(csv.reader(handle)) == [[str(c) for c in row] for row in build.csv_rows(fresh["models"])]


def test_schema_when_jsonschema_is_installed():
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(DATA, load("schema/model.schema.json"))


def test_ids_are_unique_and_count_matches():
    assert len(MODELS) == DATA["count"] == len(DATA["models"]) == 45


def test_discount_matches_price_over_list_price():
    for model in DATA["models"]:
        listed, price = model["list_price"], model["price"]
        if listed is None:
            assert model["discount_vs_list"] is None
            continue
        ratio = Decimal(str(1 - model["discount_vs_list"]))
        if price["unit"] == "per_1m_tokens":
            pairs = [(price["input"], listed["input"]), (price["output"], listed["output"])]
        else:
            pairs = list(zip([t["usd"] for t in price["tiers"]], [t["usd"] for t in listed["tiers"]]))
        for ours, theirs in pairs:
            # The catalog rounds to 2-3 significant figures (Seedance 2.0 family: 0.1512 x 0.75 -> 0.11),
            # so allow the rounding error of 2 significant figures: under 5% of the price.
            expected = Decimal(str(theirs)) * ratio
            assert abs(Decimal(str(ours)) - expected) <= expected * Decimal("0.05"), model["id"]


def test_units_follow_the_category():
    unit = {"chat": "per_1m_tokens", "image": "per_image", "video": "per_output_second"}
    for model in DATA["models"]:
        assert model["price"]["unit"] == unit[model["category"]]


def test_protocol_rules_seen_on_the_model_pages():
    for model in DATA["models"]:
        if model["category"] != "chat":
            continue
        if model["provider"] == "openai":
            assert "/v1/messages" not in model["endpoints"]  # not open for OpenAI models
        else:
            assert {"/v1/chat/completions", "/v1/responses", "/v1/messages"} <= set(model["endpoints"])


def test_a_few_spot_values():
    assert MODELS["gpt-6-sol"]["price"]["input"] == 0.6 and MODELS["gpt-6-sol"]["list_price"]["input"] == 2
    assert [t["usd"] for t in MODELS["seedance-2.5"]["price"]["tiers"]] == [0.0874, 0.196, 0.483]
    assert MODELS["nano-banana-pro"]["list_price"] is None
    peak = [r for r in MODELS["deepseek-v4-pro"]["billing_rules"] if r["rule"] == "peak_hours"]
    assert peak and peak[0]["multiplier"] == 2


def test_provider_files_cover_every_model():
    seen = set()
    for provider in build.PROVIDER_ORDER:
        path = os.path.join(ROOT, "pricing", f"{provider}.json")
        if os.path.exists(path):
            seen |= set(load(f"pricing/{provider}.json")["models"])
    assert seen == set(MODELS)


def test_readme_tables_match_the_data():
    import readme_table
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as handle:
        assert readme_table.render() in handle.read()
