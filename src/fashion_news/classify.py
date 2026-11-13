from __future__ import annotations

from .models import Article


def classify(article: Article, config: dict) -> str:
    if article.kind in config.get("niche_kinds", []):
        return config["niche_category"]
    text = article.title.lower()
    for cat in config["categories"]:
        if any(k.lower() in text for k in cat["keywords"]):
            return cat["name"]
    return config["fallback_category"]


def category_order(config: dict) -> list[str]:
    return (
        [c["name"] for c in config["categories"]]
        + [config["niche_category"], config["fallback_category"]]
    )
