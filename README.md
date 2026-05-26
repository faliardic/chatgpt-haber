# ChatGPT Haber

Tek komutla çalışan, baskıya hazır, üç sayfalık Türkçe gazete üreticisi.

## Kurulum

```bash
python -m pip install -e .
playwright install --with-deps chromium
```

Windows'ta `--with-deps` gerekli değilse şu komut yeterlidir:

```bash
playwright install chromium
```

## Kullanım

```bash
chatgpt-haber build --date 2026-05-26 --paper-size A3 --out dist/gazete-2026-05-26.pdf
```

Komut sırasıyla resmi RSS akışlarını dener, yeterli veri alamazsa `data/issue.json` dosyasını yeni üç sayfalık sözleşmeye dönüştürür, doğrular, tek HTML belge üretir ve Playwright ile PDF alır.

Yerel JSON ile çalıştırmak için:

```bash
chatgpt-haber build --no-live --input-json examples/issue.sample.json --out dist/ornek.pdf
```

## Mimari

Akış:

```text
kaynak toplama -> normalize -> doğrulama -> tek HTML render -> PDF render
```

Yeni şablon yapısı:

```text
templates/
  base.html
  pages/
    front_page.html
    news_page.html
  partials/
    masthead.html
    article.html
    hero_article.html
    briefs_strip.html
    figure.html
static/css/print.css
schemas/issue.schema.json
prompts/editorial_main_prompt.txt
```

`main.py` geriye dönük kısa yol olarak durur ve `data/issue.json` dosyasından `output/CHATGPT_HABER.pdf` üretir.
