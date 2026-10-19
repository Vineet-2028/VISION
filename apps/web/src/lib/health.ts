export type ApiHealth = "healthy" | "unavailable";

export async function getApiHealth(
  baseUrl: string,
  fetcher: typeof fetch = fetch,
): Promise<ApiHealth> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 3000);
  try {
    const response = await fetcher(new URL("/health/ready", baseUrl), {
      cache: "no-store",
      signal: controller.signal,
    });
    if (response.status !== 200) return "unavailable";
    const body: unknown = await response.json();
    return typeof body === "object" &&
      body !== null &&
      "status" in body &&
      body.status === "ok" &&
      "service" in body &&
      body.service === "sentinel-api"
      ? "healthy"
      : "unavailable";
  } catch {
    return "unavailable";
  } finally {
    // Abort unread error bodies as well as timed-out requests to release the connection.
    controller.abort();
    clearTimeout(timeout);
  }
}
