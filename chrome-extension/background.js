// Service worker - 接收来自 content script 的会话数据
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'save_session') {
    const session = msg.session;
    const key = `engram_session_${Date.now()}`;
    chrome.storage.local.set({ [key]: session }, () => {
      console.log('[Engram] Session saved locally:', session.title);
    });
    sendResponse({ status: 'saved', key });
  }

  if (msg.action === 'list_sessions') {
    chrome.storage.local.get(null, (items) => {
      const sessions = Object.entries(items)
        .filter(([k]) => k.startsWith('engram_session_'))
        .map(([k, v]) => ({ key: k, ...v }))
        .sort((a, b) => new Date(b.capturedAt) - new Date(a.capturedAt));
      sendResponse({ sessions });
    });
    return true;
  }
});
