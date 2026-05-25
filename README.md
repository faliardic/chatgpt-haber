# CHATGPT HABER

AI tarafindan uretilen haber JSON verisinden 16 sayfalik PDF gazete ureten Python/Jinja/Playwright projesi.

## Akis

1. `raw_ai_output.txt` icindeki AI ciktisi `clean_ai_output.py` ile temizlenir.
2. `data/issue.json` `repair_issue.py` ile normalize edilir.
3. `validate_issue.py` JSON semasini kontrol eder.
4. `main.py` Jinja template'leriyle HTML uretir ve Playwright ile PDF'e cevirir.

## Calistirma

```powershell
.\venv\Scripts\python.exe main.py
```

PDF ciktisi:

```text
output/CHATGPT_HABER.pdf
```

## Son Durum

- PDF 16 sayfa olarak uretiliyor.
- Ana sayfa yeniden dizayn edildi.
- Ic sayfalarda tasma kontrolu ve gorsel placeholder alanlari var.
- Sanal ortam ve gecici ciktillar Git disinda tutulur.
