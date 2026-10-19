/** Server-only configuration; callers must never forward environment values to clients. */
export function getApiBaseUrl(environment: {
  NODE_ENV?: string;
  API_BASE_URL?: string;
}): string {
  const value = environment.API_BASE_URL;
  if (value === undefined && environment.NODE_ENV !== "production") {
    return "http://127.0.0.1:8000";
  }
  if (value === undefined || value.trim() === "") {
    throw new Error("API_BASE_URL is required and must be an HTTP(S) URL.");
  }

  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error("API_BASE_URL must be a valid HTTP(S) URL.");
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error("API_BASE_URL must use HTTP or HTTPS.");
  }
  if (url.username || url.password) {
    throw new Error("API_BASE_URL must not contain credentials.");
  }
  if (url.pathname !== "/" || url.search || url.hash) {
    throw new Error(
      "API_BASE_URL must be an origin without a path, query, or fragment.",
    );
  }
  return url.href;
}
