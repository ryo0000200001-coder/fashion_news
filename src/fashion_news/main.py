from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from .classify import apply_source_filters, category_order, classify
from .dedupe import dedupe, filter_recent, normalize_url
from .fetch import fetch_all
from .models import Article
from .notion import NotionClient, build_blocks

log = logging.getLogger("fashion_news")
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[2]
SEEN_KEEP_DAYS = 30


def load_seen(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8") or "{}")


def prune_seen(seen: dict[str, str], today: str) -> dict[str, str]:
    limit = (datetime.fromisoformat(today) - timedelta(days=SEEN_KEEP_DAYS)).date().isoformat()
    return {u: d for u, d in seen.items() if d >= limit}


def group_articles(articles: list[Article], config: dict) -> dict[str, list[Article]]:
    grouped = {name: [] for name in category_order(config)}
    for a in articles:
        a.category = classify(a, config)
        grouped[a.category].append(a)
    limit = config.get("max_per_category")
    oldest = datetime.min.replace(tzinfo=timezone.utc)
    for name, items in grouped.items():
        items.sort(key=lambda a: a.published or oldest, reverse=True)  # 新しい順
        if limit:
            grouped[name] = items[:limit]
    return grouped


def render_text(title: str, grouped: dict[str, list[Article]]) -> str:
    lines = [f"# {title}"]
    for cat, items in grouped.items():
        if items:
            lines.append(f"\n## {cat}")
            lines += [f"- {a.title} ({a.source}) {a.url}" for a in items]
    return "\n".join(lines)


def page_title(now: datetime) -> str:
    """JST の正午より前なら朝刊、それ以降は夕刊。"""
    jst = now.astimezone(JST)
    return f"{jst.date().isoformat()} {'朝刊' if jst.hour < 12 else '夕刊'}"


def run(dry_run: bool, force: bool, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(JST).date().isoformat()
    title = page_title(now)

    sources = yaml.safe_load((ROOT / "config/sources.yaml").read_text(encoding="utf-8"))["sources"]
    config = yaml.safe_load((ROOT / "config/categories.yaml").read_text(encoding="utf-8"))
    seen_path = ROOT / "data/seen_urls.json"
    seen = load_seen(seen_path)

    client = parent_id = None
    if not dry_run:
        token = (os.environ.get("NOTION_TOKEN") or "").strip()
        parent_id = (os.environ.get("NOTION_PARENT_PAGE_ID") or "").strip()
        if not token or not parent_id:
            log.error("NOTION_TOKEN と NOTION_PARENT_PAGE_ID が必要です")
            return 1
        if not token.isascii() or not token.isprintable() or " " in token:
            log.error(
                "NOTION_TOKEN に半角英数字以外の文字（日本語・記号・空白・改行など）が含まれています。"
                "Notion のインテグレーション画面のコピーアイコンでトークンをコピーし直して登録してください"
            )
            return 1
        client = NotionClient(token)
        if not force and client.find_child_page(parent_id, title):
            log.info("%s は作成済みのため終了します（--force で再作成）", title)
            return 0

    fetched = fetch_all(sources)
    if not fetched:
        log.error("全ての情報源の取得に失敗しました")
        return 1
    candidates = apply_source_filters(filter_recent(fetched, now), sources, config)
    grouped = group_articles(dedupe(candidates, set(seen)), config)
    articles = [a for items in grouped.values() for a in items]  # 上限で落とした記事は履歴に入れない
    log.info("取得 %d件 → 掲載 %d件", len(fetched), len(articles))

    if dry_run:
        print(render_text(title, grouped))
        return 0

    blocks = build_blocks(grouped) or [
        {
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "本日の新着記事はありませんでした。"}}]},
        }
    ]
    url = client.create_daily_page(parent_id, title, blocks)
    log.info("Notion に作成しました: %s", url)

    seen.update({normalize_url(a.url): today for a in articles})
    seen_path.write_text(
        json.dumps(prune_seen(seen, today), ensure_ascii=False, indent=0, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="毎朝のファッションニュースを Notion に作成する")
    ap.add_argument("--dry-run", action="store_true", help="Notion に書かず標準出力に表示")
    ap.add_argument("--force", action="store_true", help="同じ日のページがあっても作成する")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(run(args.dry_run, args.force))


if __name__ == "__main__":
    main()
