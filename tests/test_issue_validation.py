import json
from pathlib import Path

from chatgpt_haber.issue import normalize_issue, validate_issue_data
from chatgpt_haber.sources import enrich_issue_images


def load_issue() -> dict:
    return normalize_issue(json.loads(Path("examples/issue.sample.json").read_text(encoding="utf-8")))


def test_page_count_matches():
    issue = load_issue()
    validate_issue_data(issue)
    assert issue["issue"]["page_count"] == len(issue["pages"]) == 3


def test_image_paths_exist_when_set():
    issue = load_issue()
    for page in issue["pages"]:
        for article in page.get("articles", []):
            image = article.get("image", {})
            path = image.get("path")
            if path:
                assert Path(path).exists(), f"Missing image: {path}"


def test_enrich_issue_images_sets_downloaded_image(monkeypatch, tmp_path):
    issue = load_issue()
    image_file = tmp_path / "photo.jpg"
    image_file.write_bytes(b"fake image")

    def fake_page_image_url(url: str) -> str:
        return "https://example.test/photo.jpg"

    def fake_download_image(image_url: str, image_dir: Path, article_id: str) -> dict:
        return {"path": str(image_file), "source_url": image_url, "width": 640, "height": 360}

    monkeypatch.setattr("chatgpt_haber.sources.page_image_url", fake_page_image_url)
    monkeypatch.setattr("chatgpt_haber.sources.download_image", fake_download_image)

    enrich_issue_images(issue, tmp_path / "assets")

    image = issue["pages"][0]["articles"][0]["image"]
    assert image["path"] == str(image_file)
    assert image["source_url"] == "https://example.test/photo.jpg"
    assert image["width"] == 640
    assert image["height"] == 360


def test_enrich_issue_images_creates_fallback_when_source_image_missing(monkeypatch, tmp_path):
    issue = load_issue()

    monkeypatch.setattr("chatgpt_haber.sources.page_image_url", lambda url: "")
    monkeypatch.setattr("chatgpt_haber.sources.download_image", lambda image_url, image_dir, article_id: None)

    enrich_issue_images(issue, tmp_path / "assets")

    for page in issue["pages"]:
        for article in page["articles"]:
            image_path = Path(article["image"]["path"])
            assert image_path.exists()
            assert image_path.name.endswith("-fallback.jpg")
