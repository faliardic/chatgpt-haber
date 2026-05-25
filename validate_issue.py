from pathlib import Path
import json
import sys


BASE_DIR = Path(__file__).resolve().parent
ISSUE_PATH = BASE_DIR / "data" / "issue.json"


REQUIRED_ROOT_FIELDS = [
    "issue",
    "editorial_policy",
    "pages",
]


REQUIRED_ISSUE_FIELDS = [
    "newspaper_name",
    "date",
    "day",
    "issue_number",
    "language",
    "page_count",
]


REQUIRED_PAGE_FIELDS = [
    "page_number",
    "section",
    "template",
    "css",
]


REQUIRED_STORY_FIELDS = [
    "id",
    "title",
    "subtitle",
    "summary",
    "body",
    "category",
    "importance",
    "status",
    "source_count",
    "sources",
    "verification_note",
    "image_prompt",
]


VALID_STATUSES = {
    "confirmed",
    "developing",
    "rumor",
    "analysis",
}


VALID_SECTIONS = {
    "front_page",
    "politics",
    "economy",
    "technology_science",
    "culture_arts",
    "lifestyle",
    "sports",
    "transfer_file",
}


def fail(message: str) -> None:
    print(f"VALIDATION ERROR: {message}")
    sys.exit(1)


def success(message: str) -> None:
    print(f"OK: {message}")


def load_issue() -> dict:
    if not ISSUE_PATH.exists():
        fail(f"issue.json bulunamadı: {ISSUE_PATH}")

    try:
        return json.loads(ISSUE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"Geçersiz JSON: {error}")


def require_dict(value, path: str) -> None:
    if not isinstance(value, dict):
        fail(f"{path} object/dict olmalı.")


def require_list(value, path: str) -> None:
    if not isinstance(value, list):
        fail(f"{path} liste/array olmalı.")


def require_fields(obj: dict, fields: list[str], path: str) -> None:
    for field in fields:
        if field not in obj:
            fail(f"{path}.{field} alanı eksik.")


def validate_root(issue_data: dict) -> None:
    require_dict(issue_data, "root")
    require_fields(issue_data, REQUIRED_ROOT_FIELDS, "root")

    require_dict(issue_data["issue"], "issue")
    require_dict(issue_data["editorial_policy"], "editorial_policy")
    require_list(issue_data["pages"], "pages")


def validate_issue_metadata(issue_data: dict) -> None:
    meta = issue_data["issue"]

    require_fields(meta, REQUIRED_ISSUE_FIELDS, "issue")

    if meta["newspaper_name"] != "CHATGPT HABER":
        fail("issue.newspaper_name değeri 'CHATGPT HABER' olmalı.")

    if meta["language"] != "tr":
        fail("issue.language değeri 'tr' olmalı.")

    if meta["page_count"] != 16:
        fail("issue.page_count değeri 16 olmalı.")


def validate_pages_count(issue_data: dict) -> None:
    pages = issue_data["pages"]

    if len(pages) != 16:
        fail(f"Sayfa sayısı 16 olmalı. Mevcut: {len(pages)}")


def validate_page_common_fields(page: dict, expected_page_number: int) -> None:
    require_dict(page, f"pages[{expected_page_number}]")
    require_fields(page, REQUIRED_PAGE_FIELDS, f"pages[{expected_page_number}]")

    if page["page_number"] != expected_page_number:
        fail(
            f"Sayfa numarası hatalı. Beklenen: {expected_page_number}, "
            f"Mevcut: {page['page_number']}"
        )

    if page["section"] not in VALID_SECTIONS:
        fail(
            f"Sayfa {expected_page_number}: Geçersiz section değeri: "
            f"{page['section']}"
        )

    if not isinstance(page["template"], str) or not page["template"].endswith(".html"):
        fail(f"Sayfa {expected_page_number}: template .html dosyası olmalı.")

    if not isinstance(page["css"], str) or not page["css"].endswith(".css"):
        fail(f"Sayfa {expected_page_number}: css .css dosyası olmalı.")


def validate_source(source: dict, path: str) -> None:
    require_dict(source, path)

    required_fields = [
        "name",
        "url",
        "published_at",
    ]

    require_fields(source, required_fields, path)

    if not isinstance(source["name"], str) or not source["name"].strip():
        fail(f"{path}.name boş olamaz.")

    if not isinstance(source["url"], str) or not source["url"].strip():
        fail(f"{path}.url boş olamaz.")

    if source["url"].startswith("[") or source["url"].endswith("]"):
        fail(f"{path}.url köşeli parantez içeremez: {source['url']}")

    if "](http" in source["url"] or "[" in source["url"] or "]" in source["url"]:
        fail(f"{path}.url markdown/köşeli parantez içeremez: {source['url']}")

    if not (
        source["url"].startswith("http://")
        or source["url"].startswith("https://")
    ):
        fail(f"{path}.url http:// veya https:// ile başlamalı: {source['url']}")

    if not isinstance(source["published_at"], str):
        fail(f"{path}.published_at string olmalı.")


def validate_story(story: dict, path: str) -> None:
    require_dict(story, path)
    require_fields(story, REQUIRED_STORY_FIELDS, path)

    for field in [
        "id",
        "title",
        "subtitle",
        "summary",
        "body",
        "category",
        "status",
        "verification_note",
        "image_prompt",
    ]:
        if not isinstance(story[field], str):
            fail(f"{path}.{field} string olmalı.")

    if not story["id"].strip():
        fail(f"{path}.id boş olamaz.")

    if not story["title"].strip():
        fail(f"{path}.title boş olamaz.")

    if story["status"] not in VALID_STATUSES:
        fail(f"{path}.status geçersiz: {story['status']}")

    if story["category"] not in VALID_SECTIONS:
        fail(f"{path}.category geçersiz: {story['category']}")

    if not isinstance(story["importance"], int):
        fail(f"{path}.importance integer olmalı.")

    if not 1 <= story["importance"] <= 5:
        fail(f"{path}.importance 1 ile 5 arasında olmalı.")

    if not isinstance(story["source_count"], int):
        fail(f"{path}.source_count integer olmalı.")

    require_list(story["sources"], f"{path}.sources")

    if len(story["sources"]) == 0:
        fail(f"{path}.sources boş olamaz.")

    if story["source_count"] != len(story["sources"]):
        fail(
            f"{path}.source_count ile sources uzunluğu uyuşmuyor. "
            f"source_count={story['source_count']}, "
            f"sources={len(story['sources'])}"
        )

    for index, source in enumerate(story["sources"], start=1):
        validate_source(source, f"{path}.sources[{index}]")

    if "[" in story["verification_note"] or "]" in story["verification_note"]:
        fail(f"{path}.verification_note köşeli parantez içeremez.")

    if "http://" in story["verification_note"] or "https://" in story["verification_note"]:
        fail(f"{path}.verification_note URL içermemeli.")

    if len(story["verification_note"]) > 300:
        fail(f"{path}.verification_note çok uzun. Maksimum 300 karakter önerilir.")


def validate_front_page(page: dict) -> None:
    required_fields = [
        "headline",
        "lead_stories",
        "briefs",
    ]

    require_fields(page, required_fields, "pages[1]")

    validate_story(page["headline"], "pages[1].headline")

    require_list(page["lead_stories"], "pages[1].lead_stories")
    require_list(page["briefs"], "pages[1].briefs")

    if len(page["lead_stories"]) < 1:
        fail("Ana sayfa lead_stories en az 1 haber içermeli.")

    if len(page["briefs"]) < 1:
        fail("Ana sayfa briefs en az 1 haber içermeli.")

    for index, story in enumerate(page["lead_stories"], start=1):
        validate_story(story, f"pages[1].lead_stories[{index}]")

    for index, story in enumerate(page["briefs"], start=1):
        validate_story(story, f"pages[1].briefs[{index}]")


def validate_inner_page(page: dict, page_number: int) -> None:
    required_fields = [
        "main_story",
        "stories",
    ]

    require_fields(page, required_fields, f"pages[{page_number}]")

    validate_story(page["main_story"], f"pages[{page_number}].main_story")

    require_list(page["stories"], f"pages[{page_number}].stories")

    if len(page["stories"]) < 1:
        fail(f"Sayfa {page_number}: stories en az 1 haber içermeli.")

    for index, story in enumerate(page["stories"], start=1):
        validate_story(story, f"pages[{page_number}].stories[{index}]")


def validate_pages(issue_data: dict) -> None:
    pages = issue_data["pages"]

    for expected_page_number, page in enumerate(pages, start=1):
        validate_page_common_fields(page, expected_page_number)

        if expected_page_number == 1:
            validate_front_page(page)
        else:
            validate_inner_page(page, expected_page_number)


def main() -> None:
    issue_data = load_issue()

    validate_root(issue_data)
    validate_issue_metadata(issue_data)
    validate_pages_count(issue_data)
    validate_pages(issue_data)

    success("issue.json temel ve içerik şema kontrolünden geçti.")
    success(f"Dosya: {ISSUE_PATH}")


if __name__ == "__main__":
    main()
