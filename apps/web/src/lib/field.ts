export const FIELD_PROTOCOL = "VISION_FIELD_PROTOCOL_V1";
export function localGateway(value: string): string {
  const url = new URL(value);
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== "/"
  )
    throw new Error("Use a local gateway origin without a path");
  const h = url.hostname;
  const parts = h.split(".").map(Number);
  const privateIp =
    parts.length === 4 &&
    parts.every((n) => Number.isInteger(n) && n >= 0 && n <= 255) &&
    (parts[0] === 10 ||
      parts[0] === 127 ||
      (parts[0] === 192 && parts[1] === 168) ||
      (parts[0] === 172 && parts[1]! >= 16 && parts[1]! <= 31));
  if (h !== "localhost" && h !== "[::1]" && !privateIp)
    throw new Error("Only loopback or private LAN addresses are allowed");
  const loopback =
    h === "localhost" || h === "[::1]" || (privateIp && parts[0] === 127);
  if (!loopback && url.protocol !== "https:")
    throw new Error("LAN connections require HTTPS");
  return url.origin;
}
export function currentAge(
  baseAgeNs: string,
  receivedAtMs: number,
  nowMs: number,
  rttMs: number,
): number {
  if (
    !/^\d{1,19}$/.test(baseAgeNs) ||
    ![receivedAtMs, nowMs, rttMs].every(Number.isFinite) ||
    nowMs < receivedAtMs ||
    rttMs < 0
  )
    throw new Error("Invalid clock metadata");
  return Number(BigInt(baseAgeNs)) / 1e6 + (nowMs - receivedAtMs) + rttMs;
}
