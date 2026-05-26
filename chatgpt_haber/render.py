from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import posixpath
import shutil
from typing import Any
from urllib.parse import unquote, urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape


BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = BASE_DIR / "templates"
PRINT_CSS = BASE_DIR / "static" / "css" / "print.css"


def _portable_asset_path(value: str, html_dir: Path) -> str:
    """Return a browser-portable relative path for images in rendered HTML.

    Playwright can render local absolute paths, but a saved HTML file opened on a
    phone cannot resolve paths such as file:///V:/.../dist/assets/image.jpg.
    The exported HTML should therefore reference assets relatively, e.g.
    assets/image.jpg, while the PDF renderer still opens the HTML from disk.
    """
    raw = str(value or "").strip()
    if not raw or raw.startswith(("http://", "https://", "data:")):
        return raw

    normalized = raw.replace("\\", "/")
    lower = normalized.lower()
    marker = "/dist/assets/"
    if marker in lower:
        idx = lower.index(marker) + len("/dist/")
        return normalized[idx:]
    if lower.startswith("assets/"):
        return normalized

    if normalized.startswith("file:"):
        parsed = urlparse(normalized)
        normalized = unquote(parsed.path).lstrip("/")

    try:
        path = Path(normalized)
        if path.is_absolute():
            return posixpath.relpath(path.resolve().as_posix(), html_dir.resolve().as_posix())
    except OSError:
        pass

    return normalized


def _make_html_portable(issue_data: dict[str, Any], html_path: Path) -> dict[str, Any]:
    portable = deepcopy(issue_data)
    html_dir = html_path.parent
    for page in portable.get("pages", []):
        for group_name in ("articles", "briefs"):
            for article in page.get(group_name, []) or []:
                image = article.get("image")
                if isinstance(image, dict) and image.get("path"):
                    image["path"] = _portable_asset_path(str(image["path"]), html_dir)
    return portable


def render_html(issue_data: dict[str, Any], html_path: Path) -> None:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("base.html")
    html_path.parent.mkdir(parents=True, exist_ok=True)

    css_target = html_path.parent / "print.css"
    shutil.copyfile(PRINT_CSS, css_target)

    portable_issue_data = _make_html_portable(issue_data, html_path)
    rendered_html = template.render(
        issue=portable_issue_data["issue"],
        pages=portable_issue_data["pages"],
        css_href="print.css",
    )
    html_path.write_text(rendered_html, encoding="utf-8")


def render_pdf(html_path: Path, pdf_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.pdf(
            path=str(pdf_path),
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()
