import { afterEach, describe, expect, it, vi } from "vitest";
import { getApiHealth } from "./health";

describe("API health", () => {
  afterEach(() => vi.useRealTimers());

  it("checks the readiness contract without caching", async () => {
    const fetcher: typeof fetch = async (input, init) => {
      expect(String(input)).toBe("http://localhost:8000/health/ready");
      expect(init?.cache).toBe("no-store");
      expect(init?.signal).toBeInstanceOf(AbortSignal);
      return Response.json({ status: "ok", service: "sentinel-api" });
    };
    expect(await getApiHealth("http://localhost:8000", fetcher)).toBe(
      "healthy",
    );
  });

  it.each([
    new Response(null, { status: 503 }),
    Response.json({ status: "ok", service: "sentinel-api" }, { status: 201 }),
    Response.json({ status: "ok" }),
    Response.json(null),
    new Response("invalid json"),
  ])("reports unsuccessful or malformed responses", async (response) => {
    expect(
      await getApiHealth("http://localhost:8000", async () => response),
    ).toBe("unavailable");
  });

  it("handles network failures", async () => {
    expect(
      await getApiHealth("http://localhost:8000", async () => {
        throw new Error("Connection failed");
      }),
    ).toBe("unavailable");
  });

  it("cancels a pending request after three seconds", async () => {
    vi.useFakeTimers();
    let requestSignal: AbortSignal | null | undefined;
    const fetcher: typeof fetch = (_input, init) => {
      requestSignal = init?.signal;
      return new Promise((_resolve, reject) => {
        requestSignal?.addEventListener(
          "abort",
          () => reject(requestSignal?.reason),
          {
            once: true,
          },
        );
      });
    };
    const result = getApiHealth("http://127.0.0.1:8000", fetcher);
    await vi.advanceTimersByTimeAsync(2999);
    expect(requestSignal?.aborted).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    expect(requestSignal?.aborted).toBe(true);
    expect(await result).toBe("unavailable");
    expect(vi.getTimerCount()).toBe(0);
  });

  it("clears the timeout when a request completes early", async () => {
    vi.useFakeTimers();
    await getApiHealth("http://127.0.0.1:8000", async () =>
      Response.json({ status: "ok", service: "sentinel-api" }),
    );
    expect(vi.getTimerCount()).toBe(0);
  });

  it("aborts an unsuccessful response without leaving a timer running", async () => {
    vi.useFakeTimers();
    let requestSignal: AbortSignal | null | undefined;
    const result = await getApiHealth(
      "http://127.0.0.1:8000",
      async (_input, init) => {
        requestSignal = init?.signal;
        return new Response("unread error body", { status: 503 });
      },
    );
    expect(result).toBe("unavailable");
    expect(requestSignal?.aborted).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
  });
});
