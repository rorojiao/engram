// Google Drive API helper - TODO: implement OAuth2 flow + file upload
// Will use chrome.identity.getAuthToken() for authentication
const DriveAPI = {
  async uploadSession(session, token) {
    const metadata = {
      name: `engram_${session.platform}_${Date.now()}.json`,
      mimeType: 'application/json',
      parents: ['appDataFolder'],
    };

    const form = new FormData();
    form.append('metadata', new Blob([JSON.stringify(metadata)], { type: 'application/json' }));
    form.append('file', new Blob([JSON.stringify(session)], { type: 'application/json' }));

    const response = await fetch('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    });

    return response.json();
  }
};
