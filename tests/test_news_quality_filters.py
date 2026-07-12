import pytest

from services.news_quality_filters import (
    apply_hard_reject_filters,
    assert_no_forbidden_rendered_text,
    is_generic_earthquake_clickbait,
    sanitize_items_or_fail,
)


def test_specific_generic_earthquake_title_is_hard_rejected():
    item = {
        "headline": "Son dakika deprem mi oldu? Az önce deprem nerede oldu? İstanbul, Ankara, İzmir ve il il AFAD son depremler 01 Haziran 2026",
        "body": [
            "Son depremler... Son dakika deprem mi oldu? Az önce deprem nerede oldu?",
            "Artçı deprem mi oldu? Son deprem büyüklüğü ne kadar?",
            "Yakınımdaki depremler nelerdir? Anlık deprem mi oldu?",
            "Son dakika canlı deprem Türkiye haritası",
        ],
        "url": "https://example.test/son-depremler",
    }

    assert is_generic_earthquake_clickbait(item)
    rejected = apply_hard_reject_filters(item)
    assert rejected["accepted"] is False
    assert rejected["rejected"] is True
    assert rejected["reject_reason"] == "seo_generic_earthquake_clickbait"
    assert rejected["exclude_from_pdf"] is True
    assert rejected["exclude_from_random"] is True


def test_serious_earthquake_signal_is_not_generic_clickbait():
    item = {
        "headline": "AFAD: Marmara'da 5.1 büyüklüğünde deprem",
        "dek": "Resmi verilere göre deprem sonrası hasar tespit çalışması başlatıldı.",
    }

    assert not is_generic_earthquake_clickbait(item)


def test_forbidden_earthquake_article_cannot_reach_front_page_or_detail_render():
    item = {
        "title": "Son dakika deprem mi oldu? Az önce deprem nerede oldu? İstanbul, Ankara, İzmir ve il il AFAD son depremler 01 Haziran 2026",
        "summary": "Son depremler... Son dakika deprem mi oldu? Az önce deprem nerede oldu? AFAD son depremler Kandilli son depremler Yakınımdaki depremler Anlık deprem mi oldu Son dakika canlı deprem Türkiye haritası",
        "source": "NTV TÜRKİYE",
        "category": "GUNDEM",
        "accepted": True,
        "importance": 999,
        "url": "https://example.com/son-dakika-deprem-mi-oldu-afad-son-depremler",
    }

    clean = sanitize_items_or_fail([item], "test_front_page_before_render")

    assert clean == []
    assert item["reject_reason"] == "seo_generic_earthquake_clickbait"


def test_final_html_validator_blocks_forbidden_earthquake_text():
    html = """
    <html>
    <body>
    <h1>Son dakika deprem mi oldu?</h1>
    <p>Az önce deprem nerede oldu? AFAD son depremler Kandilli son depremler</p>
    </body>
    </html>
    """

    with pytest.raises(RuntimeError):
        assert_no_forbidden_rendered_text(html, "test_final_html")
