import { describe, expect, it } from "vitest";
import { getApiBaseUrl } from "./server-config";

describe("server configuration", () => {
  it.each(["http://127.0.0.1:8000", "https://api.example.com"])(
    "accepts %s",
    (value) => {
      expect(
        getApiBaseUrl({ NODE_ENV: "production", API_BASE_URL: value }),
      ).toBe(`${value}/`);
    },
  );

  it.each(["development", "test"])("defaults to loopback in %s", (mode) => {
    expect(getApiBaseUrl({ NODE_ENV: mode })).toBe("http://127.0.0.1:8000");
  });

  it("requires explicit production configuration", () => {
    expect(() => getApiBaseUrl({ NODE_ENV: "production" })).toThrow(
      "API_BASE_URL is required",
    );
  });

  it.each([
    "https://api.example.com/prefix",
    "https://api.example.com/?token=example",
    "https://api.example.com/#fragment",
  ])("rejects URL components that health requests would discard", (value) => {
    expect(() => getApiBaseUrl({ API_BASE_URL: value })).toThrow(
      "API_BASE_URL must be an origin without a path, query, or fragment.",
    );
  });

  it.each(["", " ", "not-a-url", "ftp://example.com", "file:///tmp/api"])(
    "rejects invalid configuration %j",
    (value) => {
      expect(() => getApiBaseUrl({ API_BASE_URL: value })).toThrow(
        /API_BASE_URL/,
      );
    },
  );

  it("rejects embedded credentials without including them in errors", () => {
    expect(() =>
      getApiBaseUrl({
        API_BASE_URL: "https://example-user:example-password@example.com",
      }),
    ).toThrow("API_BASE_URL must not contain credentials.");
  });
});
