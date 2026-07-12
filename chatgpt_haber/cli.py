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

from .builder import issue_from_rss
from .build_timing import BuildTimer
from .issue import BASE_DIR, normalize_issue, read_json, validate_issue_data, write_json
from .render import render_html, render_pdf
from .sources import enrich_article_details, enrich_issue_images, sanitize_issue_articles
from .technology_page import ensure_technology_third_page


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


def normalize_build_mode(value: str) -> str:
    mode = value.strip().lower()
    if mode not in {"fast", "full"}:
        raise typer.BadParameter("mode fast veya full olmalı.")
    return mode


def should_enrich_article_details(mode: str) -> bool:
    return mode == "full"


def should_render_portable_html(mode: str, portable_html: bool) -> bool:
    return mode == "full" and portable_html


def should_archive(mode: str) -> bool:
    return mode == "full"


def should_copy_to_desktop(mode: str) -> bool:
    return mode == "full"


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
    mode: str = typer.Option("fast", "--mode", help="Build modu: fast veya full."),
) -> None:
    mode = normalize_build_mode(mode)
    if issue_date is None:
        issue_date = date.today().isoformat()

    paper_size = paper_size.upper()
    if paper_size not in {"A3", "A4"}:
        raise typer.BadParameter("paper-size A3 veya A4 olmalı.")

    dist_dir = out.parent
    image_dir = dist_dir / "assets"
    timing_path = dist_dir / "build_timing.json"
    timer = BuildTimer(mode)
    with timer.stage("cleanup"):
        cleanup_forbidden_render_artifacts()
    print("[GAZETTE DEBUG] cwd =", os.getcwd())
    print("[GAZETTE DEBUG] main file =", __file__)
    print("[GAZETTE DEBUG] sys.path[0] =", sys.path[0])
    print("[GAZETTE DEBUG] news_quality_filters =", nqf.__file__)

    with timer.stage("collect_issue"):
        issue_data = issue_from_rss(issue_date, paper_size, image_dir=image_dir) if live else None
        if issue_data is None:
            source = input_json or BASE_DIR / "data" / "issue.json"
            raw_issue = read_json(source)
            issue_data = normalize_issue(raw_issue, issue_date=issue_date, paper_size=paper_size)
            ensure_technology_third_page(issue_data, raw_issue=raw_issue)
    with timer.stage("sanitize"):
        sanitize_issue_articles(issue_data)
    if should_enrich_article_details(mode):
        with timer.stage("enrich_article_details"):
            enrich_article_details(issue_data)
    else:
        timer.skip("enrich_article_details")
    with timer.stage("enrich_images"):
        enrich_issue_images(issue_data, image_dir)

    with timer.stage("validate"):
        validate_issue_data(issue_data)

    html_path = dist_dir / f"{out.stem}.html"
    json_path = dist_dir / "issue.json"

    with timer.stage("write_issue_json"):
        write_json(json_path, issue_data)
    with timer.stage("write_random_cache"):
        random_cache_path = write_random_news_cache(issue_data)
    with timer.stage("write_reports"):
        report_paths = write_reports(issue_data, dist_dir)
    with timer.stage("render_pdf_html"):
        render_html(
            issue_data,
            html_path,
            portable_pdf_links=True,
            portable_assets=False,
            include_brief_details=(mode == "full"),
        )
    with timer.stage("render_pdf"):
        render_pdf(html_path, out)
    if should_render_portable_html(mode, portable_html):
        with timer.stage("render_portable_html"):
            render_html(
                issue_data,
                html_path,
                portable_pdf_links=True,
                portable_assets=True,
                include_brief_details=True,
            )
    else:
        timer.skip("render_portable_html")
    if should_archive(mode):
        with timer.stage("archive"):
            archive_path = archive_outputs(
                issue_data,
                {
                    "pdf": out,
                    "html": html_path,
                    "json": json_path,
                    **report_paths,
                },
            )
    else:
        archive_path = None
        timer.skip("archive")
    if should_copy_to_desktop(mode):
        with timer.stage("desktop_copy"):
            desktop_copy_path = copy_gazette_outputs_to_desktop([out, html_path, json_path])
    else:
        desktop_copy_path = None
        timer.skip("desktop_copy")
    timing_data = timer.write(timing_path)
    timer.print_summary(timing_data)

    typer.echo(f"OK: issue JSON: {json_path}")
    typer.echo(f"OK: random news cache: {random_cache_path}")
    typer.echo(f"OK: source report: {report_paths['source_report']}")
    if archive_path is not None:
        typer.echo(f"OK: archive: {archive_path}")
    if desktop_copy_path is not None:
        typer.echo(f"OK: desktop copy: {desktop_copy_path}")
    typer.echo(f"OK: timing: {timing_path}")
    typer.echo(f"OK: HTML: {html_path}")
    typer.echo(f"OK: PDF: {out}")


if __name__ == "__main__":
    app()
