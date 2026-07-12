from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from bs4 import BeautifulSoup

from chatgpt_haber.builder import issue_from_rss
from chatgpt_haber.issue import normalize_issue, read_json
from chatgpt_haber.render import render_html
from chatgpt_haber.technology_page import ensure_technology_third_page


def sample_article(index: int, section: str = "gundem") -> dict:
    topic = f"ozelkonu{index}"
    return {
        "id": f"story-{section}-{index}",
        "section": section,
        "kicker": section.upper(),
        "headline": f"{topic} manset",
        "importance": index,
        "dek": f"ayrinti{index} gelisme{index}",
        "body": [f"{topic} ayrinti{index} gelisme{index}"],
        "source_bundle": [
            {
                "name": "Test Kaynağı",
                "url": f"https://example.com/{section}/{index}",
                "published_at": "2026-07-12T09:00:00+03:00",
                "source_type": "rss",
                "is_primary": False,
            }
        ],
        "verification": {
            "status": "single_source",
            "checked_at": "2026-07-12T09:05:00+03:00",
            "method": ["primary_source"],
            "note": "Test verisi.",
        },
        "layout_hint": {"story_size": "secondary", "column_span": 1, "preferred_position": "mid"},
        "image": {},
    }


def normalized_sample_issue() -> tuple[dict, dict]:
    raw_issue = read_json(Path("examples/issue.sample.json"))
    issue = normalize_issue(deepcopy(raw_issue))
    ensure_technology_third_page(issue, raw_issue=raw_issue)
    return issue, raw_issue


def test_live_issue_uses_technology_as_complete_third_page(monkeypatch):
    general_articles = [sample_article(index, "gundem") for index in range(1, 97)]
    technology_articles = [sample_article(index, "teknoloji") for index in range(1, 41)]

    monkeypatch.setattr("chatgpt_haber.builder.fetch_rss_articles", lambda: general_articles)
    monkeypatch.setattr("chatgpt_haber.builder.fetch_technology_articles", lambda: technology_articles)

    issue = issue_from_rss("2026-07-12", "A3")

    assert issue is not None
    third_page = issue["pages"][2]
    assert third_page["page_no"] == 3
    assert third_page["name"] == "Teknoloji"
    assert len(third_page["articles"]) == 12
    assert len(third_page["briefs"]) == 20
    assert all(article["section"] == "teknoloji" for article in third_page["articles"] + third_page["briefs"])
    assert all(article["kicker"] == "TEKNOLOJİ" for article in third_page["articles"] + third_page["briefs"])
    assert not any("ankara" in article["section"].lower() for article in third_page["articles"] + third_page["briefs"])


def test_offline_issue_replaces_third_page_with_technology():
    issue, _ = normalized_sample_issue()

    assert issue["pages"][2]["name"] == "Teknoloji"
    assert all(article["section"] == "teknoloji" for article in issue["pages"][2]["articles"])
    assert all(article["section"] == "teknoloji" for article in issue["pages"][2]["briefs"])


def test_masthead_and_right_rail_do_not_show_source_labels(tmp_path):
    issue, _ = normalized_sample_issue()
    source_article = deepcopy(issue["pages"][0]["articles"][0])
    source_article["id"] = "rail-source-check"
    source_article["headline"] = "Sağ şerit kaynak kontrolü"
    source_article["layout_hint"] = {"story_size": "brief", "column_span": 1, "preferred_position": "rail"}
    issue["pages"][0]["briefs"] = [source_article]

    html_path = tmp_path / "issue.html"
    render_html(issue, html_path, portable_pdf_links=True)
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")

    assert not soup.select(".masthead__note")
    assert not soup.select(".front-rail__source")
    assert soup.select_one(".front-rail__item a").get_text(strip=True) == "Sağ şerit kaynak kontrolü"


def test_pdf_detail_pages_have_large_return_button_above_and_below_article(tmp_path):
    issue, _ = normalized_sample_issue()
    html_path = tmp_path / "issue.html"

    render_html(issue, html_path, portable_pdf_links=True)
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")
    detail_page = soup.select_one(".detail-page")

    assert detail_page is not None
    buttons = detail_page.select(".detail-page__back")
    assert len(buttons) == 2
    assert all(button.get_text(" ", strip=True) == "GAZETEYE DÖNÜŞ" for button in buttons)
    assert all(button["href"] == "#top" for button in buttons)
    assert detail_page.select_one(".detail-page__actions > .detail-page__back") is not None
    assert detail_page.select_one(".detail-page__actions > .detail-page__open-source") is not None
    assert detail_page.select("a.detail-page__back")[-1].parent == detail_page


def test_linked_article_detail_has_large_return_button_above_and_below_article(tmp_path):
    issue, _ = normalized_sample_issue()
    html_path = tmp_path / "issue.html"

    render_html(issue, html_path)
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")
    detail_path = tmp_path / soup.select_one(".story__headline a[href]")["href"]
    detail_soup = BeautifulSoup(detail_path.read_text(encoding="utf-8"), "lxml")

    buttons = detail_soup.select(".detail-return")
    assert len(buttons) == 2
    assert all(button.get_text(" ", strip=True) == "GAZETEYE DÖNÜŞ" for button in buttons)
    assert all(button["href"] == "../issue.html" for button in buttons)
