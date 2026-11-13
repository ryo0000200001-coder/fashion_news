from __future__ import annotations

import logging
import time

import requests

from .models import Article

log = logging.getLogger(__name__)
API = "https://api.notion.com/v1"
VERSION = "2022-06-28"
MAX_CHILDREN = 100  # 1回のリクエストで送れるブロック数の上限


def build_blocks(grouped: dict[str, list[Article]]) -> list[dict]:
    blocks: list[dict] = []
    for category, items in grouped.items():
        if not items:
            continue
        blocks.append(
            {
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": category}}]},
            }
        )
        for a in items:
            blocks.append(
                {
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": a.title[:1900], "link": {"url": a.url}},
                            },
                            {"type": "text", "text": {"content": f" — {a.source}"}},
                        ]
                    },
                }
            )
    return blocks


class NotionClient:
    def __init__(self, token: str):
        self.s = requests.Session()
        self.s.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Notion-Version": VERSION,
                "Content-Type": "application/json",
            }
        )

    def _request(self, method: str, path: str, **kw) -> dict:
        for attempt in range(4):
            r = self.s.request(method, f"{API}{path}", timeout=30, **kw)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(float(r.headers.get("Retry-After", 2 ** attempt)))
                continue
            if not r.ok:
                raise RuntimeError(f"Notion API {r.status_code}: {r.text[:300]}")
            return r.json()
        raise RuntimeError(f"Notion API が繰り返し失敗: {method} {path}")

    def find_child_page(self, parent_id: str, title: str) -> str | None:
        cursor = None
        while True:
            params = {"page_size": 100, **({"start_cursor": cursor} if cursor else {})}
            data = self._request("GET", f"/blocks/{parent_id}/children", params=params)
            for b in data["results"]:
                if b["type"] == "child_page" and b["child_page"]["title"] == title:
                    return b["id"]
            if not data.get("has_more"):
                return None
            cursor = data["next_cursor"]

    def create_daily_page(self, parent_id: str, title: str, blocks: list[dict]) -> str:
        page = self._request(
            "POST",
            "/pages",
            json={
                "parent": {"page_id": parent_id},
                "properties": {"title": {"title": [{"text": {"content": title}}]}},
                "children": blocks[:MAX_CHILDREN],
            },
        )
        for i in range(MAX_CHILDREN, len(blocks), MAX_CHILDREN):
            self._request(
                "PATCH",
                f"/blocks/{page['id']}/children",
                json={"children": blocks[i : i + MAX_CHILDREN]},
            )
        return page["url"]
