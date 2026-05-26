from __future__ import annotations

import base64
from copy import deepcopy
from mimetypes import guess_type
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape


BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = BASE_DIR / "templates"
PRINT_CSS = BASE_DIR / "static" / "css" / "print.css"
MAX_EMBED_IMAGE_BYTES = 1_500_000


def _windows_drive_path(path: str) -> str | None:
    if len(path) >= 4 and path[0] == "/" and path[2] == ":":
        return path[1:]
    return None


def _path_from_image_value(value: str, html_dir: Path) -> Path | None:
    raw = str(value or "").strip()
    if not raw or raw.startswith(("http://", "https://", "data:")):
        return None

    normalized = raw.replace("\\", "/")
    if normalized.startswith("file:"):
        parsed = urlparse(normalized)
        normalized = unquote(parsed.path)
        if re_drive := _windows_drive_path(normalized):
            normalized = re_drive

    candidates: list[Path] = []
    path = Path(normalized)
    if path.is_absolute():
        candidates.append(path)
    else:
        candidates.extend([html_dir / normalized, BASE_DIR / normalized, BASE_DIR / "dist" / normalized])

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def _data_uri_from_bytes(data: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _local_image_data_uri(image_path: Path) -> str:
    mime_type = guess_type(image_path.name)[0] or "application/octet-stream"
    return _data_uri_from_bytes(image_path.read_bytes(), mime_type)


def _remote_image_data_uri(url: str) -> str:
    import requests

    response = requests.get(
        url,
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0 ChatGPT-Haber/1.0"},
        stream=True,
    )
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if not content_type.startswith("image/"):
        content_type = guess_type(urlparse(url).path)[0] or "image/jpeg"

    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=65536):
        if not chunk:
            continue
        total += len(chunk)
        if total > MAX_EMBED_IMAGE_BYTES:
            raise ValueError(f"image too large to embed: {url}")
        chunks.append(chunk)
    return _data_uri_from_bytes(b"".join(chunks), content_type)


def _embed_images(issue_data: dict[str, Any], html_path: Path) -> dict[str, Any]:
    standalone = deepcopy(issue_data)
    html_dir = html_path.parent
    cache: dict[str, str] = {}

    for page in standalone.get("pages", []):
        for group_name in ("articles", "briefs"):
            for article in page.get(group_name, []) or []:
                image = article.get("image")
                if not isinstance(image, dict) or not image.get("path"):
                    continue
                raw = str(image["path"]).strip()
                if raw.startswith("data:"):
                    continue
                if raw in cache:
                    image["path"] = cache[raw]
                    continue

                data_uri = ""
                try:
                    if raw.startswith(("http://", "https://")):
                        data_uri = _remote_image_data_uri(raw)
                    else:
                        image_path = _path_from_image_value(raw, html_dir)
                        if image_path is not None:
                            data_uri = _local_image_data_uri(image_path)
                except Exception:
                    data_uri = ""

                if data_uri:
                    cache[raw] = data_uri
                    image["path"] = data_uri
                else:
                    image["path"] = ""
    return standalone


def render_html(issue_data: dict[str, Any], html_path: Path) -> None:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("base.html")
    html_path.parent.mkdir(parents=True, exist_ok=True)

    standalone_issue_data = _embed_images(issue_data, html_path)
    css_text = PRINT_CSS.read_text(encoding="utf-8")
    rendered_html = template.render(
        issue=standalone_issue_data["issue"],
        pages=standalone_issue_data["pages"],
        css_href=None,
        inline_css=css_text,
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
