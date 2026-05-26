from pathlib import Path
import json
import re
import sys


BASE_DIR = Path(__file__).resolve().parent
ISSUE_PATH = BASE_DIR / "data" / "issue.json"


VALID_STATUSES = {
    "confirmed",
    "developing",
    "rumor",
    "analysis",
}


VALID_CATEGORIES = {
    "front_page",
    "politics",
    "economy",
    "technology_science",
    "culture_arts",
    "lifestyle",
    "sports",
    "transfer_file",
}


SECTION_TO_CATEGORY = {
    "front_page": "front_page",
    "politics": "politics",
    "economy": "economy",
    "technology_science": "technology_science",
    "culture_arts": "culture_arts",
    "lifestyle": "lifestyle",
    "sports": "sports",
    "transfer_file": "transfer_file",
}


def fail(message: str) -> None:
    print(f"HATA: {message}")
    sys.exit(1)


def slugify(text: str, fallback: str) -> str:
    if not isinstance(text, str) or not text.strip():
        text = fallback

    text = text.lower()

    replacements = {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")

    return text or fallback


def clean_text(value, default: str = "") -> str:
    if value is None:
        return default

    if not isinstance(value, str):
        value = str(value)

    value = value.replace("\n", " ").replace("\r", " ")
    value = re.sub(r"\s+", " ", value).strip()

    return value or default


def clean_url(value: str) -> str:
    value = clean_text(value)

    value = value.strip()
    markdown_match = re.search(r"\]\((https?://[^)\s]+)\)", value)
    if markdown_match:
        value = markdown_match.group(1)
    else:
        value = value.split("](", 1)[0]

    value = value.strip("[](){}<>")
    value = value.strip('"').strip("'")

    value = value.replace('"https"://', "https://")
    value = value.replace('"http"://', "http://")
    value = value.replace("https\"://", "https://")
    value = value.replace("http\"://", "http://")

    if value.startswith("www."):
        value = "https://" + value

    url_match = re.search(r"https?://[^\s\])}<>]+", value)
    if url_match:
        value = url_match.group(0)

    if not value.startswith(("http://", "https://")):
        value = "https://example.com"

    return value


def normalize_sources(sources) -> list:
    if isinstance(sources, dict):
        sources = [sources]

    if not isinstance(sources, list):
        sources = []

    normalized = []

    for source in sources:
        if not isinstance(source, dict):
            continue

        normalized.append(
            {
                "name": clean_text(source.get("name"), "Kaynak"),
                "url": clean_url(source.get("url", "https://example.com")),
                "published_at": clean_text(source.get("published_at"), ""),
            }
        )

    if not normalized:
        normalized.append(
            {
                "name": "Kaynak",
                "url": "https://example.com",
                "published_at": "",
            }
        )

    return normalized


def clean_verification_note(value, status: str) -> str:
    value = clean_text(value)

    corrupted_markers = [
        "http://",
        "https://",
        "[",
        "]",
        "%22",
        "%7B",
        "%7D",
        '"url"',
        '"name"',
        "published_at",
        "sources",
    ]

    if any(marker in value for marker in corrupted_markers) or len(value) > 300:
        if status == "confirmed":
            return "Haber kaynaklarla doğrulandı."
        if status == "developing":
            return "Süreç devam ettiği için gelişen haber olarak işaretlendi."
        if status == "rumor":
            return "Resmi doğrulama bulunmadığı için söylenti olarak işaretlendi."
        if status == "analysis":
            return "Kaynaklara dayalı analiz olarak işaretlendi."
        return "Kaynaklar kontrol edildi."

    return value or "Kaynaklar kontrol edildi."


def normalize_story(story, path: str, category_hint: str) -> dict:
    if not isinstance(story, dict):
        story = {}

    title = clean_text(story.get("title"), "Başlık")
    status = clean_text(story.get("status"), "confirmed")

    if status not in VALID_STATUSES:
        status = "confirmed"

    category = clean_text(story.get("category"), category_hint)

    if category not in VALID_CATEGORIES:
        category = category_hint

    sources = normalize_sources(story.get("sources", []))

    try:
        importance = int(story.get("importance", 3))
    except (TypeError, ValueError):
        importance = 3

    importance = max(1, min(5, importance))

    normalized = {
        "id": clean_text(story.get("id"), slugify(title, path)),
        "title": title,
        "subtitle": clean_text(story.get("subtitle"), ""),
        "summary": clean_text(story.get("summary"), ""),
        "body": clean_text(story.get("body"), ""),
        "category": category,
        "importance": importance,
        "status": status,
        "source_count": len(sources),
        "sources": sources,
        "verification_note": clean_verification_note(
            story.get("verification_note", ""),
            status=status,
        ),
        "image_prompt": clean_text(story.get("image_prompt"), ""),
    }

    return normalized


def normalize_page(page: dict, expected_page_number: int) -> dict:
    if not isinstance(page, dict):
        page = {}

    section = clean_text(page.get("section"), "front_page")

    if section not in VALID_CATEGORIES:
        section = "front_page" if expected_page_number == 1 else "politics"

    category_hint = SECTION_TO_CATEGORY.get(section, section)

    page["page_number"] = expected_page_number
    page["section"] = section
    page["template"] = clean_text(page.get("template"), "page.html")
    page["css"] = clean_text(page.get("css"), "style.css")

    if expected_page_number == 1:
        page["headline"] = normalize_story(
            page.get("headline", {}),
            "page-1-headline",
            category_hint,
        )

        lead_stories = page.get("lead_stories", [])
        briefs = page.get("briefs", [])

        if not isinstance(lead_stories, list):
            lead_stories = []

        if not isinstance(briefs, list):
            briefs = []

        page["lead_stories"] = [
            normalize_story(story, f"page-1-lead-{index}", category_hint)
            for index, story in enumerate(lead_stories, start=1)
        ]

        page["briefs"] = [
            normalize_story(story, f"page-1-brief-{index}", category_hint)
            for index, story in enumerate(briefs, start=1)
        ]

    else:
        page["main_story"] = normalize_story(
            page.get("main_story", {}),
            f"page-{expected_page_number}-main",
            category_hint,
        )

        stories = page.get("stories", [])

        if not isinstance(stories, list):
            stories = []

        page["stories"] = [
            normalize_story(
                story,
                f"page-{expected_page_number}-story-{index}",
                category_hint,
            )
            for index, story in enumerate(stories, start=1)
        ]

    return page


def load_issue() -> dict:
    if not ISSUE_PATH.exists():
        fail(f"issue.json bulunamadı: {ISSUE_PATH}")

    try:
        return json.loads(ISSUE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"issue.json geçersiz JSON: {error}")


def save_issue(issue_data: dict) -> None:
    ISSUE_PATH.write_text(
        json.dumps(issue_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    issue_data = load_issue()
    try:
        from chatgpt_haber.issue import normalize_issue

        issue_data = normalize_issue(issue_data)
    except Exception as error:
        fail(f"issue.json otomatik tamir edilemedi: {error}")

    save_issue(issue_data)

    print("OK: issue.json 3 sayfalık sözleşmeye normalize edildi.")
    print(f"OK: Dosya: {ISSUE_PATH}")


if __name__ == "__main__":
    main()
