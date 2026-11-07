import { expect, test } from "vitest";
import { issueLabSession, validLabSession, labCookie } from "./lab-auth";
const secret = "test-only-".repeat(5);
test("Lab fails closed, rejects tampering, expiry and key rotation", () => {
  const now = 1_800_000_000_000;
  const cookie = issueLabSession(secret, now);
  expect(validLabSession(cookie, secret, now)).toBe(true);
  expect(validLabSession(cookie, undefined, now)).toBe(false);
  expect(validLabSession(cookie, secret + "rotated", now)).toBe(false);
  expect(validLabSession(cookie + "a", secret, now)).toBe(false);
  expect(validLabSession(cookie, secret, now + 8 * 3600_000)).toBe(false);
  expect(labCookie("vision_lab=a; vision_lab=b")).toBeUndefined();
});
