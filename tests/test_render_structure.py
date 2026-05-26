from bs4 import BeautifulSoup
from pathlib import Path

from chatgpt_haber.issue import read_json
from chatgpt_haber.render import render_html


def test_single_html_document(tmp_path):
    html_path = tmp_path / "issue.html"
    render_html(read_json(Path("examples/issue.sample.json")), html_path)
    html = html_path.read_text(encoding="utf-8")
    assert html.lower().count("<!doctype html>") == 1
    assert html.lower().count("<html") == 1
    assert html.lower().count("<body") == 1


def test_three_pages_present(tmp_path):
    html_path = tmp_path / "issue.html"
    render_html(read_json(Path("examples/issue.sample.json")), html_path)
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")
    pages = soup.select(".page[data-page-no]")
    assert len(pages) == 3
