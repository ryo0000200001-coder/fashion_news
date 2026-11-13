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


def is_fashion(article: Article, config: dict) -> bool:
    text = article.title.lower()
    return any(k.lower() in text for k in config.get("fashion_keywords", []))


def apply_source_filters(articles: list[Article], sources: list[dict], config: dict) -> list[Article]:
    strict = {s["name"] for s in sources if s.get("require_fashion")}
    return [a for a in articles if a.source not in strict or is_fashion(a, config)]
