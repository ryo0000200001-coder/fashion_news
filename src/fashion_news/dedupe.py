from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import Article

_TRACKING = re.compile(r"^(utm_|fbclid|gclid|ref$|ref_)")


def normalize_url(url: str) -> str:
    p = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(p.query) if not _TRACKING.match(k)]
    path = p.path.rstrip("/") or "/"
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, urlencode(query), ""))


def normalize_title(title: str) -> str:
    t = unicodedata.normalize("NFKC", title).lower()
    t = re.sub(r"\s+[-–|｜]\s+[^-–|｜]+$", "", t)  # 末尾の「 - 媒体名」を除く
    return re.sub(r"[\W_]+", "", t)


def filter_recent(articles: list[Article], now: datetime, hours: int = 36) -> list[Article]:
    """日付のない記事は残す（重複除去に任せる）。"""
    cutoff = now - timedelta(hours=hours)
    return [a for a in articles if a.published is None or a.published >= cutoff]


def dedupe(
    articles: list[Article], seen_urls: set[str], similarity: float = 0.9
) -> list[Article]:
    kept: list[Article] = []
    kept_titles: list[str] = []
    for a in articles:
        url = normalize_url(a.url)
        if url in seen_urls:
            continue
        nt = normalize_title(a.title)
        if not nt:
            continue
        if any(nt == t or SequenceMatcher(None, nt, t).ratio() >= similarity for t in kept_titles):
            continue
        kept.append(a)
        kept_titles.append(nt)
        seen_urls = seen_urls | {url}
    return kept
