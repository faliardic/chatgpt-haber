import inspect
from pathlib import Path

import pytest
from typer.testing import CliRunner

import chatgpt_haber.cli as cli
from chatgpt_haber.cli import app


runner = CliRunner()


def test_build_help():
    result = runner.invoke(app, ["build", "--help"])
    assert result.exit_code == 0
    assert "paper-size" in result.stdout
    assert "--mode" in result.stdout


def sample_issue() -> dict:
    article = {
        "id": "main-1",
        "section": "gundem",
        "kicker": "GUNDEM",
        "headline": "Ana haber",
        "importance": 1,
        "dek": "Ana haber ozeti",
        "body": ["Ana haber metni"],
        "source_bundle": [
            {
                "name": "Kaynak",
                "url": "https://example.com/main",
                "published_at": "2026-07-12T09:00:00+03:00",
                "source_type": "rss",
                "is_primary": False,
            }
        ],
        "verification": {"status": "single_source", "checked_at": "2026-07-12T09:00:00+03:00", "method": [], "note": ""},
        "layout_hint": {"story_size": "secondary", "column_span": 1, "preferred_position": "mid"},
        "image": {},
    }
    return {
        "issue": {"issue_date": "2026-07-12", "page_count": 3, "paper_size": "A3", "title": "ChatGPT Gazette"},
        "pages": [
            {"page_no": 1, "template": "front_page", "name": "Manşet", "articles": [article.copy()], "briefs": []},
            {"page_no": 2, "template": "news_page", "name": "Gündem ve Ekonomi", "articles": [article.copy()], "briefs": []},
            {"page_no": 3, "template": "news_page", "name": "Teknoloji", "articles": [article.copy()], "briefs": []},
        ],
    }


def install_build_fakes(monkeypatch, calls: dict) -> None:
    monkeypatch.setattr(cli, "cleanup_current_build_outputs", lambda **kwargs: {"removed_files": 0, "removed_detail_files": 0})
    monkeypatch.setattr(cli, "read_json", lambda path: {})
    monkeypatch.setattr(cli, "normalize_issue", lambda raw, issue_date=None, paper_size=None: sample_issue())
    monkeypatch.setattr(cli, "ensure_technology_third_page", lambda issue_data, raw_issue=None: issue_data)
    monkeypatch.setattr(cli, "sanitize_issue_articles", lambda issue_data: issue_data)
    monkeypatch.setattr(cli, "enrich_issue_images", lambda issue_data, image_dir: issue_data)
    monkeypatch.setattr(cli, "validate_issue_data", lambda issue_data: None)
    monkeypatch.setattr(cli, "write_random_news_cache", lambda issue_data: Path("cache/latest_issue.json"))
    monkeypatch.setattr(
        cli,
        "write_reports",
        lambda issue_data, dist_dir: {
            "source_report": dist_dir / "source_report.json",
            "source_report_html": dist_dir / "source_report.html",
        },
    )

    def fake_enrich(issue_data):
        calls["enrich_article_details"] = calls.get("enrich_article_details", 0) + 1
        return issue_data

    def fake_render_html(issue_data, html_path, **kwargs):
        calls.setdefault("render_html", []).append(kwargs)
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text("<html></html>", encoding="utf-8")

    def fake_render_pdf(html_path, pdf_path):
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(b"%PDF-1.4\n")

    def fake_archive(issue_data, output_paths):
        calls["archive"] = calls.get("archive", 0) + 1
        return Path("archive/test")

    def fake_copy(paths):
        calls["desktop_copy"] = calls.get("desktop_copy", 0) + 1
        return Path("Desktop/Gazette")

    monkeypatch.setattr(cli, "enrich_article_details", fake_enrich)
    monkeypatch.setattr(cli, "render_html", fake_render_html)
    monkeypatch.setattr(cli, "render_pdf", fake_render_pdf)
    monkeypatch.setattr(cli, "archive_outputs", fake_archive)
    monkeypatch.setattr(cli, "copy_gazette_outputs_to_desktop", fake_copy)


def run_build(monkeypatch, tmp_path, args: list[str] | None = None) -> tuple[object, dict, Path]:
    calls: dict = {}
    install_build_fakes(monkeypatch, calls)
    out = tmp_path / "gazete.pdf"
    result = runner.invoke(
        app,
        ["build", "--no-live", "--input-json", "examples/issue.sample.json", "--out", str(out), *(args or [])],
    )
    return result, calls, tmp_path / "build_timing.json"


def test_build_default_mode_is_fast(monkeypatch, tmp_path):
    result, calls, timing_path = run_build(monkeypatch, tmp_path)

    assert result.exit_code == 0, result.output
    assert calls.get("enrich_article_details", 0) == 0
    assert calls.get("archive", 0) == 0
    assert calls.get("desktop_copy", 0) == 0
    assert len(calls["render_html"]) == 1
    assert calls["render_html"][0]["include_brief_details"] is True
    assert timing_path.exists()
    assert '"mode": "fast"' in timing_path.read_text(encoding="utf-8")
    assert '"skipped": true' in timing_path.read_text(encoding="utf-8")


def test_build_full_mode_preserves_full_outputs(monkeypatch, tmp_path):
    result, calls, timing_path = run_build(monkeypatch, tmp_path, ["--mode", "full"])

    assert result.exit_code == 0, result.output
    assert calls.get("enrich_article_details", 0) == 1
    assert calls.get("archive", 0) == 1
    assert calls.get("desktop_copy", 0) == 1
    assert len(calls["render_html"]) == 2
    assert calls["render_html"][0]["include_brief_details"] is True
    assert calls["render_html"][1]["portable_assets"] is True
    assert calls["render_html"][1]["include_brief_details"] is True
    assert '"mode": "full"' in timing_path.read_text(encoding="utf-8")


def test_build_rejects_invalid_mode():
    result = runner.invoke(app, ["build", "--mode", "quick"])

    assert result.exit_code != 0
    assert "mode fast veya full" in result.output


def test_cleanup_current_build_outputs_only_removes_known_generated_files(tmp_path):
    dist_dir = tmp_path / "dist" / "current"
    dist_dir.mkdir(parents=True)
    pdf_path = dist_dir / "gazete.pdf"
    html_path = dist_dir / "gazete.html"
    json_path = dist_dir / "issue.json"
    generated = [
        pdf_path,
        html_path,
        json_path,
        dist_dir / "build_timing.json",
        dist_dir / "source_report.json",
        dist_dir / "quality_report.json",
        dist_dir / "earthquake_report.json",
        dist_dir / "image_report.json",
        dist_dir / "source_report.html",
    ]
    for path in generated:
        path.write_text("generated", encoding="utf-8")

    articles_dir = dist_dir / "articles"
    articles_dir.mkdir()
    for index in range(3):
        (articles_dir / f"detail-{index}.html").write_text("detail", encoding="utf-8")
    keep_detail_asset = articles_dir / "keep.txt"
    keep_detail_asset.write_text("not html", encoding="utf-8")

    assets_dir = dist_dir / "assets"
    assets_dir.mkdir()
    image = assets_dir / "image.jpg"
    image.write_bytes(b"image")
    unrelated = dist_dir / "manual-note.html"
    unrelated.write_text("user file", encoding="utf-8")
    sibling_benchmark = tmp_path / "dist" / "benchmark-fast" / "gazete.html"
    sibling_benchmark.parent.mkdir(parents=True)
    sibling_benchmark.write_text("benchmark", encoding="utf-8")
    archive_file = tmp_path / "archive" / "2026-07-12" / "gazete.html"
    archive_file.parent.mkdir(parents=True)
    archive_file.write_text("archive", encoding="utf-8")
    output_file = tmp_path / "output" / "old.html"
    output_file.parent.mkdir()
    output_file.write_text("output", encoding="utf-8")
    cache_file = tmp_path / "cache" / "old.json"
    cache_file.parent.mkdir()
    cache_file.write_text("cache", encoding="utf-8")

    result = cli.cleanup_current_build_outputs(
        dist_dir=dist_dir,
        pdf_path=pdf_path,
        html_path=html_path,
        json_path=json_path,
    )

    assert result == {"removed_files": 9, "removed_detail_files": 3}
    assert all(not path.exists() for path in generated)
    assert not any((articles_dir / f"detail-{index}.html").exists() for index in range(3))
    assert keep_detail_asset.exists()
    assert image.exists()
    assert unrelated.exists()
    assert sibling_benchmark.exists()
    assert archive_file.exists()
    assert output_file.exists()
    assert cache_file.exists()


def test_cleanup_current_build_outputs_allows_missing_files(tmp_path):
    result = cli.cleanup_current_build_outputs(
        dist_dir=tmp_path / "dist",
        pdf_path=tmp_path / "dist" / "gazete.pdf",
        html_path=tmp_path / "dist" / "gazete.html",
        json_path=tmp_path / "dist" / "issue.json",
    )

    assert result == {"removed_files": 0, "removed_detail_files": 0}


def test_cleanup_current_build_outputs_does_not_use_global_rglob():
    source = inspect.getsource(cli.cleanup_current_build_outputs)

    assert ".rglob(" not in source


def test_cleanup_current_build_outputs_skips_articles_symlink(tmp_path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    target = tmp_path / "external_articles"
    target.mkdir()
    external_html = target / "external.html"
    external_html.write_text("external", encoding="utf-8")
    articles_link = dist_dir / "articles"
    try:
        articles_link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is not available on this platform")

    result = cli.cleanup_current_build_outputs(
        dist_dir=dist_dir,
        pdf_path=dist_dir / "gazete.pdf",
        html_path=dist_dir / "gazete.html",
        json_path=dist_dir / "issue.json",
    )

    assert result == {"removed_files": 0, "removed_detail_files": 0}
    assert external_html.exists()
