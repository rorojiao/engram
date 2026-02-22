// 不依赖 class 名，用结构特征提取消息
window.EngramExtractor = {
  extractByAria(doc) {
    const byRole = doc.querySelectorAll('[data-role="user"], [data-role="assistant"], [data-message-author-role]');
    if (byRole.length > 0) {
      return Array.from(byRole).map(el => ({
        role: el.dataset.role || el.dataset.messageAuthorRole,
        content: el.innerText.trim(),
        timestamp: el.dataset.timestamp || '',
      })).filter(m => m.content.length > 5);
    }
    return null;
  },

  extractByStructure(containers) {
    const messages = [];
    let lastRole = null;
    for (const el of containers) {
      const text = el.innerText.trim();
      if (text.length < 5) continue;
      const style = window.getComputedStyle(el);
      const isRightAligned = style.justifyContent === 'flex-end' ||
                              style.marginLeft === 'auto' ||
                              el.className.toLowerCase().includes('user') ||
                              el.className.toLowerCase().includes('human');
      const role = isRightAligned ? 'user' : 'assistant';
      if (role === lastRole && messages.length > 0) {
        messages[messages.length - 1].content += '\n' + text;
      } else {
        messages.push({ role, content: text, timestamp: '' });
        lastRole = role;
      }
    }
    return messages;
  },

  extract(platformExtractor) {
    const byAria = this.extractByAria(document);
    if (byAria && byAria.length >= 2) return byAria;
    const containers = platformExtractor.getContainers(document);
    return this.extractByStructure(containers);
  },

  saveToBackground(messages, platform) {
    const firstUser = messages.find(m => m.role === 'user');
    chrome.runtime.sendMessage({
      action: 'save_session',
      session: {
        platform,
        url: window.location.href,
        title: firstUser ? firstUser.content.slice(0, 80) : document.title,
        messages,
        capturedAt: new Date().toISOString(),
      }
    });
  }
};
