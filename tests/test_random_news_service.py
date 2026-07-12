from __future__ import annotations

import json
import random
from pathlib import Path

from services.random_news_service import (
    RandomNewsService,
    copy_gazette_outputs_to_desktop,
    feedback_path,
    flatten_news,
    normalize_news,
    saved_news_path,
)
from apps.random_news_app import extension_reader_url


def write_cache(tmp_path: Path, items: list[dict]) -> Path:
    path = tmp_path / "issue.json"
    path.write_text(json.dumps({"news": items}, ensure_ascii=False), encoding="utf-8")
    return path


def service_for(tmp_path: Path, items: list[dict]) -> RandomNewsService:
    return RandomNewsService(cache_paths=[write_cache(tmp_path, items)], seen_path=tmp_path / "seen.json", rng=random.Random(1))


def test_accepted_current_news_with_link_enters_pool(tmp_path):
    service = service_for(
        tmp_path,
        [{"id": "1", "headline": "Ekonomi verileri açıklandı", "url": "https://news.test/1", "accepted": True}],
    )

    assert [item.id for item in service.filter_random_pool(service.load_current_news())] == ["1"]


def test_accepted_false_news_is_excluded(tmp_path):
    service = service_for(
        tmp_path,
        [{"id": "1", "headline": "Reddedilen haber", "url": "https://news.test/1", "accepted": False}],
    )

    assert service.filter_random_pool(service.load_current_news()) == []


def test_reject_reason_news_is_excluded(tmp_path):
    service = service_for(
        tmp_path,
        [{"id": "1", "headline": "Clickbait haber", "url": "https://news.test/1", "reject_reason": "clickbait"}],
    )

    assert service.filter_random_pool(service.load_current_news()) == []


def test_generic_earthquake_news_is_excluded(tmp_path):
    service = service_for(
        tmp_path,
        [{"id": "1", "headline": "Son dakika deprem mi oldu? AFAD son depremler", "url": "https://news.test/1"}],
    )

    assert service.filter_random_pool(service.load_current_news()) == []


def test_serious_earthquake_news_can_enter_pool(tmp_path):
    service = service_for(
        tmp_path,
        [
            {
                "id": "1",
                "headline": "7.0 büyüklüğünde deprem sonrası tsunami uyarısı",
                "url": "https://news.test/1",
                "source": "USGS",
                "earthquake_classification": "serious_earthquake_event",
            }
        ],
    )

    assert [item.id for item in service.filter_random_pool(service.load_current_news())] == ["1"]


def test_pick_prefers_unseen_news(tmp_path):
    service = service_for(
        tmp_path,
        [
            {"id": "1", "headline": "Birinci haber", "url": "https://news.test/1"},
            {"id": "2", "headline": "İkinci haber", "url": "https://news.test/2"},
        ],
    )
    service.mark_seen("1")

    assert service.pick_random_news().id == "2"


def test_seen_resets_when_all_news_were_seen(tmp_path):
    service = service_for(tmp_path, [{"id": "1", "headline": "Birinci haber", "url": "https://news.test/1"}])
    service.mark_seen("1")

    assert service.pick_random_news().id == "1"


def test_missing_fields_do_not_crash_normalization():
    assert normalize_news({"headline": "Başlık var ama link yok"}) is None


def test_normalize_news_keeps_full_body_paragraphs():
    item = normalize_news({
        "headline": "Tam metinli haber",
        "url": "https://news.test/full",
        "body": ["Birinci paragraf.", "İkinci paragraf."],
    })

    assert item is not None
    assert item.body == ("Birinci paragraf.", "İkinci paragraf.")
    assert item.full_text == "Birinci paragraf.\n\nİkinci paragraf."


def test_pick_random_news_fetches_full_text_when_cache_has_only_summary(tmp_path, monkeypatch):
    service = service_for(
        tmp_path,
        [{"id": "1", "headline": "Kaynak metni çekilecek", "url": "https://news.test/1", "summary": "Kısa özet"}],
    )
    monkeypatch.setattr(
        "services.random_news_service.extract_article_detail",
        lambda url, headline, **kwargs: ["Kaynak paragrafı bir.", "Kaynak paragrafı iki."],
    )

    item = service.pick_random_news()

    assert item is not None
    assert item.body == ("Kaynak paragrafı bir.", "Kaynak paragrafı iki.")
    assert "Kaynak paragrafı iki." in item.full_text


def test_missing_cache_returns_empty_list(tmp_path):
    service = RandomNewsService(cache_paths=[tmp_path / "missing.json"], seen_path=tmp_path / "seen.json")

    assert service.load_current_news() == []


def test_duplicate_urls_are_deduped(tmp_path):
    service = service_for(
        tmp_path,
        [
            {"id": "1", "headline": "Birinci haber", "url": "https://news.test/1"},
            {"id": "2", "headline": "Birinci haber kopyası", "url": "https://news.test/1"},
        ],
    )

    assert [item.id for item in service.load_current_news()] == ["1"]


def test_load_current_news_combines_multiple_cache_files(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(json.dumps({"news": [{"id": "1", "headline": "Birinci haber", "url": "https://news.test/1"}]}), encoding="utf-8")
    second.write_text(json.dumps({"news": [{"id": "2", "headline": "İkinci haber", "url": "https://news.test/2"}]}), encoding="utf-8")
    service = RandomNewsService(cache_paths=[first, second], seen_path=tmp_path / "seen.json")

    assert [item.id for item in service.load_current_news()] == ["1", "2"]


def test_issue_json_pages_are_flattened():
    items = flatten_news({"pages": [{"articles": [{"id": "a"}], "briefs": [{"id": "b"}]}]})

    assert [item["id"] for item in items] == ["a", "b"]


def test_extension_reader_url_adds_raw_param():
    assert extension_reader_url("https://example.com/news?id=1") == "https://example.com/news?id=1&gazette_raw=1"
    assert extension_reader_url("https://example.com/news?gazette_raw=0") == "https://example.com/news?gazette_raw=1"


def test_feedback_and_saved_news_are_written(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    service = service_for(tmp_path, [{"id": "1", "headline": "Birinci haber", "url": "https://news.test/1"}])
    item = service.load_current_news()[0]

    service.save_feedback(item, "like")
    service.save_news(item)

    assert feedback_path().exists()
    assert saved_news_path().exists()


def test_copy_gazette_outputs_to_desktop_copies_existing_files(tmp_path):
    pdf = tmp_path / "gazete.pdf"
    html = tmp_path / "gazete.html"
    pdf.write_text("pdf", encoding="utf-8")
    html.write_text("html", encoding="utf-8")
    target = tmp_path / "Desktop" / "Gazette"

    copied_to = copy_gazette_outputs_to_desktop([pdf, html, tmp_path / "missing.json"], target)

    assert copied_to == target
    assert (target / "gazete.pdf").read_text(encoding="utf-8") == "pdf"
    assert (target / "gazete.html").read_text(encoding="utf-8") == "html"
