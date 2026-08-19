export const API_BASE = (process.env.REACT_APP_API_BASE_URL || '').replace(/\/$/, '');

export async function apiFetch(path, { token, headers, ...options } = {}) {
  const mergedHeaders = { ...headers };
  if (token) mergedHeaders.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers: mergedHeaders });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || data.message || '요청에 실패했습니다.');
  }

  return res.json();
}
