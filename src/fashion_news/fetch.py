from __future__ import annotations

import calendar
import logging
from datetime import datetime, timezone

import feedparser
import requests

from .models import Article

log = logging.getLogger(__name__)
USER_AGENT = "fashion-news-bot/1.0 (personal RSS reader)"


def parse_feed(content: bytes | str, source: str, kind: str) -> list[Article]:
    parsed = feedparser.parse(content)
    articles: list[Article] = []
    for e in parsed.entries:
        title = (e.get("title") or "").strip()
        link = (e.get("link") or "").strip()
        if not title or not link:
            continue
        ts = e.get("published_parsed") or e.get("updated_parsed")
        published = (
            datetime.fromtimestamp(calendar.timegm(ts), tz=timezone.utc) if ts else None
        )
        articles.append(Article(title, link, source, kind, published))
    return articles


def fetch_source(src: dict, timeout: int = 20) -> list[Article]:
    resp = requests.get(src["url"], headers={"User-Agent": USER_AGENT}, timeout=timeout)
    resp.raise_for_status()
    return parse_feed(resp.content, src["name"], src.get("kind", "media"))


def fetch_all(sources: list[dict]) -> list[Article]:
    """1つの情報源が失敗しても他は続ける。"""
    result: list[Article] = []
    for src in sources:
        try:
            items = fetch_source(src)
            log.info("%s: %d件", src["name"], len(items))
            result.extend(items)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s の取得に失敗: %s", src["name"], exc)
    return result
