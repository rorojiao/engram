// Unified session format for Engram
const SessionFormat = {
  normalize(rawSession) {
    return {
      version: '0.1.0',
      platform: rawSession.platform || 'unknown',
      url: rawSession.url || '',
      title: rawSession.title || 'Untitled',
      capturedAt: rawSession.capturedAt || new Date().toISOString(),
      messages: (rawSession.messages || []).map(m => ({
        role: m.role,
        content: m.content,
        timestamp: m.timestamp || '',
      })),
      messageCount: rawSession.messages?.length || 0,
    };
  }
};
