from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime, timedelta, timezone

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .issue import slugify


BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = BASE_DIR / "templates"
TR_TIMEZONE = timezone(timedelta(hours=3))


def image_src(path_value: str) -> str:
    if not path_value:
        return ""
    if path_value.startswith(("http://", "https://", "file://", "data:")):
        return path_value

    path = Path(path_value)
    if path.exists():
        return path.resolve().as_uri()
    return path_value


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


def prepare_detail_links(issue_data: dict[str, Any], html_path: Path, portable_pdf_links: bool = False) -> list[dict[str, Any]]:
    articles_dir = html_path.parent / "articles"
    used_slugs: set[str] = set()
    detail_articles: list[dict[str, Any]] = []
    links_by_key: dict[str, tuple[str, str, str]] = {}
    for page in issue_data.get("pages", []):
        if not isinstance(page, dict):
            continue
        for collection_name in ("articles", "briefs"):
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


def render_html(issue_data: dict[str, Any], html_path: Path, portable_pdf_links: bool = False) -> None:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["image_src"] = image_src
    env.filters["datetime_tr"] = datetime_tr
    detail_articles = prepare_detail_links(issue_data, html_path, portable_pdf_links=portable_pdf_links)
    template = env.get_template("base.html")
    rendered_html = template.render(
        issue=issue_data["issue"],
        pages=issue_data["pages"],
        pdf_detail_articles=detail_articles if portable_pdf_links else [],
        css_href=(BASE_DIR / "static" / "css" / "print.css").resolve().as_uri(),
        logo_href=(BASE_DIR / "static" / "img" / "chatgpt-haber-logo-cropped.png").resolve().as_uri(),
    )
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(rendered_html, encoding="utf-8")

    detail_template = env.get_template("article_detail.html")
    for article in detail_articles:
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
            css_href=(BASE_DIR / "static" / "css" / "article_detail.css").resolve().as_uri(),
            logo_href=(BASE_DIR / "static" / "img" / "chatgpt-haber-logo-cropped.png").resolve().as_uri(),
        )
        detail_path.write_text(rendered_detail, encoding="utf-8")


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
