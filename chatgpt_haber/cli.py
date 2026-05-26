from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import typer

from .issue import BASE_DIR, normalize_issue, read_json, validate_issue_data, write_json
from .render import render_html, render_pdf
from .sources import enrich_issue_images, issue_from_rss


app = typer.Typer(help="Tek komutla 3 sayfalık baskıya hazır gazete üretir.")


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
) -> None:
    if issue_date is None:
        issue_date = date.today().isoformat()

    paper_size = paper_size.upper()
    if paper_size not in {"A3", "A4"}:
        raise typer.BadParameter("paper-size A3 veya A4 olmalı.")

    dist_dir = out.parent
    image_dir = dist_dir / "assets"

    issue_data = issue_from_rss(issue_date, paper_size, image_dir=image_dir) if live else None
    if issue_data is None:
        source = input_json or BASE_DIR / "data" / "issue.json"
        issue_data = normalize_issue(read_json(source), issue_date=issue_date, paper_size=paper_size)
        enrich_issue_images(issue_data, image_dir)

    validate_issue_data(issue_data)

    html_path = dist_dir / f"{out.stem}.html"
    json_path = dist_dir / "issue.json"

    write_json(json_path, issue_data)
    render_html(issue_data, html_path)
    render_pdf(html_path, out)

    typer.echo(f"OK: issue JSON: {json_path}")
    typer.echo(f"OK: HTML: {html_path}")
    typer.echo(f"OK: PDF: {out}")


if __name__ == "__main__":
    app()
