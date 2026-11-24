import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";
import { createHash } from "node:crypto";
import { labCookie, validLabSession } from "../../../lib/lab-auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function validEvent(value: unknown): boolean {
  if (!value || typeof value !== "object") return false;
  const event = value as Record<string, unknown>;
  if (event.object_diagnostics != null) {
    if (typeof event.object_diagnostics !== "object") return false;
    const objects = (event.object_diagnostics as Record<string, unknown>)
      .objects;
    if (objects !== undefined && !Array.isArray(objects)) return false;
  }
  if (event.detector_diagnostics == null) return true;
  if (typeof event.detector_diagnostics !== "object") return false;
  const detector = event.detector_diagnostics as Record<string, unknown>;
  for (const key of ["accepted_samples", "rejected_samples"]) {
    const samples = detector[key];
    if (samples === undefined) continue;
    if (!Array.isArray(samples) || samples.length > 32) return false;
    for (const sample of samples) {
      if (!sample || typeof sample !== "object") return false;
      const box = sample.original_box;
      if (
        box !== null &&
        (!Array.isArray(box) ||
          box.length !== 4 ||
          !box.every(
            (coordinate: unknown) =>
              typeof coordinate === "number" && Number.isFinite(coordinate),
          ))
      )
        return false;
    }
  }
  return true;
}

export async function GET(request: Request) {
  const headers = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
  };
  if (
    !validLabSession(
      labCookie(request.headers.get("cookie")),
      process.env.VISION_LAB_SECRET,
    )
  ) {
    return new Response(null, { status: 401, headers });
  }
  const url = new URL(request.url);
  if (
    !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname) ||
    request.headers.get("sec-fetch-site") === "cross-site"
  ) {
    return new Response(null, { status: 403, headers });
  }
  const configured = process.env.VISION_DIAGNOSTIC_CASE;
  if (!configured)
    return Response.json(
      { error: "No diagnostic case configured" },
      { status: 404, headers },
    );
  const root = resolve(configured);
  async function bounded(name: string, limit: number) {
    const path = resolve(root, name);
    if ((await stat(path)).size > limit) throw new Error("Oversized artifact");
    const bytes = await readFile(path);
    if (bytes.length > limit) throw new Error("Oversized artifact");
    return bytes;
  }
  try {
    const index = JSON.parse((await bounded("index.json", 65536)).toString());
    if (
      index.schema !== "vision.field.case.v1" ||
      typeof index.session_id !== "string" ||
      index.session_id.length < 1 ||
      index.session_id.length > 256 ||
      !Array.isArray(index.frames) ||
      index.frames.length > 24 ||
      index.frames.some(
        (frame: { sequence?: unknown; camera_ns?: unknown }, i: number) =>
          !frame ||
          !Number.isSafeInteger(frame.sequence) ||
          Number(frame.sequence) < 0 ||
          typeof frame.camera_ns !== "string" ||
          !/^\d{1,19}$/.test(frame.camera_ns) ||
          (i > 0 &&
            (Number(frame.sequence) <= index.frames[i - 1].sequence ||
              BigInt(frame.camera_ns) <=
                BigInt(index.frames[i - 1].camera_ns))),
      )
    )
      throw new Error("Invalid case");
    const selected = url.searchParams.get("frame");
    if (selected === null) return Response.json(index, { headers });
    if (
      !/^(0|[1-9][0-9]?)$/.test(selected) ||
      Number(selected) >= index.frames.length
    )
      return new Response(null, { status: 400, headers });
    const packet = JSON.parse(
      (await bounded(`${selected}.json`, 2_000_000)).toString(),
    );
    if (
      packet.sequence !== index.frames[Number(selected)].sequence ||
      packet.camera_ns !== index.frames[Number(selected)].camera_ns ||
      !Number.isInteger(packet.width) ||
      packet.width < 1 ||
      packet.width > 1280 ||
      !Number.isInteger(packet.height) ||
      packet.height < 1 ||
      packet.height > 1280 ||
      !Array.isArray(packet.recorded_events) ||
      !packet.recorded_events.every(validEvent) ||
      (packet.detector_source_events !== undefined &&
        (!Array.isArray(packet.detector_source_events) ||
          packet.detector_source_events.length > 16 ||
          !packet.detector_source_events.every(validEvent))) ||
      typeof packet.jpeg_sha256 !== "string" ||
      !/^[a-f0-9]{64}$/.test(packet.jpeg_sha256)
    )
      throw new Error("Frame identity mismatch");
    if (url.searchParams.get("media") !== "1") {
      try {
        const replay = JSON.parse(
          (await bounded("detector-replay.json", 4_000_000)).toString(),
        );
        const recomputed = replay.frames?.[Number(selected)];
        if (
          replay.schema !== "vision.field.input-replay.v1" ||
          replay.session_id !== index.session_id ||
          recomputed?.sequence !== packet.sequence ||
          recomputed?.camera_ns !== packet.camera_ns ||
          recomputed?.jpeg_sha256 !== packet.jpeg_sha256
        )
          throw new Error("Recomputed identity mismatch");
        packet.recomputed_output = recomputed.recomputed_output;
        packet.recomputation_provenance = replay.recomputation_provenance;
      } catch (error) {
        if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
      }
      return Response.json(packet, { headers });
    }
    if (process.env.VISION_LAB_MEDIA_ENABLED !== "1")
      return new Response(null, { status: 403, headers });
    const image = await bounded(`${selected}.jpg`, 512000);
    if (createHash("sha256").update(image).digest("hex") !== packet.jpeg_sha256)
      throw new Error("Frame checksum mismatch");
    return new Response(new Uint8Array(image), {
      headers: { ...headers, "Content-Type": "image/jpeg" },
    });
  } catch {
    return Response.json(
      { error: "Diagnostic artifact missing or invalid" },
      { status: 422, headers },
    );
  }
}
