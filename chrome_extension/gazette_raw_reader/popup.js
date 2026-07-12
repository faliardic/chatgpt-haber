document.getElementById("show").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.id) {
    await chrome.tabs.sendMessage(tab.id, { type: "GAZETTE_SHOW_RAW_TEXT" }).catch(() => {});
  }
  window.close();
});
