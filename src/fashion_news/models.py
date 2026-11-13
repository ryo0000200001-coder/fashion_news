from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Article:
    title: str
    url: str
    source: str
    kind: str  # media / official / sns
    published: datetime | None = None  # UTC。不明なら None
    category: str = ""
