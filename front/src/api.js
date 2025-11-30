const isBrowser = typeof window !== 'undefined';
const isLocalhost =
  isBrowser && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

const API_BASE =
  import.meta.env.VITE_API_URL ??
  (isLocalhost ? 'http://localhost:8001' : 'http://back:8001');
const CV_API_BASE =
  import.meta.env.VITE_CV_API_URL ??
  (isLocalhost ? 'http://localhost:8000' : 'http://cv:8000');

async function request(path, options = {}, baseUrl = API_BASE) {
  const { allowedStatuses = [], ...fetchOptions } = options;
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(fetchOptions.headers ?? {}) },
    ...fetchOptions
  });

  if (!response.ok && !allowedStatuses.includes(response.status)) {
    let message;
    try {
      const payload = await response.json();
      message = typeof payload?.detail === 'string' ? payload.detail : JSON.stringify(payload);
    } catch {
      message = await response.text();
    }
    const error = new Error(message || response.statusText);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  try {
    return await response.json();
  } catch (error) {
    if (!response.ok && allowedStatuses.includes(response.status)) {
      return null;
    }
    throw new Error('Не удалось разобрать ответ сервера');
  }
}

export const api = {
  startSegment() {
    return request('/segment/start', { method: 'POST', allowedStatuses: [409] });
  },
  fetchSegment(id = 0) {
    return request(
      '/segment',
      {
        method: 'POST',
        body: JSON.stringify({ id })
      },
      CV_API_BASE
    );
  }
};
