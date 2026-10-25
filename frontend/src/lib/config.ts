export const API_BASE = 
  process.env.NEXT_PUBLIC_API_URL || 
  (typeof window !== "undefined" && window.location.hostname === "localhost" 
    ? "http://localhost:8000" 
    : "");

export function getWsUrl(username: string, token: string): string {
  if (process.env.NEXT_PUBLIC_WS_URL) {
    const base = process.env.NEXT_PUBLIC_WS_URL.replace(/^http/, "ws");
    return `${base}/ws/${encodeURIComponent(username)}?token=${encodeURIComponent(token)}`;
  }

  if (typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.port === "3000" 
      ? `${window.location.hostname}:8000` 
      : window.location.host;
    return `${proto}//${host}/ws/${encodeURIComponent(username)}?token=${encodeURIComponent(token)}`;
  }

  return `ws://localhost:8000/ws/${encodeURIComponent(username)}?token=${encodeURIComponent(token)}`;
}

export function getAuthHeaders(token?: string): Record<string, string> {
  const tok = token || (typeof window !== "undefined" ? localStorage.getItem("couple_token") : null);
  const headers: Record<string, string> = {};
  if (tok) {
    headers["Authorization"] = `Bearer ${tok}`;
  }
  return headers;
}
