from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = BASE_DIR / "templates"


def image_src(path_value: str) -> str:
    if not path_value:
        return ""
    if path_value.startswith(("http://", "https://", "file://", "data:")):
        return path_value

    path = Path(path_value)
    if path.exists():
        return path.resolve().as_uri()
    return path_value


def render_html(issue_data: dict[str, Any], html_path: Path) -> None:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["image_src"] = image_src
    template = env.get_template("base.html")
    rendered_html = template.render(
        issue=issue_data["issue"],
        pages=issue_data["pages"],
        css_href=(BASE_DIR / "static" / "css" / "print.css").resolve().as_uri(),
    )
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(rendered_html, encoding="utf-8")


def render_pdf(html_path: Path, pdf_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.wait_for_function("window.__chatgptHaberFitDone === true", timeout=5000)
        page.pdf(
            path=str(pdf_path),
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()
