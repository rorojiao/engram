// 千问: chat.qwen.ai / tongyi.aliyun.com
(function() {
  const platform = 'qwen';
  const extractor = {
    getContainers(doc) {
      return doc.querySelectorAll('[class*="message"], [class*="Message"], [class*="chat-item"], [class*="bubble"]');
    }
  };

  function injectSnapshotButton() {
    if (document.getElementById('engram-btn-qwen')) return;
    const btn = document.createElement('button');
    btn.id = 'engram-btn-qwen';
    btn.textContent = '🧠 保存到 Engram';
    btn.style.cssText = 'position:fixed;bottom:80px;right:20px;background:#6366f1;color:white;border:none;padding:8px 14px;border-radius:8px;cursor:pointer;font-size:13px;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,0.3);';
    btn.onclick = () => {
      const messages = window.EngramExtractor.extract(extractor);
      if (messages.length > 0) {
        window.EngramExtractor.saveToBackground(messages, platform);
        btn.textContent = '✅ 已保存！';
        setTimeout(() => { btn.textContent = '🧠 保存到 Engram'; }, 2000);
      }
    };
    document.body.appendChild(btn);
  }

  setTimeout(injectSnapshotButton, 2000);
  new MutationObserver(injectSnapshotButton).observe(document.body, {childList: true, subtree: true});
})();
