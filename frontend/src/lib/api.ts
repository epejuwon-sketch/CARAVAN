const API_BASE = "";

export function safeGetStorage(key: string): string | null {
  try {
    return typeof window !== "undefined" && window.localStorage ? window.localStorage.getItem(key) : null;
  } catch {
    return null;
  }
}

export function safeSetStorage(key: string, value: string): void {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem(key, value);
    }
  } catch {
    // Safari private mode protection
  }
}

export function safeRemoveStorage(key: string): void {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.removeItem(key);
    }
  } catch {
    // Safari private mode protection
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = safeGetStorage("caravan_token");
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errMessage = `HTTP error ${response.status}`;
    try {
      const errData = await response.json();
      errMessage = errData.detail || errMessage;
    } catch {
      // ignore
    }
    throw new Error(errMessage);
  }

  return response.json() as Promise<T>;
}
