// Claude: claude.ai
(function() {
  const platform = 'claude';
  const extractor = {
    getContainers(doc) {
      return doc.querySelectorAll('[class*="Message"], [class*="message"], [class*="conversation"]');
    }
  };

  function injectSnapshotButton() {
    if (document.getElementById('engram-btn')) return;
    const btn = document.createElement('button');
    btn.id = 'engram-btn';
    btn.textContent = '🧠 Save to Engram';
    btn.style.cssText = 'position:fixed;bottom:80px;right:20px;background:#6366f1;color:white;border:none;padding:8px 14px;border-radius:8px;cursor:pointer;font-size:13px;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,0.3);';
    btn.onclick = () => {
      const messages = window.EngramExtractor.extract(extractor);
      if (messages.length > 0) {
        window.EngramExtractor.saveToBackground(messages, platform);
        btn.textContent = '✅ Saved!';
        setTimeout(() => { btn.textContent = '🧠 Save to Engram'; }, 2000);
      }
    };
    document.body.appendChild(btn);
  }

  setTimeout(injectSnapshotButton, 2000);
  new MutationObserver(injectSnapshotButton).observe(document.body, {childList: true, subtree: true});
})();
