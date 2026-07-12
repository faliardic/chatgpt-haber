chrome.action.onClicked.addListener(async (tab) => {
  if (!tab.id) return;
  await chrome.tabs.sendMessage(tab.id, { type: "GAZETTE_SHOW_RAW_TEXT" }).catch(() => {});
});
