from __future__ import annotations

import re
import unicodedata
from typing import Any


GENERIC_EARTHQUAKE_PATTERNS = (
    r"\bson\s+dakika\s+deprem\s+mi\s+oldu\b",
    r"\baz\s+once\s+deprem\s+nerede\s+oldu\b",
    r"\bdeprem\s+nerede\s+oldu\b",
    r"\bbugun\s+deprem\s+oldu\s+mu\b",
    r"\bson\s+depremler\b",
    r"\bafad\s+son\s+depremler\b",
    r"\bkandilli\s+son\s+depremler\b",
    r"\bcanli\s+deprem\s+(?:haritasi|turkiye\s+haritasi)\b",
    r"\bil\s+il\s+(?:afad\s+)?son\s+depremler\b",
    r"\bistanbul\s+ankara\s+izmir\s+ve\s+il\s+il\b",
    r"\bartci\s+deprem\s+mi\s+oldu\b",
    r"\bson\s+deprem\s+buyuklugu\s+ne\s+kadar\b",
    r"\byakinimdaki\s+depremler\s+nelerdir\b",
    r"\banlik\s+deprem\s+mi\s+oldu\b",
    r"\bdeprem\s+ne\s+zaman\s+ve\s+kac\s+siddetinde\s+oldu\b",
)
ABSOLUTE_BLOCKED_TITLE_PATTERNS = (
    "son dakika deprem mi oldu az once deprem nerede oldu istanbul ankara izmir ve il il afad son depremler 01 haziran 2026",
    "son dakika deprem mi oldu",
    "az once deprem nerede oldu",
    "afad son depremler",
    "kandilli son depremler",
    "canli deprem turkiye haritasi",
    "canli deprem haritasi",
    "yakinimdaki depremler",
    "artci deprem mi oldu",
)
BLOCK_SCAN_FIELDS = (
    "title",
    "headline",
    "summary",
    "description",
    "body",
    "content",
    "text",
    "url",
    "link",
    "slug",
    "canonical",
    "canonical_url",
    "source",
    "category",
    "tags",
)
FORBIDDEN_RENDERED_TEXTS = (
    "Son dakika deprem mi oldu",
    "Az önce deprem nerede oldu",
    "AFAD son depremler",
    "Kandilli son depremler",
    "Yakınımdaki depremler",
    "Anlık deprem mi oldu",
    "canlı deprem Türkiye haritası",
)
SERIOUS_EARTHQUAKE_PATTERNS = (
    r"\b[5-9](?:[.,]\d)?\s+buyuklugunde\b",
    r"\bhasar\b",
    r"\bagir\s+hasar\b",
    r"\byikim\b",
    r"\byikildi\b",
    r"\byarali\b",
    r"\bcan\s+kaybi\b",
    r"\benkaz\b",
    r"\btsunami\b",
    r"\btahliye\b",
    r"\bkurtarma\b",
    r"\bresmi\s+alarm\b",
)


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    for old, new in {"ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c"}.items():
        text = text.replace(old, new)
    return re.sub(r"[^a-z0-9.,]+", " ", text).strip()


def normalize_block_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        value = " ".join(map(str, value))
    elif isinstance(value, dict):
        value = " ".join(map(str, value.values()))
    else:
        value = str(value)
    text = unicodedata.normalize("NFKD", value.casefold().replace("ı", "i").replace("İ", "i"))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def value_from_item(item: Any, field: str) -> Any:
    if isinstance(item, dict):
        return item.get(field, "")
    return getattr(item, field, "")


def item_text_for_blocking(item: Any) -> str:
    parts = [value_from_item(item, field) for field in BLOCK_SCAN_FIELDS]
    return normalize_block_text(" ".join(map(str, parts)))


def is_absolute_blocked_content(item: Any) -> bool:
    text = item_text_for_blocking(item)
    return any(normalize_block_text(pattern) in text for pattern in ABSOLUTE_BLOCKED_TITLE_PATTERNS)


def item_text(item: dict[str, Any]) -> str:
    body = item.get("body", "")
    if isinstance(body, list):
        body = " ".join(str(value) for value in body)
    sources = item.get("source_bundle") or item.get("sources") or []
    source_text = ""
    if isinstance(sources, list):
        source_text = " ".join(str(source) for source in sources)
    fields = (
        "title",
        "headline",
        "summary",
        "description",
        "dek",
        "url",
        "link",
        "slug",
        "canonical",
    )
    return normalize_text(" ".join(str(item.get(field) or "") for field in fields) + f" {body} {source_text}")


def contains_serious_earthquake_signal(text: str) -> bool:
    if any(re.search(pattern, text) for pattern in SERIOUS_EARTHQUAKE_PATTERNS):
        if any(negative in text for negative in ("hasar bildirilmedi", "can kaybi yok", "yarali yok")):
            return bool(re.search(r"\b[5-9](?:[.,]\d)?\s+buyuklugunde\b", text))
        return True
    return False


def is_generic_earthquake_clickbait(item: dict[str, Any]) -> bool:
    if is_absolute_blocked_content(item):
        return True
    text = item_text(item)
    if "deprem" not in text:
        return False
    generic = any(re.search(pattern, text) for pattern in GENERIC_EARTHQUAKE_PATTERNS)
    return generic and not contains_serious_earthquake_signal(text)


def hard_reject_item(item: Any, reason: str = "seo_generic_earthquake_clickbait") -> Any:
    updates = {
        "accepted": False,
        "rejected": True,
        "reject_reason": reason,
        "importance": 0,
        "score": 0,
        "exclude_from_homepage": True,
        "exclude_from_pdf": True,
        "exclude_from_random": True,
        "exclude_from_latest": True,
        "exclude_from_detail_pages": True,
        "earthquake_classification": "seo_generic_earthquake",
    }
    if isinstance(item, dict):
        item.update(updates)
        return item
    for key, value in updates.items():
        try:
            setattr(item, key, value)
        except Exception:
            continue
    return item


def apply_absolute_block_filters(item: Any) -> Any:
    if is_absolute_blocked_content(item):
        return hard_reject_item(item)
    return item


def apply_hard_reject_filters(item: dict[str, Any]) -> dict[str, Any]:
    apply_absolute_block_filters(item)
    if item.get("rejected") is True:
        return item
    if is_generic_earthquake_clickbait(item):
        hard_reject_item(item)
    return item


def is_hard_rejected(item: dict[str, Any]) -> bool:
    return bool(apply_hard_reject_filters(item).get("rejected") or item.get("exclude_from_pdf"))


def item_rejected(item: Any) -> bool:
    if is_absolute_blocked_content(item):
        return True
    if isinstance(item, dict):
        return bool(
            item.get("rejected") is True
            or item.get("accepted") is False
            or item.get("exclude_from_pdf") is True
            or item.get("exclude_from_homepage") is True
            or item.get("exclude_from_detail_pages") is True
        )
    return bool(
        getattr(item, "rejected", False) is True
        or getattr(item, "accepted", True) is False
        or getattr(item, "exclude_from_pdf", False) is True
        or getattr(item, "exclude_from_homepage", False) is True
        or getattr(item, "exclude_from_detail_pages", False) is True
    )


def sanitize_items_or_fail(items: list[Any] | tuple[Any, ...] | None, stage: str) -> list[Any]:
    clean: list[Any] = []
    rejected: list[Any] = []
    for item in items or []:
        apply_absolute_block_filters(item)
        if isinstance(item, dict):
            apply_hard_reject_filters(item)
        if item_rejected(item):
            rejected.append(item)
            continue
        clean.append(item)

    print(f"[GAZETTE FILTER] stage={stage} input={len(items or [])} clean={len(clean)} rejected={len(rejected)}")
    for item in clean:
        if is_absolute_blocked_content(item):
            title = value_from_item(item, "title") or value_from_item(item, "headline")
            raise RuntimeError(
                f"[GAZETTE BLOCKER FAILED] Forbidden earthquake SEO article survived at stage={stage}: {title}"
            )
    return clean


def assert_no_forbidden_rendered_text(rendered_text: str, stage: str, *, quiet: bool = False) -> None:
    normalized = normalize_block_text(rendered_text)
    hits = [phrase for phrase in FORBIDDEN_RENDERED_TEXTS if normalize_block_text(phrase) in normalized]
    if hits:
        raise RuntimeError(f"[GAZETTE FINAL VALIDATION FAILED] stage={stage} forbidden_text_found={hits}")
    if not quiet:
        print(f"[GAZETTE FINAL VALIDATION] stage={stage} forbidden_phrase_result=clean")
