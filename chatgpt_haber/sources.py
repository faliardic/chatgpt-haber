from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


DEFAULT_FEEDS = {
    "TRT Haber": "https://www.trthaber.com/xml_mobile.php?tur=xml_genel&kategori=gundem",
    "Anadolu Ajansı": "https://www.aa.com.tr/tr/rss/default?cat=guncel",
    "TCMB": "https://www.tcmb.gov.tr/wps/wcm/connect/tr/tcmb+tr/main+menu/duyurular/rss",
}


def fetch_rss_articles(limit: int = 12) -> list[dict[str, Any]]:
    try:
        import feedparser
    except ImportError:
        return []

    articles: list[dict[str, Any]] = []
    for source_name, url in DEFAULT_FEEDS.items():
        parsed = feedparser.parse(url)
        for entry in parsed.entries[: max(1, limit // len(DEFAULT_FEEDS))]:
            published = (
                getattr(entry, "published", None)
                or getattr(entry, "updated", None)
                or datetime.now(timezone.utc).isoformat()
            )
            title = str(getattr(entry, "title", "Başlık"))
            summary = str(getattr(entry, "summary", title))
            link = str(getattr(entry, "link", url))
            articles.append(
                {
                    "id": f"{source_name.lower().replace(' ', '-')}-{len(articles) + 1}",
                    "section": "gundem" if source_name != "TCMB" else "ekonomi",
                    "headline": title,
                    "dek": summary,
                    "body": [summary],
                    "source_bundle": [
                        {
                            "name": source_name,
                            "url": link,
                            "published_at": published,
                            "source_type": "institution" if source_name == "TCMB" else "rss",
                            "is_primary": source_name == "TCMB",
                        }
                    ],
                    "verification": {
                        "status": "single_source",
                        "checked_at": datetime.now(timezone.utc).isoformat(),
                        "method": ["primary_source"],
                        "note": f"{source_name} RSS akışından alındı.",
                    },
                    "layout_hint": {"story_size": "secondary", "column_span": 2, "preferred_position": "mid"},
                    "image": {},
                }
            )
    return articles[:limit]


def issue_from_rss(issue_date: str, paper_size: str) -> dict[str, Any] | None:
    articles = fetch_rss_articles()
    if len(articles) < 3:
        return None

    articles[0]["layout_hint"] = {"story_size": "hero", "column_span": 5, "preferred_position": "top"}
    articles[1]["layout_hint"] = {"story_size": "lead", "column_span": 4, "preferred_position": "top"}
    articles[2]["layout_hint"] = {"story_size": "radar", "column_span": 2, "preferred_position": "top"}
    return {
        "issue": {
            "issue_date": issue_date,
            "edition_name": "Sabah Baskısı",
            "language": "tr-TR",
            "page_count": 3,
            "paper_size": paper_size,
            "title": "CHATGPT HABER",
            "timezone": "Europe/Istanbul",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "edition_note": "TRT Haber, AA ve TCMB RSS akışlarından otomatik derlendi",
        },
        "pages": [
            {"page_no": 1, "template": "front_page", "name": "Manşet", "articles": articles[:5], "briefs": articles[5:8]},
            {"page_no": 2, "template": "news_page", "name": "Gündem ve Ekonomi", "articles": articles[1:7], "briefs": []},
            {"page_no": 3, "template": "radar_page", "name": "Fatih'in Radarı", "articles": articles[2:8], "briefs": []},
        ],
    }
