(() => {
  const PANEL_ID = "gazette-raw-reader-panel";

  const clean = (value) => (value || "").replace(/\s+/g, " ").trim();

  const scoreContainer = (element) => {
    const paragraphs = [...element.querySelectorAll("p")]
      .map((p) => clean(p.innerText))
      .filter((text) => text.length > 40);
    const textLength = paragraphs.join(" ").length;
    const bad = element.querySelectorAll("nav, footer, header, aside, form, script, style").length;
    return textLength + paragraphs.length * 120 - bad * 180;
  };

  const bestArticleNode = () => {
    const selectors = [
      "article",
      "[data-testid='article-body']",
      ".article-body",
      ".news-detail",
      ".haber-detay",
      ".entry-content",
      ".post-content",
      "main"
    ];
    const candidates = selectors.flatMap((selector) => [...document.querySelectorAll(selector)]);
    const unique = [...new Set(candidates)].filter(Boolean);
    unique.sort((a, b) => scoreContainer(b) - scoreContainer(a));
    return unique[0] || document.body;
  };

  const extractRawText = () => {
    const title = clean(document.querySelector("h1")?.innerText || document.title);
    const node = bestArticleNode();
    const paragraphs = [...node.querySelectorAll("p")]
      .map((p) => clean(p.innerText))
      .filter((text) => text.length > 35)
      .filter((text, index, arr) => arr.indexOf(text) === index);
    const body = paragraphs.length ? paragraphs.join("\n\n") : clean(node.innerText);
    return `${title}\n\n${body}`.trim();
  };

  const showPanel = () => {
    document.getElementById(PANEL_ID)?.remove();
    const panel = document.createElement("section");
    panel.id = PANEL_ID;
    panel.innerHTML = `
      <div class="gazette-raw-reader-header">
        <strong>Gazette Ham Metin</strong>
        <div>
          <button type="button" data-summary>Özet</button>
          <button type="button" data-clickbait>Clickbait?</button>
          <button type="button" data-save>Gazette'e Kaydet</button>
          <button type="button" data-copy>Kopyala</button>
          <button type="button" data-close>Kapat</button>
        </div>
      </div>
      <textarea readonly></textarea>
      <div class="gazette-raw-reader-status"></div>
    `;
    const style = document.createElement("style");
    style.textContent = `
      #${PANEL_ID} {
        position: fixed; inset: 24px 24px 24px auto; z-index: 2147483647;
        width: min(560px, calc(100vw - 48px)); background: #fff; color: #111827;
        border: 1px solid #cfd8e3; box-shadow: 0 18px 48px rgba(15,23,42,.28);
        font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      }
      #${PANEL_ID} .gazette-raw-reader-header {
        display: flex; align-items: center; justify-content: space-between; gap: 12px;
        padding: 12px 14px; background: #1f4f8f; color: #fff;
      }
      #${PANEL_ID} button {
        margin-left: 8px; border: 0; padding: 7px 10px; cursor: pointer;
        background: #eef4ff; color: #173c6e; font-weight: 700;
      }
      #${PANEL_ID} textarea {
        width: 100%; height: calc(100vh - 130px); border: 0; resize: none;
        box-sizing: border-box; padding: 16px; font: 15px/1.55 Georgia, serif;
        color: #111827; background: #fff;
      }
      #${PANEL_ID} .gazette-raw-reader-status {
        padding: 8px 12px; border-top: 1px solid #e5e7eb; color: #475467; font: 12px system-ui;
      }
    `;
    panel.appendChild(style);
    document.documentElement.appendChild(panel);
    const textarea = panel.querySelector("textarea");
    const status = panel.querySelector(".gazette-raw-reader-status");
    textarea.value = extractRawText() || "Bu sayfada çıkarılabilir haber metni bulunamadı.";
    panel.querySelector("[data-close]").addEventListener("click", () => panel.remove());
    panel.querySelector("[data-copy]").addEventListener("click", async () => {
      await navigator.clipboard.writeText(textarea.value).catch(() => {});
      status.textContent = "Metin kopyalandı.";
    });
    panel.querySelector("[data-summary]").addEventListener("click", () => {
      const sentences = textarea.value.split(/(?<=[.!?])\s+/).map(clean).filter((item) => item.length > 40);
      textarea.value = sentences.slice(0, 5).map((item, index) => `${index + 1}. ${item}`).join("\n\n") || textarea.value;
      status.textContent = "Yerel 5 maddelik özet çıkarıldı.";
    });
    panel.querySelector("[data-clickbait]").addEventListener("click", () => {
      const text = textarea.value.toLocaleLowerCase("tr-TR");
      const patterns = ["son dakika", "mi oldu", "nerede oldu", "işte", "şoke", "inanamadı", "son depremler"];
      const hits = patterns.filter((pattern) => text.includes(pattern));
      status.textContent = hits.length ? `Şüpheli clickbait sinyali: ${hits.join(", ")}` : "Belirgin clickbait sinyali yok.";
    });
    panel.querySelector("[data-save]").addEventListener("click", () => {
      const saved = JSON.parse(localStorage.getItem("gazette_saved_pages") || "[]");
      saved.push({ title: document.title, url: location.href, text: textarea.value, savedAt: new Date().toISOString() });
      localStorage.setItem("gazette_saved_pages", JSON.stringify(saved.slice(-100)));
      status.textContent = "Sayfa extension yerel kaydına eklendi.";
    });
  };

  chrome.runtime.onMessage.addListener((message) => {
    if (message?.type === "GAZETTE_SHOW_RAW_TEXT") showPanel();
  });

  const params = new URLSearchParams(window.location.search);
  if (params.get("gazette_raw") === "1") {
    window.setTimeout(showPanel, 900);
  }
})();
