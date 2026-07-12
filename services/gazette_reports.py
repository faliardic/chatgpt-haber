from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import json
import shutil
from pathlib import Path
from typing import Any

from services.news_quality_filters import is_generic_earthquake_clickbait


def iter_articles(issue_data: dict[str, Any]):
    for page in issue_data.get("pages", []):
        if not isinstance(page, dict):
            continue
        for collection_name in ("articles", "briefs"):
            for article in page.get(collection_name, []) or []:
                if isinstance(article, dict):
                    yield page, collection_name, article


def source_of(article: dict[str, Any]) -> str:
    sources = article.get("source_bundle") if isinstance(article.get("source_bundle"), list) else []
    source = sources[0] if sources and isinstance(sources[0], dict) else {}
    return str(source.get("name") or article.get("source") or "Kaynak")


def generate_source_report(issue_data: dict[str, Any]) -> dict[str, Any]:
    rows: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "source": "",
        "total": 0,
        "accepted": 0,
        "rejected": 0,
        "clickbait_or_seo": 0,
        "earthquake_seo_rejects": 0,
        "with_image": 0,
        "front_page": 0,
        "average_importance_score": 0,
    })
    score_totals: Counter[str] = Counter()
    for page, _, article in iter_articles(issue_data):
        source = source_of(article)
        row = rows[source]
        row["source"] = source
        row["total"] += 1
        rejected = article.get("rejected") is True or article.get("accepted") is False or bool(article.get("reject_reason"))
        row["rejected" if rejected else "accepted"] += 1
        if article.get("reject_reason") or is_generic_earthquake_clickbait(article):
            row["clickbait_or_seo"] += 1
        if article.get("reject_reason") == "seo_generic_earthquake_clickbait":
            row["earthquake_seo_rejects"] += 1
        if isinstance(article.get("image"), dict) and article["image"].get("path"):
            row["with_image"] += 1
        if page.get("page_no") == 1:
            row["front_page"] += 1
        score = article.get("importance_score")
        if isinstance(score, (int, float)):
            score_totals[source] += score
    for source, row in rows.items():
        if row["total"]:
            row["image_rate"] = round(row["with_image"] / row["total"], 3)
            row["average_importance_score"] = round(score_totals[source] / row["total"], 2)
    return {"generated_at": datetime.now().isoformat(), "sources": sorted(rows.values(), key=lambda row: row["total"], reverse=True)}


def generate_quality_report(issue_data: dict[str, Any]) -> dict[str, Any]:
    articles = []
    for page, collection_name, article in iter_articles(issue_data):
        quality = {
            "id": article.get("id"),
            "headline": article.get("headline"),
            "page_no": page.get("page_no"),
            "collection": collection_name,
            "source": source_of(article),
            "importance": article.get("importance"),
            "importance_score": article.get("importance_score"),
            "earthquake_classification": article.get("earthquake_classification", "not_earthquake"),
            "reject_reason": article.get("reject_reason", ""),
            "has_image": bool(isinstance(article.get("image"), dict) and article["image"].get("path")),
            "selection_reason": selection_reason(article),
        }
        article["quality"] = quality
        articles.append(quality)
    return {"generated_at": datetime.now().isoformat(), "articles": articles}


def selection_reason(article: dict[str, Any]) -> str:
    if article.get("reject_reason"):
        return f"elendi: {article['reject_reason']}"
    if article.get("earthquake_classification") == "serious_earthquake_event":
        return "ciddi deprem olayı ve resmi/etki sinyali"
    if article.get("importance_score"):
        return "kaynak, güncellik ve editoryal skorla seçildi"
    return "temiz haber havuzundan seçildi"


def generate_earthquake_report(issue_data: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for page, collection_name, article in iter_articles(issue_data):
        text = f"{article.get('headline', '')} {article.get('dek', '')}".casefold()
        if "deprem" not in text and not article.get("earthquake_classification"):
            continue
        rows.append({
            "id": article.get("id"),
            "headline": article.get("headline"),
            "page_no": page.get("page_no"),
            "collection": collection_name,
            "classification": article.get("earthquake_classification", "not_classified"),
            "magnitude": article.get("magnitude"),
            "location": article.get("location", ""),
            "official_source_detected": article.get("official_source_detected", False),
            "impact_detected": article.get("impact_detected", False),
            "reject_reason": article.get("reject_reason", ""),
        })
    return {"generated_at": datetime.now().isoformat(), "earthquake_items": rows}


def generate_image_report(issue_data: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for page, collection_name, article in iter_articles(issue_data):
        image = article.get("image") if isinstance(article.get("image"), dict) else {}
        rows.append({
            "id": article.get("id"),
            "headline": article.get("headline"),
            "page_no": page.get("page_no"),
            "collection": collection_name,
            "has_image": bool(image.get("path")),
            "path": image.get("path", ""),
            "width": image.get("width", 0),
            "height": image.get("height", 0),
            "is_fallback": str(image.get("path", "")).endswith("-fallback.jpg"),
        })
    return {"generated_at": datetime.now().isoformat(), "images": rows}


def write_reports(issue_data: dict[str, Any], dist_dir: Path) -> dict[str, Path]:
    dist_dir.mkdir(parents=True, exist_ok=True)
    reports = {
        "source_report": generate_source_report(issue_data),
        "quality_report": generate_quality_report(issue_data),
        "earthquake_report": generate_earthquake_report(issue_data),
        "image_report": generate_image_report(issue_data),
    }
    paths: dict[str, Path] = {}
    for name, data in reports.items():
        path = dist_dir / f"{name}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[name] = path
    paths["source_report_html"] = write_source_report_html(reports["source_report"], dist_dir / "source_report.html")
    return paths


def write_source_report_html(report: dict[str, Any], path: Path) -> Path:
    rows = "\n".join(
        f"<tr><td>{row['source']}</td><td>{row['total']}</td><td>{row['accepted']}</td><td>{row['rejected']}</td><td>{row['image_rate']}</td><td>{row['front_page']}</td></tr>"
        for row in report.get("sources", [])
    )
    html = f"""<!doctype html>
<html lang="tr"><meta charset="utf-8"><title>Gazette Kaynak Raporu</title>
<style>body{{font-family:Segoe UI,sans-serif;margin:24px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px}}th{{background:#1f4f8f;color:white;text-align:left}}</style>
<h1>Gazette Kaynak Raporu</h1>
<table><thead><tr><th>Kaynak</th><th>Toplam</th><th>Kabul</th><th>Ret</th><th>Görsel Oranı</th><th>1. Sayfa</th></tr></thead><tbody>{rows}</tbody></table>
</html>"""
    path.write_text(html, encoding="utf-8")
    return path


def archive_outputs(issue_data: dict[str, Any], output_paths: dict[str, Path], archive_root: Path = Path("archive")) -> Path:
    issue_date = str(issue_data.get("issue", {}).get("issue_date") or datetime.now().date())
    target = archive_root / issue_date
    target.mkdir(parents=True, exist_ok=True)
    for name, path in output_paths.items():
        if path and path.exists() and path.is_file():
            shutil.copy2(path, target / path.name)
    return target
