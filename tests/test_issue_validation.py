import json
from pathlib import Path

from chatgpt_haber.issue import validate_issue_data


def load_issue() -> dict:
    return json.loads(Path("examples/issue.sample.json").read_text(encoding="utf-8"))


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
