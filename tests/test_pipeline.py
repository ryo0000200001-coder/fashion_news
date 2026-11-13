from datetime import datetime, timedelta, timezone

import yaml

from fashion_news.classify import classify
from fashion_news.dedupe import dedupe, filter_recent, normalize_title, normalize_url
from fashion_news.fetch import parse_feed
from fashion_news.main import group_articles, prune_seen, render_text
from fashion_news.models import Article
from fashion_news.notion import build_blocks

RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>パリコレクション開幕</title><link>https://ex.com/a?utm_source=x</link>
<pubDate>Fri, 13 Nov 2026 20:00:00 +0000</pubDate></item>
<item><title></title><link>https://ex.com/empty</link></item>
</channel></rss>"""

CONFIG = yaml.safe_load(open("config/categories.yaml", encoding="utf-8"))
NOW = datetime(2026, 11, 13, 21, 0, tzinfo=timezone.utc)


def art(title, url="https://ex.com/1", kind="media", pub=None):
    return Article(title, url, "src", kind, pub)


def test_parse_feed_skips_empty_title_and_parses_date():
    items = parse_feed(RSS, "ex", "media")
    assert len(items) == 1
    assert items[0].published == datetime(2026, 11, 13, 20, 0, tzinfo=timezone.utc)


def test_normalize_url_strips_tracking_and_fragment():
    assert normalize_url("https://EX.com/a/?utm_source=x&id=1#top") == "https://ex.com/a?id=1"


def test_normalize_title_drops_source_suffix():
    assert normalize_title("新作スニーカー発売 - 某メディア") == normalize_title("新作スニーカー発売")


def test_dedupe_by_url_title_and_seen():
    items = [
        art("新作スニーカーが発売", "https://ex.com/1"),
        art("新作スニーカーが発売 - 別媒体", "https://other.com/2"),
        art("別の話題", "https://ex.com/3"),
        art("掲載済み", "https://ex.com/4"),
    ]
    out = dedupe(items, {"https://ex.com/4"})
    assert [a.title for a in out] == ["新作スニーカーが発売", "別の話題"]


def test_filter_recent_keeps_undated():
    old = art("old", pub=NOW - timedelta(hours=40))
    new = art("new", pub=NOW - timedelta(hours=1))
    undated = art("undated")
    assert filter_recent([old, new, undated], NOW) == [new, undated]


def test_classify_priority_and_fallback():
    assert classify(art("ミラノでコレクション発表"), CONFIG) == "ハイブランド/コレクション"
    assert classify(art("ナイキ新作スニーカー"), CONFIG) == "ストリート/スニーカー"
    assert classify(art("決算を発表"), CONFIG) == "業界・ビジネス"
    assert classify(art("何でもない記事"), CONFIG) == "その他"
    assert classify(art("ナイキ新作", kind="official"), CONFIG) == "公式発表・ニッチ"


def test_build_blocks_and_render():
    grouped = group_articles([art("ナイキ新作スニーカー"), art("決算", "https://ex.com/2")], CONFIG)
    blocks = build_blocks(grouped)
    assert [b["type"] for b in blocks] == ["heading_2", "bulleted_list_item"] * 2
    assert "ナイキ" in render_text("T", grouped)


def test_prune_seen():
    seen = {"a": "2026-01-01", "b": "2026-11-12"}
    assert prune_seen(seen, "2026-11-13") == {"b": "2026-11-12"}


def test_max_per_category_keeps_newest():
    cfg = dict(CONFIG, max_per_category=2)
    items = [
        art(f"決算{i}", f"https://ex.com/{i}", pub=NOW - timedelta(hours=i)) for i in range(5)
    ]
    out = group_articles(items, cfg)["業界・ビジネス"]
    assert [a.title for a in out] == ["決算0", "決算1"]


def test_require_fashion_filter():
    from fashion_news.classify import apply_source_filters

    srcs = [{"name": "strict", "require_fashion": True}]
    a = Article("ファッションの話", "https://ex.com/a", "strict", "sns")
    b = Article("政治の話", "https://ex.com/b", "strict", "sns")
    c = Article("政治の話", "https://ex.com/c", "other", "media")
    assert apply_source_filters([a, b, c], srcs, CONFIG) == [a, c]


def test_page_title_morning_and_evening():
    from fashion_news.main import page_title

    assert page_title(datetime(2026, 11, 13, 21, 45, tzinfo=timezone.utc)) == "2026-11-14 朝刊"
    assert page_title(datetime(2026, 11, 14, 8, 45, tzinfo=timezone.utc)) == "2026-11-14 夕刊"
