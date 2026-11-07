import {
  configured,
  equalSecret,
  issueLabSession,
  LAB_COOKIE,
} from "../../../../lib/lab-auth";
export async function POST(request: Request) {
  const url = new URL(request.url);
  // Next may normalize request.url to its configured bind hostname. Compare the
  // actual Host header, and keep this operator-only endpoint on loopback hosts.
  const host = request.headers.get("host") ?? url.host;
  const origin = `${url.protocol}//${host}`;
  if (
    !/^(localhost|127\.0\.0\.1|\[::1\])(:\d{1,5})?$/.test(host) ||
    request.headers.get("origin") !== origin ||
    Number(request.headers.get("content-length") ?? 0) > 1024
  )
    return new Response(null, { status: 403 });
  const secret = process.env.VISION_LAB_SECRET;
  if (!configured(secret))
    return new Response(
      "Lab is disabled. Configure the operator secret locally.",
      { status: 503 },
    );
  const reader = request.body?.getReader();
  if (!reader) return new Response(null, { status: 400 });
  let raw = "";
  let bytes = 0;
  const decoder = new TextDecoder();
  try {
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      bytes += chunk.value.byteLength;
      if (bytes > 1024) {
        await reader.cancel();
        return new Response(null, { status: 413 });
      }
      raw += decoder.decode(chunk.value, { stream: true });
    }
    raw += decoder.decode();
  } finally {
    reader.releaseLock();
  }
  if (
    raw.length > 1024 ||
    !equalSecret(new URLSearchParams(raw).get("secret") ?? "", secret)
  )
    return new Response("Invalid credentials", { status: 401 });
  return new Response(null, {
    status: 303,
    headers: {
      Location: "/lab",
      "Cache-Control": "no-store",
      "Set-Cookie": `${LAB_COOKIE}=${issueLabSession(secret)}; Path=/; HttpOnly; SameSite=Strict; Max-Age=28800${url.protocol === "https:" ? "; Secure" : ""}`,
    },
  });
}
