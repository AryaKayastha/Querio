const DEFAULT_API_BASE = "http://localhost:8000";
const API_BASE = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE).replace(/\/$/u, "");

export const sendChatMessage = async (query) => {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: query.trim() }),
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    const error = new Error(`Chat request failed with ${response.status}`);
    error.type = "http_error";
    error.details = detail;
    throw error;
  }

  return response.json();
};
