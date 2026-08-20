const DEFAULT_API_BASE = "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 15_000;

export const MAX_QUERY_LENGTH = 2000; // Client-side safeguard until a server-side limit is enforced.

const API_BASE = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE).replace(/\/$/, "");

export class BackendApiError extends Error {
  constructor(type, message, options = {}) {
    super(message);
    this.name = "BackendApiError";
    this.type = type;
    this.status = options.status;
    this.details = options.details;
  }
}

const normalizeQuery = (query) => {
  if (typeof query !== "string") {
    return "";
  }

  return query.replace(/\s+/gu, " ").trim();
};

const createTimeoutSignal = (timeoutMs) => {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  return { controller, timeoutId };
};

export const sendChatMessage = async (query) => {
  const normalizedQuery = normalizeQuery(query);

  if (normalizedQuery.length === 0) {
    throw new BackendApiError("empty_query", "Please enter a message before sending.");
  }

  if (normalizedQuery.length > MAX_QUERY_LENGTH) {
    throw new BackendApiError(
      "query_too_long",
      `Message is too long. Maximum allowed length is ${MAX_QUERY_LENGTH} characters.`
    );
  }

  const { controller, timeoutId } = createTimeoutSignal(REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query: normalizedQuery }),
      signal: controller.signal,
    });

    if (!response.ok) {
      let responseBody = "";

      try {
        responseBody = await response.text();
      } catch {
        responseBody = "";
      }

      throw new BackendApiError(
        "http_error",
        `Chat request failed with ${response.status}${responseBody ? `: ${responseBody}` : ""}`,
        {
          status: response.status,
          details: responseBody,
        }
      );
    }

    return response.json();
  } catch (error) {
    if (error && error.name === "AbortError") {
      throw new BackendApiError(
        "timeout",
        "The chat request timed out after 15 seconds. Please try again."
      );
    }

    if (error instanceof BackendApiError) {
      throw error;
    }

    throw new BackendApiError(
      "network_error",
      "Network error while contacting the Querio backend."
    );
  } finally {
    window.clearTimeout(timeoutId);
  }
};

export const checkHealth = async () => {
  const { controller, timeoutId } = createTimeoutSignal(REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE}/health`, {
      method: "GET",
      signal: controller.signal,
    });

    if (!response.ok) {
      return false;
    }

    const body = await response.json();
    return body && body.status === "ok";
  } catch {
    return false;
  } finally {
    window.clearTimeout(timeoutId);
  }
};
