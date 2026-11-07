import { afterEach, describe, expect, it, vi } from "vitest";
import { POST } from "../app/api/lab/login/route";

afterEach(() => vi.unstubAllEnvs());
const request = (body: string, origin = "http://localhost") =>
  new Request("http://localhost/api/lab/login", {
    method: "POST",
    headers: { origin },
    body,
  });
describe("Lab login boundary", () => {
  it("fails closed without configuration and rejects cross-origin requests", async () => {
    vi.stubEnv("VISION_LAB_SECRET", "");
    expect((await POST(request("secret=x"))).status).toBe(503);
    expect(
      (await POST(request("secret=x", "https://attacker.invalid"))).status,
    ).toBe(403);
  });
  it("bounds a body without content-length before authenticating", async () => {
    vi.stubEnv("VISION_LAB_SECRET", "a".repeat(48));
    expect((await POST(request("x".repeat(1025)))).status).toBe(413);
    expect((await POST(request("secret=wrong"))).status).toBe(401);
  });
  it("issues a scoped HttpOnly cookie only for a valid secret", async () => {
    vi.stubEnv("VISION_LAB_SECRET", "a".repeat(48));
    const response = await POST(request(`secret=${"a".repeat(48)}`));
    expect(response.status).toBe(303);
    expect(response.headers.get("set-cookie")).toContain(
      "HttpOnly; SameSite=Strict",
    );
    expect(response.headers.get("cache-control")).toBe("no-store");
  });
  it("uses the actual loopback Host when Next normalizes the bind hostname", async () => {
    vi.stubEnv("VISION_LAB_SECRET", "a".repeat(48));
    const actual = new Request("http://localhost:3010/api/lab/login", {
      method: "POST",
      headers: { host: "127.0.0.1:3010", origin: "http://127.0.0.1:3010" },
      body: `secret=${"a".repeat(48)}`,
    });
    expect((await POST(actual)).status).toBe(303);
    expect(
      (
        await POST(
          new Request("http://localhost/api/lab/login", {
            method: "POST",
            headers: {
              host: "attacker.invalid",
              origin: "http://attacker.invalid",
            },
            body: "secret=x",
          }),
        )
      ).status,
    ).toBe(403);
  });
});
