from bs4 import BeautifulSoup
from copy import deepcopy
from pathlib import Path

from chatgpt_haber.issue import normalize_issue, read_json
from chatgpt_haber.render import image_src, render_html
from chatgpt_haber.sources import issue_from_rss


def test_single_html_document(tmp_path):
    html_path = tmp_path / "issue.html"
    render_html(normalize_issue(read_json(Path("examples/issue.sample.json"))), html_path)
    html = html_path.read_text(encoding="utf-8")
    assert html.lower().count("<!doctype html>") == 1
    assert html.lower().count("<html") == 1
    assert html.lower().count("<body") == 1


def test_three_pages_present(tmp_path):
    html_path = tmp_path / "issue.html"
    render_html(normalize_issue(read_json(Path("examples/issue.sample.json"))), html_path)
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")
    pages = soup.select(".page[data-page-no]")
    assert len(pages) == 3


def test_local_image_paths_render_as_file_uri(tmp_path):
    image_path = tmp_path / "photo.jpg"
    image_path.write_bytes(b"fake image")

    assert image_src(str(image_path)).startswith("file:///")


def test_article_headlines_link_to_sources(tmp_path):
    html_path = tmp_path / "issue.html"
    render_html(normalize_issue(read_json(Path("examples/issue.sample.json"))), html_path)
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")

    headline_links = soup.select(".story__headline a[href]")
    assert headline_links
    assert all(link["href"].startswith("https://") for link in headline_links)


def test_front_page_rail_lists_twenty_text_only_items(tmp_path):
    issue = normalize_issue(read_json(Path("examples/issue.sample.json")))
    front = issue["pages"][0]
    source_article = deepcopy(front["articles"][0])
    front["briefs"] = []
    for index in range(20):
        article = deepcopy(source_article)
        article["id"] = f"rail-{index}"
        article["headline"] = f"Kısa haber {index + 1}"
        article["image"] = {"path": "should-not-render.jpg"}
        article["layout_hint"] = {"story_size": "brief", "column_span": 1, "preferred_position": "rail"}
        front["briefs"].append(article)

    html_path = tmp_path / "issue.html"
    render_html(issue, html_path)
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")

    rail_items = soup.select(".page[data-page-no='1'] .front-rail__item")
    assert len(rail_items) == 20
    assert [item.select_one(".front-rail__number").get_text(strip=True) for item in rail_items[:3]] == ["01", "02", "03"]
    assert not soup.select(".page[data-page-no='1'] .front-rail img")


def test_rail_numbering_continues_across_pages(tmp_path):
    issue = normalize_issue(read_json(Path("examples/issue.sample.json")))
    source_article = deepcopy(issue["pages"][0]["articles"][0])
    for page in issue["pages"]:
        page["briefs"] = []
        for index in range(20):
            article = deepcopy(source_article)
            article["id"] = f"page-{page['page_no']}-rail-{index}"
            article["headline"] = f"Kısa haber {index + 1}"
            article["layout_hint"] = {"story_size": "brief", "column_span": 1, "preferred_position": "rail"}
            page["briefs"].append(article)

    html_path = tmp_path / "issue.html"
    render_html(issue, html_path)
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")

    assert soup.select_one(".page[data-page-no='1'] .front-rail__number").get_text(strip=True) == "01"
    assert soup.select_one(".page[data-page-no='2'] .front-rail__number").get_text(strip=True) == "21"
    assert soup.select_one(".page[data-page-no='3'] .front-rail__number").get_text(strip=True) == "41"


def test_live_issue_front_page_has_twelve_main_blocks_and_twenty_rail_items(monkeypatch):
    articles = []
    for index in range(96):
        articles.append(
            {
                "id": f"story-{index}",
                "section": "gundem",
                "headline": f"Haber {index + 1}",
                "importance": index + 1,
                "dek": "Kısa özet",
                "body": ["Kısa haber metni."],
                "source_bundle": [
                    {
                        "name": "Kaynak",
                        "url": "https://example.com",
                        "published_at": "2026-05-26",
                        "source_type": "rss",
                        "is_primary": False,
                    }
                ],
                "verification": {
                    "status": "single_source",
                    "checked_at": "2026-05-26",
                    "method": ["primary_source"],
                    "note": "Test",
                },
                "layout_hint": {"story_size": "secondary", "column_span": 1, "preferred_position": "mid"},
                "image": {},
            }
        )

    monkeypatch.setattr("chatgpt_haber.sources.fetch_rss_articles", lambda: articles)
    monkeypatch.setattr("chatgpt_haber.sources.fetch_ankara_local_articles", lambda: articles)

    issue = issue_from_rss("2026-05-26", "A3")

    assert issue["issue"]["page_count"] == 3
    assert issue["pages"][2]["name"] == "Ankara Özel Bülteni"
    for page in issue["pages"]:
        assert len(page["articles"]) == 12
        assert len(page["briefs"]) == 20
        assert all(article["layout_hint"]["story_size"] == "brief" for article in page["briefs"])


def test_all_pages_use_shared_grid_layout(tmp_path):
    html_path = tmp_path / "issue.html"
    render_html(normalize_issue(read_json(Path("examples/issue.sample.json"))), html_path)
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")

    assert len(soup.select(".page .front-layout")) == 3
