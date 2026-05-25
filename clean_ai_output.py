from pathlib import Path
import json
import re
import sys
from urllib.parse import unquote


BASE_DIR = Path(__file__).resolve().parent

RAW_OUTPUT_PATH = BASE_DIR / "raw_ai_output.txt"
ISSUE_OUTPUT_PATH = BASE_DIR / "data" / "issue.json"
DEBUG_OUTPUT_PATH = BASE_DIR / "debug_json_error.txt"
REPAIRED_OUTPUT_PATH = BASE_DIR / "debug_repaired_json.txt"


def fail(message: str) -> None:
    print(f"HATA: {message}")
    sys.exit(1)


def extract_json(text: str) -> str:
    """
    AI çıktısının içinden JSON bölümünü ayıklar.
    JSON dışında açıklama varsa ilk { ile son } arasını alır.
    Markdown kod bloğu varsa temizler.
    """
    text = text.strip()

    if not text:
        fail("raw_ai_output.txt boş.")

    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        fail("JSON başlangıcı veya bitişi bulunamadı.")

    return text[start:end + 1]


def normalize_quotes(text: str) -> str:
    replacements = {
        "“": '"',
        "”": '"',
        "„": '"',
        "‟": '"',
        "‘": "'",
        "’": "'",
        "‚": "'",
        "‛": "'",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def repair_corrupted_url_quotes(text: str) -> str:
    """
    Şu bozuk formatları düzeltir:

    "url":"["https"://example.com/..."
    "url": "["https"://example.com/..."
    "url":"[https://example.com]"
    "url": [https://example.com]
    "url": https://example.com
    """

    # "url":"["https"://example.com/path"
    text = re.sub(
        r'("url"\s*:\s*)"\["(https?)"://([^"]*?)"',
        r'\1"\2://\3"',
        text,
        flags=re.IGNORECASE
    )

    # "url": "["https"://example.com/path"
    text = re.sub(
        r'("url"\s*:\s*)"\[\s*"(https?)"://([^"]*?)"',
        r'\1"\2://\3"',
        text,
        flags=re.IGNORECASE
    )

    # "url":"[https://example.com]"
    text = re.sub(
        r'("url"\s*:\s*)"\[(https?://[^\]"]+)\]"',
        r'\1"\2"',
        text,
        flags=re.IGNORECASE
    )

    # "url":"[www.example.com]"
    text = re.sub(
        r'("url"\s*:\s*)"\[(www\.[^\]"]+)\]"',
        r'\1"https://\2"',
        text,
        flags=re.IGNORECASE
    )

    # "url": [https://example.com]
    text = re.sub(
        r'("url"\s*:\s*)\[(https?://[^\]\s"]+)\]',
        r'\1"\2"',
        text,
        flags=re.IGNORECASE
    )

    # "url": [www.example.com]
    text = re.sub(
        r'("url"\s*:\s*)\[(www\.[^\]\s"]+)\]',
        r'\1"https://\2"',
        text,
        flags=re.IGNORECASE
    )

    # "url": https://example.com
    text = re.sub(
        r'("url"\s*:\s*)(https?://[^,\n\r}\]\s"]+)',
        r'\1"\2"',
        text,
        flags=re.IGNORECASE
    )

    # "url": www.example.com
    text = re.sub(
        r'("url"\s*:\s*)(www\.[^,\n\r}\]\s"]+)',
        r'\1"https://\2"',
        text,
        flags=re.IGNORECASE
    )

    # "url": "https"://example.com
    text = re.sub(
        r'("url"\s*:\s*)"https"://([^"]+)"',
        r'\1"https://\2"',
        text,
        flags=re.IGNORECASE
    )

    # "url": "http"://example.com
    text = re.sub(
        r'("url"\s*:\s*)"http"://([^"]+)"',
        r'\1"http://\2"',
        text,
        flags=re.IGNORECASE
    )

    return text


def repair_markdown_links(text: str) -> str:
    """
    Markdown linkleri düz metne indirger:

    [Kaynak](https://example.com)
    ->
    Kaynak - https://example.com
    """
    text = re.sub(
        r'\[([^\]]+)\]\((https?://[^)]+)\)',
        r'\1 - \2',
        text
    )

    return text


def repair_trailing_commas(text: str) -> str:
    """
    Object/list kapanmadan önceki fazla virgülleri siler.
    """
    return re.sub(r",\s*([}\]])", r"\1", text)


def repair_single_quoted_values(text: str) -> str:
    """
    Basit tek tırnaklı JSON değerlerini çift tırnağa çevirir.

    "status": 'confirmed'
    ->
    "status": "confirmed"
    """
    return re.sub(
        r'(:\s*)\'([^\'\n\r]*)\'(\s*[,}\]])',
        r'\1"\2"\3',
        text
    )


def repair_missing_quotes_on_simple_keys(text: str) -> str:
    """
    Basit key hatalarını düzeltir:

    title: "Haber"
    ->
    "title": "Haber"
    """
    return re.sub(
        r'([{\[,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:',
        r'\1"\2":',
        text
    )


def repair_unescaped_newlines_inside_strings(text: str) -> str:
    """
    String içindeki ham satır sonlarını \\n yapar.
    """
    result = []
    inside_string = False
    escape_next = False

    for char in text:
        if escape_next:
            result.append(char)
            escape_next = False
            continue

        if char == "\\":
            result.append(char)
            escape_next = True
            continue

        if char == '"':
            result.append(char)
            inside_string = not inside_string
            continue

        if inside_string and char == "\n":
            result.append("\\n")
            continue

        if inside_string and char == "\r":
            continue

        result.append(char)

    return "".join(result)


def light_repair_json(text: str) -> str:
    """
    JSON parse edilmeden önce metin seviyesinde yaygın AI hatalarını düzeltir.
    """
    text = normalize_quotes(text)

    # Önce URL bozulmalarını düzelt.
    # Bu işlem markdown link düzeltmesinden önce yapılmalı.
    text = repair_corrupted_url_quotes(text)

    text = repair_markdown_links(text)
    text = repair_single_quoted_values(text)
    text = repair_missing_quotes_on_simple_keys(text)
    text = repair_trailing_commas(text)
    text = repair_unescaped_newlines_inside_strings(text)

    return text


def clean_text_value(value: str) -> str:
    """
    Parse sonrası string değerleri sadeleştirir.
    """
    value = unquote(value)

    value = value.replace("\n", " ")
    value = value.replace("\r", " ")

    value = re.sub(r"\s+", " ", value).strip()

    return value


def clean_url(value: str) -> str:
    """
    URL alanını sadeleştirir.
    """
    value = clean_text_value(value)

    value = value.strip()
    markdown_match = re.search(r"\]\((https?://[^)\s]+)\)", value)
    if markdown_match:
        value = markdown_match.group(1)
    else:
        value = value.split("](", 1)[0]

    value = value.strip("[](){}<>")
    value = value.strip('"').strip("'")

    value = value.replace('"https"://', "https://")
    value = value.replace('"http"://', "http://")
    value = value.replace("https\"://", "https://")
    value = value.replace("http\"://", "http://")

    if value.startswith("www."):
        value = "https://" + value

    url_match = re.search(r"https?://[^\s\])}<>]+", value)
    if url_match:
        value = url_match.group(0)

    return value


def clean_verification_note(value: str, status: str | None = None) -> str:
    """
    verification_note alanı bozulduysa sade ve güvenli metne çevirir.
    """
    value = clean_text_value(value)

    # Markdown / URL / encoded JSON kalıntısı varsa agresif sadeleştir.
    is_corrupted = any(
        marker in value
        for marker in [
            "%22",
            "%7B",
            "%7D",
            "](http",
            "published_at",
            '"url"',
            '"name"',
            "sources",
            "verification_note",
        ]
    )

    if is_corrupted or len(value) > 220:
        if status == "confirmed":
            return "Haber kaynaklarla doğrulandı."
        if status == "developing":
            return "Haber kaynaklarla kontrol edildi; süreç devam ettiği için gelişen haber olarak işaretlendi."
        if status == "rumor":
            return "Resmi doğrulama bulunmadığı için söylenti olarak işaretlendi."
        if status == "analysis":
            return "Kaynaklara dayalı analiz olarak işaretlendi."

        return "Kaynaklar kontrol edildi; doğrulama notu sadeleştirildi."

    return value


def post_process_issue_data(data):
    """
    JSON parse edildikten sonra tüm veri içinde dolaşır.
    url ve verification_note alanlarını normalize eder.
    """
    if isinstance(data, dict):
        status = data.get("status")

        cleaned = {}

        for key, value in data.items():
            if key == "url" and isinstance(value, str):
                cleaned[key] = clean_url(value)

            elif key == "verification_note" and isinstance(value, str):
                cleaned[key] = clean_verification_note(value, status=status)

            elif isinstance(value, str):
                cleaned[key] = clean_text_value(value)

            else:
                cleaned[key] = post_process_issue_data(value)

        return cleaned

    if isinstance(data, list):
        return [post_process_issue_data(item) for item in data]

    return data


def save_debug_context(json_text: str, error: json.JSONDecodeError) -> None:
    pos = error.pos
    start = max(0, pos - 1200)
    end = min(len(json_text), pos + 1200)

    context = json_text[start:end]

    debug_text = (
        "JSON HATA BAĞLAMI\n"
        "=================\n\n"
        f"Hata: {error}\n"
        f"Satır: {error.lineno}\n"
        f"Sütun: {error.colno}\n"
        f"Pozisyon: {pos}\n\n"
        "Hatalı bölgenin çevresi:\n\n"
        f"{context}\n"
    )

    DEBUG_OUTPUT_PATH.write_text(debug_text, encoding="utf-8")


def validate_json(json_text: str) -> dict:
    """
    Önce doğrudan parse dener.
    Olmazsa repair uygular.
    Repair edilmiş metni ayrıca debug_repaired_json.txt içine yazar.
    """
    try:
        issue_data = json.loads(json_text)
        return post_process_issue_data(issue_data)

    except json.JSONDecodeError:
        repaired_text = light_repair_json(json_text)
        REPAIRED_OUTPUT_PATH.write_text(repaired_text, encoding="utf-8")

        try:
            issue_data = json.loads(repaired_text)
            return post_process_issue_data(issue_data)

        except json.JSONDecodeError as error:
            save_debug_context(repaired_text, error)
            fail(
                "Geçersiz JSON. Hata bağlamı debug_json_error.txt dosyasına yazıldı. "
                "Onarılmış metin debug_repaired_json.txt dosyasına yazıldı."
            )


def save_issue(issue_data: dict) -> None:
    ISSUE_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    formatted_json = json.dumps(
        issue_data,
        ensure_ascii=False,
        indent=2
    )

    ISSUE_OUTPUT_PATH.write_text(formatted_json, encoding="utf-8")


def main() -> None:
    if not RAW_OUTPUT_PATH.exists():
        fail(f"raw_ai_output.txt bulunamadı: {RAW_OUTPUT_PATH}")

    raw_text = RAW_OUTPUT_PATH.read_text(encoding="utf-8")

    json_text = extract_json(raw_text)
    issue_data = validate_json(json_text)
    save_issue(issue_data)

    print("OK: AI çıktısı temizlendi.")
    print(f"OK: issue.json oluşturuldu: {ISSUE_OUTPUT_PATH}")


if __name__ == "__main__":
    import json
    import re
    from pathlib import Path
    
    text = Path("raw_ai_output.txt").read_text(encoding="utf-8")
    s = text.find("{")
    e = text.rfind("}")
    j = text[s:e+1]
    j = re.sub(r'\]\([^)]*\)', '', j)
    for o,n in [('%22','"'),('%2F','/'),('%3A',':'),('%2C',','),('%7B','{'),('%7D','}'),('%20',' ')]:
        j = j.replace(o,n)
    j = re.sub(r'"url":"\[https://', r'"url":"https://', j)
    j = j.replace('\\"', '"').replace('\\/', '/')
    d = json.loads(j)
    Path("data").mkdir(exist_ok=True)
    Path("data/issue.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print("✅ OK")
