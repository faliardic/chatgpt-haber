from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import mimetypes
import re
import unicodedata
from urllib.parse import urljoin, urlparse
from typing import Any

from .issue import slugify


DEFAULT_FEEDS = {
    "NTV Türkiye": "https://www.ntv.com.tr/turkiye.rss",
    "NTV Dünya": "https://www.ntv.com.tr/dunya.rss",
    "NTV Ekonomi": "https://www.ntv.com.tr/ekonomi.rss",
    "NTV Teknoloji": "https://www.ntv.com.tr/teknoloji.rss",
    "NTV Spor": "https://www.ntv.com.tr/sporskor.rss",
    "Habertürk Gündem": "https://www.haberturk.com/rss/kategori/gundem.xml",
    "Habertürk Dünya": "https://www.haberturk.com/rss/kategori/dunya.xml",
    "Habertürk Ekonomi": "https://www.haberturk.com/rss/ekonomi.xml",
    "Habertürk Spor": "https://www.haberturk.com/rss/spor.xml",
    "Habertürk Teknoloji": "https://www.haberturk.com/rss/kategori/teknoloji.xml",
    "Sözcü Gündem": "https://www.sozcu.com.tr/feeds-rss-category-gundem",
    "Sözcü Dünya": "https://www.sozcu.com.tr/feeds-rss-category-dunya",
    "Sözcü Ekonomi": "https://www.sozcu.com.tr/feeds-rss-category-ekonomi",
    "Sözcü Spor": "https://www.sozcu.com.tr/feeds-rss-category-spor",
    "Sözcü Teknoloji": "https://www.sozcu.com.tr/feeds-rss-category-bilim-teknoloji",
    "Evrim Ağacı": "https://evrimagaci.org/rss.xml",
}

ANKARA_LOCAL_FEEDS = {
    "Haberci06 Ankara": "https://haberci06.com/rss/category/ankara",
    "Başkent Gazete Ankara": "https://www.baskentgazete.com.tr/rss/ankara",
    "Redaktör Haber Yerel": "https://www.redaktorhaber.com/rss/yerel-haberler",
    "Ankara Haber Gündemi": "https://ankarahabergundemi.com/rss",
}

PERSONAL_RADAR_CATEGORIES = [
    {
        "kicker": "ANA KARAR",
        "keywords": ("faiz", "kredi", "ankara", "yapay zeka", "inşaat", "deprem", "ulaşım", "ekonomi"),
        "impact": "Bugünün ana karar sinyali: zamanı, parayı veya iş planını etkileyebilecek başlık.",
        "action": "Bugün tek karar notu çıkar: ertele, takip et veya aksiyona çevir.",
    },
    {
        "kicker": "ŞANTİYE RADAR",
        "keywords": (
            "inşaat",
            "şantiye",
            "yapı",
            "ruhsat",
            "iskan",
            "iskân",
            "yapı denetim",
            "toki",
            "kentsel dönüşüm",
            "konut",
            "beton",
            "demir",
            "iş güvenliği",
            "deprem",
            "müteahhit",
        ),
        "preferred_sections": ("ankara", "ekonomi"),
        "impact": "Şantiye şefliği, saha kontrolü, risk yönetimi veya mesleki değer açısından izlenmeli.",
        "action": "Mevzuat, maliyet veya saha riski doğuruyorsa kısa kontrol listene ekle.",
    },
    {
        "kicker": "STATİK RADAR",
        "keywords": (
            "deprem",
            "afet",
            "betonarme",
            "güçlendirme",
            "kolon",
            "kiriş",
            "temel",
            "yapı güvenliği",
            "hasar",
            "mühendislik",
            "yönetmelik",
            "denetim",
        ),
        "preferred_sections": ("ankara", "gundem"),
        "impact": "Structural Design Engineer hedefi için teknik sezgi ve güvenli tasarım odağı taşır.",
        "action": "Teknik terim veya hata örneği varsa not al; ileride statik çalışma dosyana taşı.",
    },
    {
        "kicker": "YAZILIM + AI",
        "keywords": (
            "python",
            "yapay zeka",
            "ai",
            "github",
            "copilot",
            "chatgpt",
            "gemini",
            "claude",
            "android",
            "vscode",
            "api",
            "veri",
            "otomasyon",
            "uygulama",
        ),
        "preferred_sections": ("teknoloji",),
        "impact": "Kendi mühendislik yazılımlarını, raporlama ve otomasyon hedeflerini hızlandırabilir.",
        "action": "Araç veya yöntem tekrar kullanılabiliyorsa proje fikirleri listene bir satır ekle.",
    },
    {
        "kicker": "PARA VE NAKİT",
        "keywords": (
            "faiz",
            "kredi",
            "kart",
            "borç",
            "tcmb",
            "bdkk",
            "enflasyon",
            "mevduat",
            "altın",
            "döviz",
            "yakıt",
            "kira",
            "maaş",
            "ekonomi",
        ),
        "preferred_sections": ("ekonomi",),
        "impact": "Haziran-Ekim borç sıfırlama planı, nakit akışı veya harcama disiplini etkilenebilir.",
        "action": "Bu haber ödeme planını etkiliyorsa bütçe dosyanda tek kalemi güncelle.",
    },
    {
        "kicker": "ARAÇ VE YOL",
        "keywords": (
            "otomobil",
            "elektrikli araç",
            "şarj",
            "ötv",
            "mtv",
            "kasko",
            "sigorta",
            "yakıt",
            "trafik",
            "ulaşım",
            "metro",
            "ankara yolu",
            "motosiklet",
        ),
        "preferred_sections": ("ekonomi", "ankara"),
        "impact": "Günlük ulaşım, araç maliyeti, gelecek EV planı veya Ankara güzergahı açısından değerli.",
        "action": "Maliyet veya güzergah etkisi varsa araç/yol radarına işaret koy.",
    },
    {
        "kicker": "CİHAZ VE ÜRETİM",
        "keywords": (
            "tablet",
            "telefon",
            "android",
            "dex",
            "laptop",
            "asus",
            "samsung",
            "logitech",
            "yazıcı",
            "pdf",
            "canva",
            "not",
            "github",
            "vscode",
        ),
        "preferred_sections": ("teknoloji",),
        "impact": "İş, öğrenme, çıktı alma veya üretim sistemini kolaylaştırabilecek araç sinyali.",
        "action": "Gerçek verim katkısı varsa ekipman/araç notlarına ekle; sadece tüketimse ele.",
    },
    {
        "kicker": "ENERJİ VE DENGE",
        "keywords": (
            "sağlık",
            "uyku",
            "beslenme",
            "kilo",
            "protein",
            "diz",
            "ortopedi",
            "yorgunluk",
            "egzersiz",
            "antrenman",
            "iş güvenliği",
            "baret",
            "stres",
        ),
        "preferred_sections": ("teknoloji", "ankara"),
        "impact": "Şantiye temposu, kilo hedefi, uyku ve sürdürülebilir çalışma dengesiyle ilişkili.",
        "action": "Bugün uygulanabilir tek sağlık davranışı seç: uyku, yürüyüş, su veya protein.",
    },
    {
        "kicker": "ODAK SİSTEMİ",
        "keywords": (
            "alışkanlık",
            "odak",
            "verimlilik",
            "planlama",
            "proje",
            "motivasyon",
            "strateji",
            "karar",
            "öğrenme",
        ),
        "impact": "Aşırı yüklenmeden düzenli ilerlemek için sistem, dikkat ve karar kalitesine dokunur.",
        "action": "Bir sonraki çalışma bloğu için en küçük net hedefi yaz.",
    },
    {
        "kicker": "KÜLTÜR VE ZİHİN",
        "keywords": (
            "kitap",
            "edebiyat",
            "roman",
            "çeviri",
            "sinema",
            "film",
            "tarih",
            "felsefe",
            "psikoloji",
            "kültür",
            "sanat",
            "ankara konser",
        ),
        "preferred_sections": ("ankara", "teknoloji"),
        "impact": "Kişisel akademi, okuma hattı ve zihinsel derinlik için takip edilebilir.",
        "action": "Okuma/izleme listene girecekse tek cümlelik gerekçeyle kaydet.",
    },
    {
        "kicker": "ANKARA YAŞAM",
        "keywords": (
            "ankara",
            "sincan",
            "mamak",
            "kızılay",
            "çankaya",
            "keçiören",
            "ulaşım",
            "trafik",
            "toki",
            "konut",
            "belediye",
            "etkinlik",
            "altyapı",
        ),
        "preferred_sections": ("ankara",),
        "impact": "Günlük hayat, iş yolu, aile düzeni veya Ankara gelecek planı açısından temas edebilir.",
        "action": "Güzergah, zaman veya aile planına etkisi varsa takvime/kısa nota geçir.",
    },
    {
        "kicker": "ÜRETİM MASASI",
        "keywords": (
            "gazete",
            "sosyal medya",
            "canva",
            "içerik",
            "tiktok",
            "algoritma",
            "editör",
            "görsel",
            "otomasyon",
            "yapay zeka",
        ),
        "preferred_sections": ("teknoloji",),
        "impact": "Gazete motoru, içerik üretimi, mizanpaj veya tek komutla üretim sistemine ilham verebilir.",
        "action": "Gazete motoruna dönüştürülebilecek fikir varsa backlog'a bir madde aç.",
    },
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
REQUEST_HEADERS = {
    "User-Agent": "ChatGPT-Haber/0.2 (+https://example.com; print issue builder)",
}
STOP_WORDS = {
    "aciklandi",
    "ardindan",
    "baskan",
    "baskani",
    "belli",
    "bir",
    "bugun",
    "cumhurbaskani",
    "dakika",
    "de",
    "da",
    "dedi",
    "den",
    "icin",
    "ile",
    "son",
    "sonra",
    "ve",
    "ya",
    "yeni",
}


def entry_image_url(entry: Any) -> str:
    for attr in ("media_content", "media_thumbnail"):
        values = getattr(entry, attr, None)
        if isinstance(values, list):
            for item in values:
                if isinstance(item, dict) and item.get("url"):
                    return str(item["url"])

    for link in getattr(entry, "links", []) or []:
        if not isinstance(link, dict):
            continue
        href = str(link.get("href") or "")
        mime_type = str(link.get("type") or "")
        rel = str(link.get("rel") or "")
        if href and (mime_type.startswith("image/") or rel in {"enclosure", "image"}):
            return href

    image = getattr(entry, "image", None)
    if isinstance(image, dict) and image.get("href"):
        return str(image["href"])
    if isinstance(image, dict) and image.get("url"):
        return str(image["url"])
    return ""


def page_image_url(page_url: str) -> str:
    if not page_url:
        return ""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return ""

    try:
        response = requests.get(page_url, headers=REQUEST_HEADERS, timeout=8)
        response.raise_for_status()
    except Exception:
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    selectors = [
        ("meta", {"property": "og:image"}, "content"),
        ("meta", {"name": "twitter:image"}, "content"),
        ("meta", {"property": "twitter:image"}, "content"),
        ("link", {"rel": "image_src"}, "href"),
    ]
    for tag_name, attrs, value_attr in selectors:
        tag = soup.find(tag_name, attrs=attrs)
        value = tag.get(value_attr) if tag else ""
        if value:
            return urljoin(page_url, str(value))
    return ""


def extension_from_response(url: str, content_type: str) -> str:
    parsed_ext = Path(urlparse(url).path).suffix.lower()
    if parsed_ext in IMAGE_EXTENSIONS:
        return ".jpg" if parsed_ext == ".jpeg" else parsed_ext

    mime = content_type.split(";", 1)[0].strip().lower()
    guessed = mimetypes.guess_extension(mime) or ".jpg"
    if guessed == ".jpe":
        return ".jpg"
    return guessed if guessed in IMAGE_EXTENSIONS else ".jpg"


def image_dimensions(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image
    except ImportError:
        return 0, 0

    try:
        with Image.open(path) as image:
            return image.size
    except Exception:
        return 0, 0


def fallback_font(size: int, bold: bool = False):
    from PIL import ImageFont

    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default(size=size)


def wrapped_lines(draw: Any, text: str, font: Any, max_width: int, max_lines: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if current and bbox[2] - bbox[0] > max_width:
            lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break
        else:
            current = candidate
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines


def fallback_image(article: dict[str, Any], image_dir: Path) -> dict[str, Any] | None:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None

    headline = str(article.get("headline") or "Haber")
    section = str(article.get("section") or "gundem").upper()
    article_id = str(article.get("id") or headline)
    image_dir.mkdir(parents=True, exist_ok=True)
    path = image_dir / f"{slugify(article_id, 'story')}-fallback.jpg"

    palette = {
        "ANKARA": ("#f2efe8", "#243447", "#b14a32"),
        "EKONOMI": ("#edf3f8", "#243b53", "#2f6f9f"),
        "GUNDEM": ("#f0f4f8", "#2f3a3f", "#8a4f2a"),
        "SPOR": ("#eaf6ef", "#174a3c", "#2f855a"),
        "TEKNOLOJI": ("#eef2ff", "#243447", "#4c51bf"),
        "DUNYA": ("#f4f1ea", "#2f3a3f", "#8c6d31"),
    }
    bg, fg, accent = palette.get(slugify(section, "gundem").upper(), ("#f4f4f2", "#252525", "#777777"))
    image = Image.new("RGB", (1200, 720), bg)
    draw = ImageDraw.Draw(image)
    font_large = fallback_font(58, bold=True)
    font_small = fallback_font(28, bold=True)
    font_caption = fallback_font(24)

    draw.rectangle((0, 0, 1200, 720), fill=bg)
    draw.rectangle((0, 0, 1200, 74), fill=fg)
    draw.rectangle((0, 646, 1200, 720), fill=fg)
    draw.rectangle((48, 112, 1152, 608), outline=accent, width=8)
    draw.rectangle((80, 144, 240, 154), fill=accent)
    draw.text((80, 34), section, fill="#ffffff", font=font_small)

    lines = wrapped_lines(draw, headline, font_large, 980, 4)
    y = 250
    for line in lines:
        draw.text((92, y), line, fill=fg, font=font_large)
        y += 70
    draw.text((92, 650), "CHATGPT HABER | TEMSİLİ GÖRSEL", fill="#ffffff", font=font_caption)
    image.save(path, quality=88)
    return {"path": str(path), "source_url": "", "width": 1200, "height": 720}


def download_image(image_url: str, image_dir: Path, article_id: str) -> dict[str, Any] | None:
    if not image_url:
        return None
    try:
        import requests
    except ImportError:
        return None

    try:
        response = requests.get(image_url, headers=REQUEST_HEADERS, timeout=12)
        response.raise_for_status()
    except Exception:
        return None

    content_type = response.headers.get("content-type", "")
    if content_type and not content_type.lower().startswith("image/"):
        return None

    image_dir.mkdir(parents=True, exist_ok=True)
    safe_id = slugify(article_id, "story")
    ext = extension_from_response(image_url, content_type)
    path = image_dir / f"{safe_id}{ext}"
    path.write_bytes(response.content)
    width, height = image_dimensions(path)
    if width <= 0 or height <= 0:
        path.unlink(missing_ok=True)
        return None
    return {"path": str(path), "source_url": image_url, "width": width, "height": height}


def ensure_article_image(article: dict[str, Any], image_dir: Path) -> None:
    image = article.get("image")
    if isinstance(image, dict) and image.get("path"):
        return

    source_bundle = article.get("source_bundle") if isinstance(article.get("source_bundle"), list) else []
    source = source_bundle[0] if source_bundle and isinstance(source_bundle[0], dict) else {}
    source_url = str(source.get("url") or "")
    image_url = str(article.get("image_url") or "")
    if not image_url:
        image_url = page_image_url(source_url)

    downloaded = download_image(image_url, image_dir, str(article.get("id") or article.get("headline") or "story"))
    if not downloaded:
        downloaded = fallback_image(article, image_dir)
    if not downloaded:
        return

    article["image"] = {
        "path": downloaded["path"],
        "source_url": downloaded["source_url"] or source_url,
        "alt": str(article.get("headline") or "Haber fotoğrafı"),
        "caption": str(article.get("dek") or article.get("headline") or "Haber fotoğrafı"),
        "credit": str(source.get("name") or "Kaynak"),
        "width": downloaded["width"],
        "height": downloaded["height"],
        "crop": "landscape",
    }


def enrich_issue_images(issue_data: dict[str, Any], image_dir: Path) -> dict[str, Any]:
    seen: set[int] = set()
    for page in issue_data.get("pages", []):
        if not isinstance(page, dict):
            continue
        for collection_name in ("articles", "briefs"):
            collection = page.get(collection_name, [])
            if not isinstance(collection, list):
                continue
            for article in collection:
                if not isinstance(article, dict):
                    continue
                if article.get("layout_hint", {}).get("story_size") == "brief":
                    continue
                object_id = id(article)
                if object_id in seen:
                    continue
                seen.add(object_id)
                ensure_article_image(article, image_dir)
    return issue_data


def section_for_source(source_name: str) -> str:
    source_key = source_name.lower()
    if "ankara" in source_key or "yerel" in source_key:
        return "ankara"
    if any(value in source_key for value in ("ekonomi", "tcmb")):
        return "ekonomi"
    if "spor" in source_key:
        return "spor"
    if any(value in source_key for value in ("teknoloji", "evrim")):
        return "teknoloji"
    if "dünya" in source_key or "dunya" in source_key:
        return "dunya"
    return "gundem"


def normalize_for_match(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    for old, new in {"ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c"}.items():
        text = text.replace(old, new)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def match_tokens(article: dict[str, Any]) -> set[str]:
    text = normalize_for_match(f"{article.get('headline', '')} {article.get('dek', '')}")
    return {token for token in text.split() if len(token) > 2 and token not in STOP_WORDS}


def image_match_key(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    return normalize_for_match(Path(parsed.path).stem)


def article_similarity(left: dict[str, Any], right: dict[str, Any]) -> float:
    left_tokens = match_tokens(left)
    right_tokens = match_tokens(right)
    if not left_tokens or not right_tokens:
        return 0
    overlap = len(left_tokens & right_tokens)
    return overlap / max(1, min(len(left_tokens), len(right_tokens)))


def is_duplicate_article(candidate: dict[str, Any], selected: list[dict[str, Any]]) -> bool:
    candidate_image = image_match_key(str(candidate.get("image_url") or ""))
    for article in selected:
        if candidate_image and candidate_image == image_match_key(str(article.get("image_url") or "")):
            return True
        same_section = candidate.get("section") == article.get("section")
        threshold = 0.58 if same_section else 0.68
        if article_similarity(candidate, article) >= threshold:
            return True
    return False


def dedupe_similar_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for article in articles:
        if not is_duplicate_article(article, selected):
            article["importance"] = len(selected) + 1
            selected.append(article)
    return selected


def parse_feed_articles(feeds: dict[str, str], limit: int) -> list[dict[str, Any]]:
    try:
        import feedparser
    except ImportError:
        return []

    by_source: list[list[dict[str, Any]]] = []
    seen_links: set[str] = set()
    per_feed_limit = max(5, limit // max(1, len(feeds)))
    for source_name, url in feeds.items():
        parsed = feedparser.parse(url)
        source_articles: list[dict[str, Any]] = []
        for entry in parsed.entries[:per_feed_limit]:
            published = (
                getattr(entry, "published", None)
                or getattr(entry, "updated", None)
                or datetime.now(timezone.utc).isoformat()
            )
            title = str(getattr(entry, "title", "Başlık"))
            summary = str(getattr(entry, "summary", title))
            link = str(getattr(entry, "link", url))
            if link in seen_links:
                continue
            seen_links.add(link)
            image_url = entry_image_url(entry)
            section = section_for_source(source_name)
            source_articles.append(
                {
                    "id": f"{source_name.lower().replace(' ', '-')}-{len(source_articles) + 1}",
                    "section": section,
                    "headline": title,
                    "importance": len(source_articles) + 1,
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
                    "image_url": image_url,
                }
            )
        if source_articles:
            by_source.append(source_articles)

    articles: list[dict[str, Any]] = []
    max_source_len = max((len(items) for items in by_source), default=0)
    for idx in range(max_source_len):
        for source_articles in by_source:
            if idx < len(source_articles):
                source_articles[idx]["importance"] = len(articles) + 1
                articles.append(source_articles[idx])
    return dedupe_similar_articles(articles)[:limit]


def fetch_rss_articles(limit: int = 120) -> list[dict[str, Any]]:
    return parse_feed_articles(DEFAULT_FEEDS, limit)


def fetch_ankara_local_articles(limit: int = 60) -> list[dict[str, Any]]:
    return parse_feed_articles(ANKARA_LOCAL_FEEDS, limit)


def page_articles(source_articles: list[dict[str, Any]], start: int = 0) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    layouts = [
        {"story_size": "hero", "column_span": 1, "preferred_position": "top"},
        {"story_size": "lead", "column_span": 1, "preferred_position": "top"},
    ] + [{"story_size": "secondary", "column_span": 1, "preferred_position": "mid"} for _ in range(10)]

    main_articles = deepcopy(source_articles[start : start + 12])
    if len(main_articles) < 12:
        main_articles.extend(deepcopy(source_articles[: 12 - len(main_articles)]))
    for offset, (article, layout_hint) in enumerate(zip(main_articles, layouts)):
        article["importance"] = offset + 1
        article["layout_hint"] = layout_hint

    rail_articles = deepcopy(source_articles[start + 12 : start + 32])
    if len(rail_articles) < 20:
        rail_articles.extend(deepcopy(source_articles[: 20 - len(rail_articles)]))
    for offset, article in enumerate(rail_articles[:20]):
        article["importance"] = offset + 1
        article["layout_hint"] = {"story_size": "brief", "column_span": 1, "preferred_position": "rail"}
        article["image"] = {}
    return main_articles[:12], rail_articles[:20]


def ankara_articles(source_articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keywords = (
        "ankara",
        "başkent",
        "baskent",
        "altındağ",
        "cankaya",
        "çankaya",
        "keçiören",
        "mamak",
        "yenimahalle",
        "sincan",
        "etimesgut",
        "pursaklar",
        "gölbaşı",
        "polatlı",
        "kızılcahamam",
        "beypazarı",
        "nallıhan",
        "ayaş",
        "çubuk",
        "elmadag",
        "elmadag",
        "mahalle",
        "ulaşım",
        "metro",
        "ego",
        "askı",
        "park",
        "pazar",
        "esnaf",
        "etkinlik",
        "konser",
        "kültür",
        "okul",
        "trafik",
        "yangın",
        "kaza",
        "belediye",
    )
    selected = []
    fallback = []
    for article in source_articles:
        text = f"{article.get('headline', '')} {article.get('dek', '')} {article.get('section', '')}".lower()
        if any(keyword in text for keyword in keywords):
            selected.append(article)
        elif article.get("section") in {"gundem", "ankara"}:
            fallback.append(article)
    selected.extend(article for article in fallback if article not in selected)
    selected.extend(article for article in source_articles if article not in selected)
    return selected


def article_text(article: dict[str, Any]) -> str:
    return " ".join(
        [
            str(article.get("headline") or ""),
            str(article.get("dek") or ""),
            str(article.get("section") or ""),
            str(article.get("source_bundle", [{}])[0].get("name") if article.get("source_bundle") else ""),
        ]
    ).lower()


def keyword_score(article: dict[str, Any], keywords: tuple[str, ...]) -> int:
    text = article_text(article)
    return sum(3 if keyword in text else 0 for keyword in keywords) + sum(
        1 for word in text.split() if any(keyword in word for keyword in keywords)
    )


def category_score(article: dict[str, Any], category: dict[str, Any]) -> int:
    score = keyword_score(article, category["keywords"])
    preferred_sections = category.get("preferred_sections", ())
    if article.get("section") in preferred_sections:
        score += 8
    return score


def best_article_for_category(
    articles: list[dict[str, Any]],
    category: dict[str, Any],
    used_links: set[str],
) -> dict[str, Any]:
    available = [
        article
        for article in articles
        if article.get("source_bundle")
        and article["source_bundle"][0].get("url")
        and article["source_bundle"][0]["url"] not in used_links
    ]
    if not available:
        available = articles

    scored = sorted(
        available,
        key=lambda article: (category_score(article, category), -int(article.get("importance", 999))),
        reverse=True,
    )
    return deepcopy(scored[0])


def personalize_article(article: dict[str, Any], category: dict[str, Any], importance: int) -> dict[str, Any]:
    original_dek = str(article.get("dek") or article.get("headline") or "")
    article["id"] = f"fatih-radar-{importance}-{slugify(category['kicker'], 'radar')}"
    article["section"] = "radar"
    article["kicker"] = category["kicker"]
    article["importance"] = importance
    article["dek"] = f"{category['impact']} Kaynak notu: {original_dek}"
    article["body"] = [
        f"Fatih etkisi: {category['impact']}",
        f"Günün aksiyonu: {category['action']}",
        original_dek,
    ]
    article["layout_hint"] = {
        "story_size": "hero" if importance == 1 else "lead" if importance == 2 else "secondary",
        "column_span": 1,
        "preferred_position": "top" if importance <= 2 else "mid",
    }
    return article


def personal_radar_page_articles(
    general_articles: list[dict[str, Any]],
    ankara_local: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pool = general_articles + ankara_local
    if not pool:
        return [], []

    used_links: set[str] = set()
    main_articles: list[dict[str, Any]] = []
    for idx, category in enumerate(PERSONAL_RADAR_CATEGORIES, start=1):
        article = best_article_for_category(pool, category, used_links)
        if article.get("source_bundle"):
            used_links.add(article["source_bundle"][0].get("url", ""))
        main_articles.append(personalize_article(article, category, idx))

    all_keywords = tuple(keyword for category in PERSONAL_RADAR_CATEGORIES for keyword in category["keywords"])
    rail_candidates = [
        deepcopy(article)
        for article in sorted(pool, key=lambda article: keyword_score(article, all_keywords), reverse=True)
        if article.get("source_bundle") and article["source_bundle"][0].get("url") not in used_links
    ]
    if len(rail_candidates) < 20:
        rail_candidates.extend(deepcopy(article) for article in pool if article not in rail_candidates)

    rail_articles = rail_candidates[:20]
    for idx, article in enumerate(rail_articles, start=1):
        article["section"] = "radar"
        article["kicker"] = "FATİH RADARI"
        article["importance"] = idx
        article["layout_hint"] = {"story_size": "brief", "column_span": 1, "preferred_position": "rail"}
        article["image"] = {}
    return main_articles, rail_articles


def issue_from_rss(issue_date: str, paper_size: str, image_dir: Path | None = None) -> dict[str, Any] | None:
    articles = fetch_rss_articles()
    if len(articles) < 3:
        return None

    front_articles, front_briefs = page_articles(articles, 0)
    inside_articles, inside_briefs = page_articles(articles, 32)
    ankara_source = fetch_ankara_local_articles()
    if len(ankara_source) < 32:
        ankara_source.extend(article for article in ankara_articles(articles) if article not in ankara_source)
    ankara_main, ankara_briefs = page_articles(ankara_source, 0)
    for article in ankara_main + ankara_briefs:
        article["section"] = "ankara"
        article["kicker"] = "ANKARA"
    issue_data = {
        "issue": {
            "issue_date": issue_date,
            "edition_name": "Anlık Baskı",
            "language": "tr-TR",
            "page_count": 3,
            "paper_size": paper_size,
            "title": "CHATGPT HABER",
            "timezone": "Europe/Istanbul",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "edition_note": "NTV, Habertürk, Sözcü ve Evrim Ağacı RSS akışlarından otomatik derlendi",
        },
        "pages": [
            {"page_no": 1, "template": "front_page", "name": "Manşet", "articles": front_articles, "briefs": front_briefs},
            {"page_no": 2, "template": "news_page", "name": "Gündem ve Ekonomi", "articles": inside_articles, "briefs": inside_briefs},
            {"page_no": 3, "template": "news_page", "name": "Ankara Özel Bülteni", "articles": ankara_main, "briefs": ankara_briefs},
        ],
    }
    if image_dir is not None:
        enrich_issue_images(issue_data, image_dir)
    return issue_data
