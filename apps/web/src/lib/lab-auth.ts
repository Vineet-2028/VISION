import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
export const LAB_COOKIE = "vision_lab";
export function configured(secret: string | undefined): secret is string {
  return typeof secret === "string" && secret.length >= 32;
}
export function equalSecret(a: string, b: string): boolean {
  const digest = (s: string) =>
    createHmac("sha256", "vision-secret-compare").update(s).digest();
  return timingSafeEqual(digest(a), digest(b));
}
export function issueLabSession(secret: string, now = Date.now()): string {
  if (!configured(secret)) throw new Error("Lab disabled");
  const payload = `${now + 8 * 3600_000}.${randomBytes(16).toString("hex")}`;
  return `${payload}.${createHmac("sha256", secret).update(payload).digest("hex")}`;
}
export function validLabSession(
  value: string | undefined,
  secret: string | undefined,
  now = Date.now(),
): boolean {
  if (
    !configured(secret) ||
    !value ||
    !/^\d{13}\.[a-f0-9]{32}\.[a-f0-9]{64}$/.test(value)
  )
    return false;
  const [expiry, nonce, signature] = value.split(".");
  const expected = createHmac("sha256", secret)
    .update(`${expiry}.${nonce}`)
    .digest("hex");
  return (
    Number(expiry) > now &&
    Number(expiry) <= now + 8 * 3600_000 &&
    equalSecret(signature!, expected)
  );
}
export function labCookie(header: string | null): string | undefined {
  const values = (header ?? "")
    .split(";")
    .map((x) => x.trim())
    .filter((x) => x.startsWith(`${LAB_COOKIE}=`));
  return values.length === 1
    ? values[0]!.slice(LAB_COOKIE.length + 1)
    : undefined;
}
