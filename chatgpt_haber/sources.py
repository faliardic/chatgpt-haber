from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
import re
from typing import Any

GENERAL_FEEDS = {
    "NTV Türkiye": ("gundem", "https://www.ntv.com.tr/turkiye.rss"),
    "NTV Dünya": ("dunya", "https://www.ntv.com.tr/dunya.rss"),
    "NTV Ekonomi": ("ekonomi", "https://www.ntv.com.tr/ekonomi.rss"),
    "NTV Teknoloji": ("teknoloji", "https://www.ntv.com.tr/teknoloji.rss"),
    "NTV Spor": ("spor", "https://www.ntv.com.tr/spor.rss"),
    "Habertürk Gündem": ("gundem", "https://www.haberturk.com/rss/gundem.xml"),
    "Habertürk Dünya": ("dunya", "https://www.haberturk.com/rss/dunya.xml"),
    "Habertürk Ekonomi": ("ekonomi", "https://www.haberturk.com/rss/ekonomi.xml"),
    "Habertürk Spor": ("spor", "https://www.haberturk.com/rss/spor.xml"),
    "Habertürk Teknoloji": ("teknoloji", "https://www.haberturk.com/rss/teknoloji.xml"),
    "Sözcü Gündem": ("gundem", "https://www.sozcu.com.tr/rss/gundem.xml"),
    "Sözcü Dünya": ("dunya", "https://www.sozcu.com.tr/rss/dunya.xml"),
    "Sözcü Ekonomi": ("ekonomi", "https://www.sozcu.com.tr/rss/ekonomi.xml"),
    "Sözcü Spor": ("spor", "https://www.sozcu.com.tr/rss/spor.xml"),
    "Sözcü Teknoloji": ("teknoloji", "https://www.sozcu.com.tr/rss/teknoloji.xml"),
    "Evrim Ağacı": ("bilim", "https://evrimagaci.org/rss.xml"),
}

ANKARA_FEEDS = {
    "Haberci06 Ankara": ("ankara", "https://haberci06.com/rss"),
    "Başkent Gazete Ankara": ("ankara", "https://www.baskentgazete.com.tr/rss"),
    "Redaktör Haber Yerel": ("ankara", "https://www.redaktorhaber.com/rss"),
    "Ankara Haber Gündemi": ("ankara", "https://ankarahabergundemi.com/feed/"),
}

RADAR = [
    ("ANA KARAR", "Bugünün ana karar sinyali: zamanı, parayı veya iş planını etkileyebilecek başlık.", ("ekonomi", "teknoloji", "gundem")),
    ("ŞANTİYE RADAR", "Şantiye şefliği, saha kontrolü, risk yönetimi veya mesleki değer açısından izlenmeli.", ("ankara", "gundem", "ekonomi")),
    ("STATİK RADAR", "Structural Design Engineer hedefi için teknik sezgi ve yapı güvenliği odağı taşır.", ("bilim", "ankara", "teknoloji")),
    ("YAZILIM + AI", "Mühendislik yazılımları, raporlama ve otomasyon hedeflerini hızlandırabilir.", ("teknoloji", "bilim")),
    ("PARA VE NAKİT", "Borç sıfırlama planı, nakit akışı veya harcama disiplinini etkileyebilir.", ("ekonomi", "gundem")),
    ("ARAÇ VE YOL", "Günlük ulaşım, araç maliyeti, EV planı veya Ankara güzergahı açısından değerli.", ("teknoloji", "ekonomi", "ankara")),
    ("CİHAZ VE ÜRETİM", "İş, öğrenme, çıktı alma veya üretim sistemini kolaylaştırabilecek araç sinyali.", ("teknoloji", "bilim")),
    ("ENERJİ VE DENGE", "Şantiye temposu, kilo hedefi, uyku ve sürdürülebilir çalışma dengesiyle ilişkili.", ("bilim", "teknoloji", "gundem")),
    ("ODAK SİSTEMİ", "Aşırı yüklenmeden düzenli ilerleme, hedef sistemi ve karar kalitesi için izlenmeli.", ("bilim", "teknoloji", "ekonomi")),
    ("KÜLTÜR VE ZİHİN", "Okuma, film, tarih, bilim ve kişisel akademi hattını besleyebilecek içerik.", ("bilim", "ankara", "gundem")),
    ("ANKARA YAŞAM", "Günlük hayatı, iş yolunu, aile planını veya yerel gündemi etkileyebilir.", ("ankara",)),
    ("ÜRETİM MASASI", "Gazete motoru, sosyal medya, AI üretim ve GitHub çalışma sistemi için fikir verebilir.", ("teknoloji", "bilim", "ekonomi")),
]


def clean(value: Any, fallback: str = "") -> str:
    text = unescape(str(value or fallback or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip() or fallback


def make_id(source: str, index: int) -> str:
    text = source.lower()
    for old, new in {"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u"}.items():
        text = text.replace(old, new)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return f"{text}-{index + 1}"


def fetch_map(feed_map: dict[str, tuple[str, str]], per_feed: int = 8) -> list[dict[str, Any]]:
    try:
        import feedparser
    except ImportError:
        return []

    items = []
    seen = set()
    for source, (section, url) in feed_map.items():
        parsed = feedparser.parse(url)
        for entry in parsed.entries[:per_feed]:
            link = str(getattr(entry, "link", url) or url)
            if link in seen:
                continue
            seen.add(link)
            title = clean(getattr(entry, "title", ""), "Başlık")
            summary = clean(getattr(entry, "summary", "") or getattr(entry, "description", ""), title)
            published = getattr(entry, "published", None) or getattr(entry, "updated", None) or datetime.now(timezone.utc).isoformat()
            items.append({
                "id": make_id(source, len(items)),
                "section": section,
                "kicker": section.upper(),
                "headline": title,
                "dek": summary,
                "body": [summary],
                "source_bundle": [{"name": source, "url": link, "published_at": str(published), "source_type": "rss", "is_primary": False}],
                "verification": {"status": "single_source", "checked_at": datetime.now(timezone.utc).isoformat(), "method": ["rss_fetch"], "note": f"{source} RSS akışından alındı."},
                "layout_hint": {"story_size": "secondary", "column_span": 1, "preferred_position": "mid"},
                "image": {},
            })
    return items


def layout(article: dict[str, Any], size: str, span: int = 1, kicker: str | None = None) -> dict[str, Any]:
    item = {**article}
    if kicker is not None:
        item["kicker"] = kicker
    item["layout_hint"] = {"story_size": size, "column_span": span, "preferred_position": "top" if size in {"hero", "lead"} else "mid"}
    return item


def pick(pool: list[dict[str, Any]], start: int, count: int) -> list[dict[str, Any]]:
    if not pool:
        return []
    return [pool[(start + i) % len(pool)] for i in range(count)]


def by_section(pool: list[dict[str, Any]], sections: tuple[str, ...]) -> list[dict[str, Any]]:
    return [item for item in pool if item.get("section") in sections]


def standard_page(page_no: int, name: str, pool: list[dict[str, Any]], start: int, template: str) -> dict[str, Any]:
    selected = pick(pool, start, 32)
    articles = [layout(selected[0], "hero", 5)] if selected else []
    if len(selected) > 1:
        articles.append(layout(selected[1], "lead", 1))
    articles.extend(layout(item, "secondary", 1) for item in selected[2:12])
    briefs = [layout(item, "brief", 1) for item in selected[12:32]]
    return {"page_no": page_no, "template": template, "name": name, "articles": articles, "briefs": briefs}


def radar_page(page_no: int, general: list[dict[str, Any]], ankara: list[dict[str, Any]]) -> dict[str, Any]:
    combined = general + ankara
    used = set()
    articles = []
    for idx, (kicker, effect, sections) in enumerate(RADAR):
        candidates = [a for a in by_section(combined, sections) if a.get("id") not in used] or [a for a in combined if a.get("id") not in used] or combined
        source = candidates[idx % len(candidates)]
        used.add(source.get("id"))
        summary = clean(source.get("dek"), source.get("headline", ""))
        item = {**source}
        item["id"] = f"fatih-radar-{idx + 1}"
        item["kicker"] = kicker
        item["dek"] = f"{effect} Kaynak notu: {summary}"
        item["body"] = [f"Fatih etkisi: {effect}", "Günün aksiyonu: Bu başlığı tek satır karar notuna indir.", summary]
        articles.append(layout(item, "hero" if idx == 0 else "secondary", 5 if idx == 0 else 1, kicker))
    briefs = [layout(item, "brief", 1) for item in pick([a for a in combined if a.get("id") not in used] or combined, 0, 20)]
    return {"page_no": page_no, "template": "radar_page", "name": "Fatih'in Radarı", "articles": articles, "briefs": briefs}


def fetch_rss_articles(limit: int = 96) -> list[dict[str, Any]]:
    return fetch_map(GENERAL_FEEDS, per_feed=8)[:limit]


def issue_from_rss(issue_date: str, paper_size: str) -> dict[str, Any] | None:
    general = fetch_map(GENERAL_FEEDS, per_feed=8)
    ankara = fetch_map(ANKARA_FEEDS, per_feed=8)
    if len(general) < 8:
        return None
    if not ankara:
        ankara = by_section(general, ("gundem", "ekonomi"))
    return {
        "issue": {
            "issue_date": issue_date,
            "edition_name": "Sabah Baskısı",
            "language": "tr-TR",
            "page_count": 4,
            "paper_size": paper_size,
            "title": "CHATGPT HABER",
            "timezone": "Europe/Istanbul",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "edition_note": "NTV, Habertürk, Sözcü, Evrim Ağacı ve yerel Ankara RSS akışlarından otomatik derlendi",
        },
        "pages": [
            standard_page(1, "Manşet", general, 0, "front_page"),
            standard_page(2, "Gündem ve Ekonomi", general, 12, "news_page"),
            standard_page(3, "Ankara Özel Bülteni", ankara, 0, "news_page"),
            radar_page(4, general, ankara),
        ],
    }
