# ChatGPT Haber v1.0

## Durum: Tamamlandı / Bakım Modu

ChatGPT Haber, üç sayfalık Türkçe gazete üreten, PDF ve statik web çıktısı hazırlayan yerel bir yayın aracıdır.

v1.0 hedefleri tamamlanmıştır. Yeni özellik geliştirmesi planlanmamaktadır. Proje yalnız kritik hata, kaynak kırılması ve güvenlik düzeltmeleri için bakım modundadır.

## Canlı Site

Canlı gazete:

https://faliardic.github.io/chatgpt-haber/

## Özellikler

- Üç sayfalık Türkçe gazete: manşet, gündem-ekonomi ve teknoloji.
- RSS toplama, editoryal filtreleme ve kaynak doğrulama raporları.
- Fast ve full üretim modları.
- PDF içinde haber detayları ve `GAZETEYE DÖNÜŞ` bağlantıları.
- GitHub Pages için statik web gazetesi.
- Web üzerinde PDF indirme bağlantısı ve tarih arşivi.
- Windows Gazette Studio arayüzü.
- Build timing ölçümleri ve hedef odaklı hızlı cleanup.

## Hızlı Kullanım

Kurulum:

```powershell
python -m pip install -e .
python -m playwright install chromium
```

Yerel örnek veriyle hızlı gazete üretimi:

```powershell
python -m chatgpt_haber.cli build --mode fast --no-live --input-json examples\issue.sample.json --out dist\gazete.pdf
```

Canlı RSS akışlarıyla üretim:

```powershell
python -m chatgpt_haber.cli build --mode fast --out dist\gazete.pdf
```

## Gazette Studio

Gazette Studio, Windows üzerinde temel üretim komutlarını tek pencerede sunar.

- `Gazete Üret`: `--mode fast`
- `Tam Üretim`: `--mode full`
- son PDF/HTML açma
- kaynak raporu açma
- testleri çalıştırma

Uygulama kaynak kodu: `apps/gazette_studio.py`

## Fast ve Full Modları

Fast mod günlük üretim içindir:

```powershell
python -m chatgpt_haber.cli build --mode fast
```

Full mod detay zenginleştirme, portable HTML, arşiv ve masaüstü kopyasını da çalıştırır:

```powershell
python -m chatgpt_haber.cli build --mode full
```

## Web Sitesini Güncelleme

GitHub Pages çıktısı `main` dalındaki `docs/` klasöründen yayınlanır.

Offline test yayını:

```powershell
python -m chatgpt_haber.cli publish-pages --no-live --input-json examples\issue.sample.json
```

Canlı site çıktısını güncelleme:

```powershell
python -m chatgpt_haber.cli publish-pages
```

Bu komut `docs/index.html`, `docs/gazete.pdf`, `docs/issue.json` ve `docs/archive/` tarih arşivini günceller.

## Testler

Tam test ve compile:

```powershell
python -m pytest -q
python -m compileall chatgpt_haber services apps
git diff --check
```

## Windows Paketi

Windows dağıtım klasörünü üretmek için:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
```

Beklenen çıktı:

```text
dist\ChatGPTHaber\ChatGPTHaber.exe
```

Release paketi:

```text
release\ChatGPTHaber-v1.0.0-windows.zip
```

Playwright/Chromium bağımlılıkları nedeniyle `dist\ChatGPTHaber` klasörü bütün olarak taşınmalıdır.

## Mimari

Ana akış:

```text
RSS veya issue JSON -> normalize -> teknoloji sayfası garantisi -> editoryal filtre -> görsel zenginleştirme -> doğrulama -> HTML -> PDF
```

Önemli modüller:

- `chatgpt_haber/cli.py`: komut satırı girişleri.
- `chatgpt_haber/pages_publish.py`: GitHub Pages statik site yayını.
- `chatgpt_haber/render.py`: HTML ve PDF render.
- `chatgpt_haber/builder.py`: RSS tabanlı sayı üretimi.
- `chatgpt_haber/technology_page.py`: üçüncü sayfa teknoloji garantisi.
- `services/news_quality_filters.py`: final güvenlik ve kalite filtreleri.

## Bilinen Sınırlar

- Canlı üretim RSS kaynaklarının erişilebilirliğine bağlıdır.
- PDF üretimi için Playwright Chromium gerekir.
- Windows EXE klasörü tek dosya değildir; bağımlılık klasörüyle birlikte dağıtılır.
- Statik site kullanıcı hesabı, backend veya veritabanı içermez.

## Bakım Politikası

Bu repository v1.0 itibarıyla bakım modundadır. Kabul edilen değişiklikler kritik hata, bozuk RSS kaynağı, güvenlik sorunu, işletim sistemi veya bağımlılık uyumluluk hatası ve GitHub Pages yayın hatası ile sınırlıdır.

Yeni özellik geliştirmesi planlanmamaktadır.
