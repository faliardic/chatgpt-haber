from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import sys
from typing import Optional

import typer

import services.news_quality_filters as nqf
from services.news_quality_filters import assert_no_forbidden_rendered_text
from services.gazette_reports import archive_outputs, write_reports
from services.random_news_service import appdata_news_cache_path, copy_gazette_outputs_to_desktop

from .issue import BASE_DIR, normalize_issue, read_json, validate_issue_data, write_json
from .render import render_html, render_pdf
from .sources import enrich_article_details, enrich_issue_images, sanitize_issue_articles
from .technology_page import ensure_technology_third_page, issue_from_rss


app = typer.Typer(help="Tek komutla 3 sayfalık baskıya hazır gazete üretir.")


def cleanup_forbidden_render_artifacts() -> None:
    scanned = 0
    removed = 0
    for root_name in ("dist", "output", "cache"):
        root = Path(root_name)
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".html", ".json", ".pdf"}:
                continue
            if path.suffix.lower() == ".pdf":
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                scanned += 1
                assert_no_forbidden_rendered_text(text, f"stale_output_scan:{path}", quiet=True)
            except RuntimeError:
                path.unlink(missing_ok=True)
                removed += 1
                print("[GAZETTE CLEANUP] removed forbidden stale output =", path)
    if scanned or removed:
        print(f"[GAZETTE CLEANUP] stale_output_scan scanned={scanned} removed={removed}")


def write_random_news_cache(issue_data: dict) -> Path:
    path = appdata_news_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, issue_data)
    return path


@app.callback()
def callback() -> None:
    """ChatGPT Haber komutları."""


@app.command()
def build(
    issue_date: str | None = typer.Option(None, "--date", help="Baskı tarihi, YYYY-MM-DD."),
    paper_size: str = typer.Option("A3", "--paper-size", help="A3 veya A4."),
    out: Path = typer.Option(Path("dist/gazete.pdf"), "--out", help="Üretilecek PDF yolu."),
    input_json: Optional[Path] = typer.Option(None, "--input-json", help="Var olan issue JSON dosyası."),
    live: bool = typer.Option(True, "--live/--no-live", help="Resmi RSS akışlarını dene; olmazsa yerel veriye düş."),
    portable_html: bool = typer.Option(True, "--portable-html/--linked-html", help="HTML'i tek başına paylaşılabilir üret."),
) -> None:
    if issue_date is None:
        issue_date = date.today().isoformat()

    paper_size = paper_size.upper()
    if paper_size not in {"A3", "A4"}:
        raise typer.BadParameter("paper-size A3 veya A4 olmalı.")

    dist_dir = out.parent
    image_dir = dist_dir / "assets"
    cleanup_forbidden_render_artifacts()
    print("[GAZETTE DEBUG] cwd =", os.getcwd())
    print("[GAZETTE DEBUG] main file =", __file__)
    print("[GAZETTE DEBUG] sys.path[0] =", sys.path[0])
    print("[GAZETTE DEBUG] news_quality_filters =", nqf.__file__)

    issue_data = issue_from_rss(issue_date, paper_size, image_dir=image_dir) if live else None
    if issue_data is None:
        source = input_json or BASE_DIR / "data" / "issue.json"
        raw_issue = read_json(source)
        issue_data = normalize_issue(raw_issue, issue_date=issue_date, paper_size=paper_size)
        ensure_technology_third_page(issue_data, raw_issue=raw_issue)
    sanitize_issue_articles(issue_data)
    enrich_article_details(issue_data)
    enrich_issue_images(issue_data, image_dir)

    validate_issue_data(issue_data)

    html_path = dist_dir / f"{out.stem}.html"
    json_path = dist_dir / "issue.json"

    write_json(json_path, issue_data)
    random_cache_path = write_random_news_cache(issue_data)
    report_paths = write_reports(issue_data, dist_dir)
    render_html(issue_data, html_path, portable_pdf_links=True, portable_assets=False)
    render_pdf(html_path, out)
    if portable_html:
        render_html(issue_data, html_path, portable_pdf_links=True, portable_assets=True)
    archive_path = archive_outputs(
        issue_data,
        {
            "pdf": out,
            "html": html_path,
            "json": json_path,
            **report_paths,
        },
    )
    desktop_copy_path = copy_gazette_outputs_to_desktop([out, html_path, json_path])

    typer.echo(f"OK: issue JSON: {json_path}")
    typer.echo(f"OK: random news cache: {random_cache_path}")
    typer.echo(f"OK: source report: {report_paths['source_report']}")
    typer.echo(f"OK: archive: {archive_path}")
    typer.echo(f"OK: desktop copy: {desktop_copy_path}")
    typer.echo(f"OK: HTML: {html_path}")
    typer.echo(f"OK: PDF: {out}")


if __name__ == "__main__":
    app()
