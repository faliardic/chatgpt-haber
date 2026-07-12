from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import sys
from typing import Any

from chatgpt_haber.sources import extract_article_detail, is_clickbait_article, normalize_for_match
from services.news_quality_filters import is_generic_earthquake_clickbait, sanitize_items_or_fail


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else PROJECT_ROOT


def appdata_news_cache_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Gazette" / "latest_issue.json"
    return Path.home() / ".gazette" / "latest_issue.json"


def feedback_path() -> Path:
    return appdata_news_cache_path().parent / "random_feedback.json"


def saved_news_path() -> Path:
    return appdata_news_cache_path().parent / "saved_news.json"


def desktop_dir() -> Path:
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"


def desktop_gazette_dir(now: datetime | None = None) -> Path:
    stamp = (now or datetime.now()).strftime("%Y-%m-%d")
    return desktop_dir() / "Gazette" / f"gazete-kopya-{stamp}"


DEFAULT_CACHE_CANDIDATES = (
    appdata_news_cache_path(),
    RUNTIME_ROOT / "issue.json",
    RUNTIME_ROOT / "dist" / "issue.json",
    PROJECT_ROOT / "dist" / "issue.json",
    PROJECT_ROOT / "output" / "news.json",
    PROJECT_ROOT / "output" / "issue.json",
    PROJECT_ROOT / "data" / "latest_news.json",
    PROJECT_ROOT / "data" / "news_cache.json",
    PROJECT_ROOT / "cache" / "latest.json",
)

LATEST_GAZETTE_CANDIDATES = (
    PROJECT_ROOT / "dist" / "gazete.pdf",
    PROJECT_ROOT / "dist" / "gazete.html",
    PROJECT_ROOT / "dist" / "issue.json",
    PROJECT_ROOT / "output" / "CHATGPT_HABER.pdf",
)


@dataclass(frozen=True)
class NewsItem:
    id: str
    title: str
    url: str
    source: str = ""
    published_at: str = ""
    summary: str = ""
    body: tuple[str, ...] = ()
    category: str = ""
    importance: int | None = None
    score: float | None = None
    earthquake_classification: str = ""

    @property
    def full_text(self) -> str:
        paragraphs = [paragraph.strip() for paragraph in self.body if paragraph.strip()]
        if paragraphs:
            return "\n\n".join(paragraphs)
        return self.summary.strip()


class RandomNewsService:
    def __init__(
        self,
        cache_paths: list[Path] | None = None,
        seen_path: Path | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.cache_paths = cache_paths or list(DEFAULT_CACHE_CANDIDATES)
        self.seen_path = seen_path or default_seen_path()
        self.rng = rng or random.Random()

    def load_current_news(self) -> list[NewsItem]:
        all_items: list[NewsItem] = []
        for path in self.cache_paths:
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            items = [item for item in (normalize_news(raw) for raw in flatten_news(data)) if item]
            if items:
                all_items.extend(items)
        return dedupe_items(all_items)

    def filter_random_pool(self, news: list[NewsItem]) -> list[NewsItem]:
        return dedupe_items([item for item in sanitize_items_or_fail(news, "random_pool") if random_pool_allowed(item)])

    def pick_random_news(self) -> NewsItem | None:
        pool = self.filter_random_pool(self.load_current_news())
        if not pool:
            return None
        seen = self._load_seen()
        unseen = [item for item in pool if item.id not in seen]
        if not unseen:
            seen = set()
            unseen = pool
        item = self.with_full_text(self.rng.choice(unseen))
        seen.add(item.id)
        self._save_seen(seen)
        return item

    def with_full_text(self, item: NewsItem) -> NewsItem:
        if item.body:
            return item
        paragraphs = extract_article_detail(item.url, item.title, max_paragraphs=None)
        cleaned = tuple(paragraph.strip() for paragraph in paragraphs if paragraph.strip())
        return replace(item, body=cleaned) if cleaned else item

    def mark_seen(self, news_id: str) -> None:
        seen = self._load_seen()
        seen.add(news_id)
        self._save_seen(seen)

    def save_feedback(self, item: NewsItem, action: str) -> Path:
        path = feedback_path()
        data = read_json_list(path)
        data.append({"id": item.id, "title": item.title, "url": item.url, "source": item.source, "action": action, "saved_at": datetime.now(timezone.utc).isoformat()})
        write_json_list(path, data)
        return path

    def save_news(self, item: NewsItem) -> Path:
        path = saved_news_path()
        data = read_json_list(path)
        if not any(entry.get("id") == item.id for entry in data if isinstance(entry, dict)):
            data.append({
                "id": item.id,
                "title": item.title,
                "url": item.url,
                "source": item.source,
                "summary": item.summary,
                "body": list(item.body),
                "full_text": item.full_text,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            })
        write_json_list(path, data)
        return path

    def copy_latest_gazette_to_desktop(self) -> Path:
        return copy_latest_gazette_to_desktop()

    def reset_seen_if_needed(self) -> None:
        pool = self.filter_random_pool(self.load_current_news())
        if not pool:
            return
        seen = self._load_seen()
        if all(item.id in seen for item in pool):
            self._save_seen(set())

    def _load_seen(self) -> set[str]:
        try:
            data = json.loads(self.seen_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return set()
        if isinstance(data, list):
            return {str(item) for item in data}
        if isinstance(data, dict) and isinstance(data.get("seen"), list):
            return {str(item) for item in data["seen"]}
        return set()

    def _save_seen(self, seen: set[str]) -> None:
        self.seen_path.parent.mkdir(parents=True, exist_ok=True)
        self.seen_path.write_text(json.dumps({"seen": sorted(seen)}, ensure_ascii=False, indent=2), encoding="utf-8")


def default_seen_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Gazette" / "random_news_seen.json"
    return Path.home() / ".gazette" / "random_news_seen.json"


def read_json_list(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def write_json_list(path: Path, data: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def flatten_news(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    if isinstance(data.get("news"), list):
        return [item for item in data["news"] if isinstance(item, dict)]
    if isinstance(data.get("articles"), list):
        return [item for item in data["articles"] if isinstance(item, dict)]
    pages = data.get("pages")
    if isinstance(pages, list):
        items: list[dict[str, Any]] = []
        for page in pages:
            if not isinstance(page, dict):
                continue
            for key in ("articles", "briefs"):
                value = page.get(key)
                if isinstance(value, list):
                    items.extend(item for item in value if isinstance(item, dict))
        return items
    return []


def normalize_news(raw: dict[str, Any]) -> NewsItem | None:
    if raw.get("accepted") is False or raw.get("rejected") is True or first_text(raw, "reject_reason"):
        return None
    title = first_text(raw, "title", "headline", "name")
    url = first_text(raw, "url", "link", "source_url")
    source = first_text(raw, "source", "publisher", "source_name")
    source_bundle = raw.get("source_bundle") or raw.get("sources")
    if isinstance(source_bundle, list) and source_bundle and isinstance(source_bundle[0], dict):
        url = url or first_text(source_bundle[0], "url", "link")
        source = source or first_text(source_bundle[0], "name", "source", "publisher")
    if not title or not url:
        return None

    published_at = first_text(raw, "published_at", "created_at", "date", "updated_at")
    summary = first_text(raw, "summary", "description", "dek", "subtitle")
    body = body_paragraphs(raw)
    category = first_text(raw, "category", "section", "kicker")
    item_id = first_text(raw, "id") or stable_id(url, source, title, published_at)
    return NewsItem(
        id=item_id,
        title=title,
        url=url,
        source=source,
        published_at=published_at,
        summary=summary,
        body=tuple(body),
        category=category,
        importance=parse_int(raw.get("importance")),
        score=parse_float(raw.get("importance_score", raw.get("score"))),
        earthquake_classification=first_text(raw, "earthquake_classification"),
    )


def body_paragraphs(raw: dict[str, Any]) -> list[str]:
    for key in ("body", "content", "full_text", "text", "article_text"):
        value = raw.get(key)
        if isinstance(value, list):
            paragraphs = [str(item).strip() for item in value if str(item).strip()]
            if paragraphs:
                return paragraphs
        if isinstance(value, str) and value.strip():
            return [part.strip() for part in value.replace("\r\n", "\n").split("\n\n") if part.strip()]
    return []


def first_text(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def stable_id(url: str, source: str, title: str, published_at: str) -> str:
    value = "|".join([url, source, title, published_at])
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def parse_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def random_pool_allowed(item: NewsItem) -> bool:
    full_text = item.full_text
    raw = {
        "headline": item.title,
        "dek": item.summary,
        "body": list(item.body) or [item.summary],
        "source_bundle": [{"name": item.source, "url": item.url, "published_at": item.published_at}],
        "earthquake_classification": item.earthquake_classification,
    }
    text = normalize_for_match(f"{item.title} {item.summary} {full_text}")
    if not item.title or not item.url:
        return False
    if "example.com" in item.url or item.source.lower() in {"test", "mock"}:
        return False
    if item.earthquake_classification in {"seo_generic_earthquake", "minor_earthquake_ticker"}:
        return False
    if is_generic_earthquake_clickbait(raw):
        return False
    if "deprem" in text and item.earthquake_classification and item.earthquake_classification != "serious_earthquake_event":
        return False
    if is_clickbait_article(raw):
        return False
    if item.importance is not None and item.importance > 80:
        return False
    if item.score is not None and 0 <= item.score < 0.35:
        return False
    if item.published_at and is_old(item.published_at):
        return False
    return True


def is_old(value: str, max_age_hours: int = 72) -> bool:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - dt.astimezone(timezone.utc) > timedelta(hours=max_age_hours)


def dedupe_items(items: list[NewsItem]) -> list[NewsItem]:
    seen: set[str] = set()
    deduped: list[NewsItem] = []
    for item in items:
        key = item.url or item.id
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def copy_latest_gazette_to_desktop(
    target_dir: Path | None = None,
    candidates: tuple[Path, ...] = LATEST_GAZETTE_CANDIDATES,
) -> Path:
    available = [path for path in candidates if path.exists() and path.is_file()]
    if not available:
        raise FileNotFoundError("Kopyalanacak gazete çıktısı bulunamadı.")
    return copy_gazette_outputs_to_desktop(available, target_dir)


def copy_gazette_outputs_to_desktop(paths: list[Path], target_dir: Path | None = None) -> Path:
    available = [path for path in paths if path.exists() and path.is_file()]
    if not available:
        raise FileNotFoundError("Kopyalanacak gazete çıktısı bulunamadı.")
    target = target_dir or desktop_gazette_dir()
    target.mkdir(parents=True, exist_ok=True)
    for path in available:
        shutil.copy2(path, target / path.name)
    return target
