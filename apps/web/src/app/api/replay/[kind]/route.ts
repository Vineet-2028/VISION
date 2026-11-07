import {
  replayFrame,
  replayIndex,
  replayStream,
  reviewPacket,
  replayVideo,
} from "../../../../lib/replay-store";
import { labCookie, validLabSession } from "../../../../lib/lab-auth";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(
  request: Request,
  context: { params: Promise<{ kind: string }> },
) {
  if (
    !validLabSession(
      labCookie(request.headers.get("cookie")),
      process.env.VISION_LAB_SECRET,
    )
  )
    return new Response(null, {
      status: 401,
      headers: { "Cache-Control": "no-store" },
    });
  if (
    !["localhost", "127.0.0.1", "[::1]"].includes(
      new URL(request.url).hostname,
    ) ||
    request.headers.get("sec-fetch-site") === "cross-site"
  )
    return new Response(null, { status: 403 });
  try {
    const { kind } = await context.params;
    if (kind === "review")
      return Response.json(await reviewPacket(), {
        headers: { "Cache-Control": "no-store" },
      });
    if (kind === "manifest") {
      const { manifest, entries } = await replayIndex();
      return Response.json(
        {
          manifest,
          timestamps: entries.map((e) => e.pts),
          playback_mode: "OFFLINE_REPLAY",
        },
        { headers: { "Cache-Control": "no-store" } },
      );
    }
    if (kind === "frame") {
      const raw = new URL(request.url).searchParams.get("pts");
      const pts = raw === null ? NaN : Number(raw);
      if (!Number.isSafeInteger(pts) || pts < 0)
        return Response.json({ error: "Invalid PTS" }, { status: 400 });
      return Response.json(await replayFrame(pts), {
        headers: { "Cache-Control": "no-store" },
      });
    }
    if (kind === "video") {
      if (process.env.VISION_LAB_MEDIA_ENABLED !== "1")
        return new Response("Media access is disabled by the operator", {
          status: 403,
        });
      const video = await replayVideo();
      const range = request.headers.get("range");
      let start = 0,
        end = video.size - 1;
      if (range) {
        const match = /^bytes=(\d+)-(\d*)$/.exec(range);
        if (!match) return new Response(null, { status: 416 });
        start = Number(match[1]);
        end = match[2]
          ? Number(match[2])
          : Math.min(start + 4_000_000 - 1, video.size - 1);
        if (
          !Number.isSafeInteger(start) ||
          !Number.isSafeInteger(end) ||
          start > end ||
          end >= video.size
        )
          return new Response(null, { status: 416 });
      }
      const stream = await replayStream(video, start, end);
      return new Response(stream, {
        status: range ? 206 : 200,
        headers: {
          "Content-Type": "video/mp4",
          "Accept-Ranges": "bytes",
          "Content-Length": String(end - start + 1),
          ...(range
            ? { "Content-Range": `bytes ${start}-${end}/${video.size}` }
            : {}),
          "Cache-Control": "no-store",
        },
      });
    }
    return new Response(null, { status: 404 });
  } catch {
    return Response.json(
      {
        error:
          "Local replay unavailable or invalid. Check the operator's configured evidence files.",
      },
      { status: 503 },
    );
  }
}
