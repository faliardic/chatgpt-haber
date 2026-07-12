from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any
from datetime import datetime, timedelta, timezone

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .issue import BASE_DIR, slugify
from services.news_quality_filters import (
    assert_no_forbidden_rendered_text,
    is_absolute_blocked_content,
    sanitize_items_or_fail,
)


TEMPLATE_DIR = BASE_DIR / "templates"
TR_TIMEZONE = timezone(timedelta(hours=3))


def image_src(path_value: str) -> str:
    return asset_src(path_value, embed=False)


def asset_src(path_value: str, embed: bool = False) -> str:
    if not path_value:
        return ""
    if path_value.startswith(("http://", "https://", "data:")):
        return path_value

    if path_value.startswith("file://"):
        path = Path(path_value.removeprefix("file:///"))
    else:
        path = Path(path_value)
    if embed:
        data_uri = file_data_uri(path)
        if data_uri:
            return data_uri
    if path_value.startswith("file://"):
        return path_value
    if path.exists():
        return path.resolve().as_uri()
    return path_value


def file_data_uri(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def css_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def linked_or_embedded_asset(path: Path, portable_assets: bool) -> str:
    if portable_assets:
        return file_data_uri(path)
    return path.resolve().as_uri()


def linked_or_embedded_css(path: Path, portable_assets: bool) -> str:
    if portable_assets:
        return css_text(path)
    return ""


def css_href(path: Path, portable_assets: bool) -> str:
    if portable_assets:
        return ""
    return path.resolve().as_uri()


def image_src_filter(portable_assets: bool):
    def _image_src(path_value: str) -> str:
        return asset_src(path_value, embed=portable_assets)

    return _image_src


def render_html(
    issue_data: dict[str, Any],
    html_path: Path,
    portable_pdf_links: bool = False,
    portable_assets: bool = False,
    include_brief_details: bool = True,
) -> None:
    sanitize_render_issue(issue_data)
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["image_src"] = image_src_filter(portable_assets)
    env.filters["datetime_tr"] = datetime_tr
    detail_articles = sanitize_items_or_fail(
        prepare_detail_links(
            issue_data,
            html_path,
            portable_pdf_links=portable_pdf_links,
            include_briefs=include_brief_details,
        ),
        "detail_pages_before_render",
    )
    template = env.get_template("base.html")
    print_css = BASE_DIR / "static" / "css" / "print.css"
    detail_css = BASE_DIR / "static" / "css" / "article_detail.css"
    logo_path = BASE_DIR / "static" / "img" / "chatgpt-haber-logo-cropped.png"
    rendered_html = template.render(
        issue=issue_data["issue"],
        pages=issue_data["pages"],
        pdf_detail_articles=detail_articles if portable_pdf_links else [],
        css_href=css_href(print_css, portable_assets),
        css_content=linked_or_embedded_css(print_css, portable_assets),
        logo_href=linked_or_embedded_asset(logo_path, portable_assets),
    )
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(rendered_html, encoding="utf-8")
    assert_no_forbidden_rendered_text(rendered_html, "final_html_before_pdf")

    detail_template = env.get_template("article_detail.html")
    for article in detail_articles:
        if is_absolute_blocked_content(article):
            raise RuntimeError("[GAZETTE BLOCKER FAILED] Forbidden earthquake SEO article reached detail renderer")
        detail_path = Path(str(article.get("detail_path") or ""))
        if not detail_path:
            continue
        detail_path.parent.mkdir(parents=True, exist_ok=True)
        rendered_detail = detail_template.render(
            issue=issue_data["issue"],
            article=article,
            source_name=source_name(article),
            source_url=source_url(article),
            back_href=f"../{html_path.name}",
            css_href=css_href(detail_css, portable_assets),
            css_content=linked_or_embedded_css(detail_css, portable_assets),
            logo_href=linked_or_embedded_asset(logo_path, portable_assets),
        )
        detail_path.write_text(rendered_detail, encoding="utf-8")
        assert_no_forbidden_rendered_text(rendered_detail, "detail_html_before_pdf")


def datetime_tr(value: str) -> str:
    if not value:
        dt = datetime.now(TR_TIMEZONE)
    else:
        normalized = str(value).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            return str(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TR_TIMEZONE)
        else:
            dt = dt.astimezone(TR_TIMEZONE)
    return dt.strftime("%d.%m.%Y %H:%M")


def source_url(article: dict[str, Any]) -> str:
    sources = article.get("source_bundle") if isinstance(article.get("source_bundle"), list) else []
    source = sources[0] if sources and isinstance(sources[0], dict) else {}
    return str(source.get("url") or "#")


def source_name(article: dict[str, Any]) -> str:
    sources = article.get("source_bundle") if isinstance(article.get("source_bundle"), list) else []
    source = sources[0] if sources and isinstance(sources[0], dict) else {}
    return str(source.get("name") or "Kaynak")


def prepare_detail_links(
    issue_data: dict[str, Any],
    html_path: Path,
    portable_pdf_links: bool = False,
    include_briefs: bool = True,
) -> list[dict[str, Any]]:
    articles_dir = html_path.parent / "articles"
    used_slugs: set[str] = set()
    detail_articles: list[dict[str, Any]] = []
    links_by_key: dict[str, tuple[str, str, str]] = {}
    for page in issue_data.get("pages", []):
        if not isinstance(page, dict):
            continue
        collection_names = ("articles", "briefs") if include_briefs else ("articles",)
        for collection_name in collection_names:
            collection = page.get(collection_name, [])
            if not isinstance(collection, list):
                continue
            for article in collection:
                if not isinstance(article, dict):
                    continue
                key = str(article.get("id") or source_url(article) or article.get("headline") or "")
                if key in links_by_key:
                    detail_path, detail_url, detail_anchor = links_by_key[key]
                    article["detail_path"] = detail_path
                    article["detail_url"] = detail_url
                    article["detail_anchor"] = detail_anchor
                    if portable_pdf_links:
                        article["pdf_detail_url"] = f"#{detail_anchor}"
                    continue

                base_slug = slugify(str(article.get("id") or article.get("headline") or "haber"), "haber")
                slug = unique_detail_slug(base_slug, used_slugs)
                detail_path = str(articles_dir / f"{slug}.html")
                detail_url = f"articles/{slug}.html"
                detail_anchor = f"article-detail-{slug}"
                links_by_key[key] = (detail_path, detail_url, detail_anchor)
                article["detail_path"] = detail_path
                article["detail_url"] = detail_url
                article["detail_anchor"] = detail_anchor
                if portable_pdf_links:
                    article["pdf_detail_url"] = f"#{detail_anchor}"
                detail_articles.append(article)
    return detail_articles


def unique_detail_slug(base_slug: str, used_slugs: set[str]) -> str:
    slug = base_slug
    suffix = 2
    while slug in used_slugs:
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    used_slugs.add(slug)
    return slug


def sanitize_render_issue(issue_data: dict[str, Any]) -> None:
    for page in issue_data.get("pages", []):
        if not isinstance(page, dict):
            continue
        for collection_name in ("articles", "briefs"):
            collection = page.get(collection_name, [])
            if isinstance(collection, list):
                page[collection_name] = sanitize_items_or_fail(
                    [article for article in collection if isinstance(article, dict)],
                    f"{collection_name}_before_render_page_{page.get('page_no', '?')}",
                )
        articles = page.get("articles", [])
        if isinstance(articles, list) and articles and is_absolute_blocked_content(articles[0]):
            raise RuntimeError("[GAZETTE BLOCKER FAILED] Forbidden earthquake SEO article selected as top story")


def extract_pdf_text(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            import fitz
        except ImportError:
            print("[GAZETTE FINAL VALIDATION] PDF text extractor not installed; skipped")
            return ""
        doc = fitz.open(str(pdf_path))
        return "\n".join(page.get_text("text") for page in doc)
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def render_pdf(html_path: Path, pdf_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    print(f"[GAZETTE RENDER] html_path = {html_path}")
    print(f"[GAZETTE RENDER] pdf_path = {pdf_path}")
    html_text = html_path.read_text(encoding="utf-8", errors="ignore")
    assert_no_forbidden_rendered_text(html_text, "final_html_before_pdf")
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
    pdf_text = extract_pdf_text(pdf_path)
    if pdf_text:
        try:
            assert_no_forbidden_rendered_text(pdf_text, "final_pdf_after_render")
        except RuntimeError:
            pdf_path.unlink(missing_ok=True)
            raise
