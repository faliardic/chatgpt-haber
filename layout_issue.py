from pathlib import Path
import json


BASE_DIR = Path(__file__).resolve().parent
ISSUE_PATH = BASE_DIR / "data" / "issue.json"


SECTION_LABELS = {
    "front_page": "Ana Sayfa",
    "politics": "Siyaset",
    "economy": "Ekonomi",
    "technology_science": "Teknoloji",
    "culture_arts": "Kultur",
    "lifestyle": "Yasam",
    "sports": "Spor",
    "transfer_file": "Transfer",
}


def story_ref(story: dict, fallback: str) -> str:
    if not isinstance(story, dict):
        return fallback
    return story.get("id") or fallback


def front_page_blocks(issue_data: dict, page: dict) -> list[dict]:
    blocks = [
        {
            "role": "masthead",
            "size": "full",
            "data_type": "issue_meta",
        },
        {
            "role": "breaking_band",
            "size": "full",
            "text": page.get("headline", {}).get("subtitle", ""),
        },
        {
            "role": "main_headline",
            "size": "xl",
            "story_id": story_ref(page.get("headline"), "front-headline"),
            "image_required": True,
            "title_variant": "medium",
        },
    ]

    for index, story in enumerate(page.get("lead_stories", [])[:2], start=1):
        blocks.append(
            {
                "role": f"right_column_{index}",
                "size": "m",
                "story_id": story_ref(story, f"front-lead-{index}"),
                "image_required": True,
                "title_variant": "short",
            }
        )

    for index, story in enumerate(page.get("briefs", [])[:6], start=1):
        blocks.append(
            {
                "role": f"front_brief_{index}",
                "size": "s",
                "story_id": story_ref(story, f"front-brief-{index}"),
                "image_required": index <= 3,
                "title_variant": "short",
            }
        )

    for teaser_page in issue_data.get("pages", [])[1:]:
        blocks.append(
            {
                "role": f"page_teaser_{teaser_page.get('page_number')}",
                "size": "xs",
                "page_ref": teaser_page.get("page_number"),
                "section": teaser_page.get("section"),
                "section_label": SECTION_LABELS.get(
                    teaser_page.get("section"),
                    teaser_page.get("section", ""),
                ),
                "story_id": story_ref(
                    teaser_page.get("main_story"),
                    f"page-{teaser_page.get('page_number')}-main",
                ),
                "title_variant": "short",
            }
        )

    return blocks


def inner_page_blocks(page: dict) -> list[dict]:
    blocks = [
        {
            "role": "section_header",
            "size": "full",
            "section": page.get("section"),
            "section_label": SECTION_LABELS.get(
                page.get("section"),
                page.get("section", ""),
            ),
        },
        {
            "role": "main_file",
            "size": "xl",
            "story_id": story_ref(
                page.get("main_story"),
                f"page-{page.get('page_number')}-main",
            ),
            "image_required": True,
            "title_variant": "medium",
        },
        {
            "role": "analysis_column",
            "size": "m",
            "story_id": story_ref(
                (page.get("stories") or [{}])[0],
                f"page-{page.get('page_number')}-analysis",
            ),
            "title_variant": "short",
        },
    ]

    for index, story in enumerate((page.get("stories") or [])[1:5], start=1):
        blocks.append(
            {
                "role": f"supporting_story_{index}",
                "size": "s",
                "story_id": story_ref(story, f"page-{page.get('page_number')}-story-{index}"),
                "image_required": index <= 2,
                "title_variant": "short",
            }
        )

    blocks.append(
        {
            "role": "data_box",
            "size": "s",
            "data_type": page.get("section"),
        }
    )

    return blocks


def apply_layout(issue_data: dict) -> dict:
    pages = issue_data.get("pages", [])

    for page in pages:
        page_number = page.get("page_number")

        if page_number == 1 or page.get("section") == "front_page":
            page["layout"] = "front_dense_newspaper"
            page["template"] = "front_page.html"
            page["layout_blocks"] = front_page_blocks(issue_data, page)
            continue

        section = page.get("section", "general")
        page["layout"] = f"{section}_newspaper"
        page["layout_blocks"] = inner_page_blocks(page)

    return issue_data


def main() -> None:
    issue_data = json.loads(ISSUE_PATH.read_text(encoding="utf-8"))
    issue_data = apply_layout(issue_data)
    ISSUE_PATH.write_text(
        json.dumps(issue_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"OK: layout_blocks eklendi: {ISSUE_PATH}")


if __name__ == "__main__":
    main()
