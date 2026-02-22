chrome.runtime.sendMessage({ action: 'list_sessions' }, (response) => {
  const container = document.getElementById('sessions-list');
  const sessions = response?.sessions || [];

  if (sessions.length === 0) {
    container.innerHTML = '<div class="empty">No sessions yet.<br>Visit a supported AI chat and click "🧠 Save to Engram"</div>';
    return;
  }

  container.innerHTML = sessions.slice(0, 20).map(s => `
    <div class="session">
      <div class="platform">${s.platform.toUpperCase()} · ${s.messages?.length || 0} messages</div>
      <div class="title">${s.title}</div>
    </div>
  `).join('');
});
