import { createReadStream } from "node:fs";
import { createHash } from "node:crypto";
import { open, readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";
import { indexAtOrBefore, object, parseFrame } from "./replay";
import { parseReviewPacket } from "./human-review";

const directory = resolve(
  process.env.VISION_REPLAY_DIR ??
    "../../benchmark-results/v02/alpha-full-realtime-01",
);
const path = resolve(directory, "frames.jsonl");
const MAX_LINE = 4_000_000;
export async function reviewPacket() {
  const source = await readFile(
    resolve(
      process.env.VISION_REVIEW_PACKET ??
        "../../benchmark-results/v0-rescue/human-review/manifest.json",
    ),
  );
  const raw = object(JSON.parse(source.toString("utf8")));
  const manifest = object(
    JSON.parse(await readFile(resolve(directory, "manifest.json"), "utf8")),
  );
  if (manifest.source_sha256 !== raw.source_sha256)
    throw new Error("Review source differs from replay");
  return parseReviewPacket({
    ...raw,
    packet_sha256: createHash("sha256").update(source).digest("hex"),
  });
}
type Entry = { pts: number; offset: number; bytes: number };
let cached: ReturnType<typeof buildIndex> | undefined;
async function buildIndex() {
  const manifest = object(
    JSON.parse(await readFile(resolve(directory, "manifest.json"), "utf8")),
  );
  if (manifest.trace_mode === "COMPACT_ALPHA_TRACE") {
    const tracePath = resolve(directory, "updates.jsonl");
    const info = await stat(tracePath);
    const sidecarPath = resolve(directory, "demo-index.json");
    if ((await stat(sidecarPath)).size > 8_000_000)
      throw new Error("Oversized replay index");
    const index = object(JSON.parse(await readFile(sidecarPath, "utf8")));
    if (
      manifest.status !== "COMPLETE" ||
      index.source_sha256 !== manifest.source_sha256 ||
      info.size !== index.size ||
      typeof index.mtime_ms !== "number" ||
      Math.abs(index.mtime_ms - info.mtimeMs) > 1 ||
      !Array.isArray(index.entries) ||
      index.entries.length !== object(manifest.trace_writer).rows ||
      index.entries.length > 100_000
    )
      throw new Error("Replay index differs from the measured trace");
    let offset = 0,
      previous = -1;
    const entries: Entry[] = index.entries.map((item) => {
      if (
        !Array.isArray(item) ||
        item.length !== 3 ||
        !item.every(Number.isSafeInteger)
      )
        throw new Error("Invalid replay index row");
      const [pts, start, bytes] = item;
      if (pts <= previous || start !== offset || bytes <= 0 || bytes > MAX_LINE)
        throw new Error("Invalid replay offsets");
      previous = pts;
      offset += bytes;
      return { pts, offset: start, bytes };
    });
    if (offset !== info.size) throw new Error("Incomplete trace index");
    return {
      entries,
      timestamps: entries.map((e) => e.pts),
      size: info.size,
      mtimeMs: info.mtimeMs,
      tracePath,
      alpha: true,
      manifest: {
        schema_version: 1,
        source_sha256: manifest.source_sha256,
        mode: manifest.mode,
        updates: entries.length,
        release: "VISION_CONTROLLED_ALPHA_V1",
      },
    };
  }
  const before = await stat(path);
  if (
    manifest.schema_version !== 1 ||
    !Number.isSafeInteger(manifest.updates) ||
    Number(manifest.updates) <= 0 ||
    Number(manifest.updates) > 100_000
  )
    throw new Error("Invalid replay manifest");
  const entries: Entry[] = [];
  let carry = Buffer.alloc(0),
    offset = 0,
    previous = -1;
  for await (const chunk of createReadStream(path, {
    highWaterMark: 64 * 1024,
  })) {
    carry = Buffer.concat([carry, chunk as Buffer]);
    let end: number;
    while ((end = carry.indexOf(10)) >= 0) {
      if (end > MAX_LINE || entries.length >= 100_000)
        throw new Error("Replay limit exceeded");
      const frame = parseFrame(
        JSON.parse(carry.subarray(0, end).toString("utf8")),
      );
      if (frame.frame.observation_ns <= previous)
        throw new Error("Nonmonotonic replay PTS");
      previous = frame.frame.observation_ns;
      entries.push({ pts: previous, offset, bytes: end });
      offset += end + 1;
      carry = carry.subarray(end + 1);
    }
    if (carry.length > MAX_LINE) throw new Error("Replay line limit exceeded");
  }
  if (carry.length || entries.length !== manifest.updates)
    throw new Error("Incomplete replay export");
  const after = await stat(path);
  if (before.size !== after.size || before.mtimeMs !== after.mtimeMs)
    throw new Error("Replay changed during indexing");
  return {
    entries,
    manifest,
    timestamps: entries.map((e) => e.pts),
    size: after.size,
    mtimeMs: after.mtimeMs,
    tracePath: path,
    alpha: false,
  };
}
export function replayIndex() {
  cached ??= buildIndex().catch((error) => {
    cached = undefined;
    throw error;
  });
  return cached;
}
export async function replayFrame(pts: number) {
  const { entries, timestamps, size, mtimeMs, tracePath, alpha } =
    await replayIndex();
  const index = indexAtOrBefore(timestamps, pts);
  const entry = entries[index];
  if (!entry) return null;
  const file = await open(tracePath, "r");
  try {
    const info = await file.stat();
    if (info.size !== size || info.mtimeMs !== mtimeMs) {
      cached = undefined;
      throw new Error("Replay changed after indexing");
    }
    const buffer = Buffer.alloc(entry.bytes);
    const { bytesRead } = await file.read(buffer, 0, entry.bytes, entry.offset);
    if (bytesRead !== entry.bytes)
      throw new Error("Replay changed during reading");
    const row = object(JSON.parse(buffer.toString("utf8")));
    const frame = parseFrame(
      alpha
        ? {
            ...row,
            schema_version: 1,
            frame: row.identity,
            dimensions: { width: row.width, height: row.height },
            corridor: row.corridor_analysis,
            trajectory: row.trajectory_set,
            interaction: row.interaction_analysis,
            risk: row.risk_assessment_set,
            attention: row.attention_decision_set,
            alerts: row.alert_output_set,
          }
        : row,
    );
    if (frame.frame.observation_ns !== entry.pts)
      throw new Error("Indexed PTS mismatch");
    return frame;
  } finally {
    await file.close();
  }
}
let verifiedVideo: ReturnType<typeof verifyVideo> | undefined;
export function replayVideo() {
  verifiedVideo ??= verifyVideo().catch((error) => {
    verifiedVideo = undefined;
    throw error;
  });
  return verifiedVideo;
}
async function verifyVideo() {
  // Operator-configured path only, never a browser-supplied filesystem path.
  const manifest = object(
    JSON.parse(await readFile(resolve(directory, "manifest.json"), "utf8")),
  );
  const configPath = resolve(
    directory,
    manifest.trace_mode === "COMPACT_ALPHA_TRACE"
      ? "configuration.json"
      : "../realtime-06-gpu-no-depth/configuration.json",
  );
  const video =
    process.env.VISION_REPLAY_VIDEO ??
    object(JSON.parse(await readFile(configPath, "utf8"))).input;
  if (typeof video !== "string") throw new Error("Replay video unavailable");
  const absolute = resolve(video);
  const info = await stat(absolute);
  if (!info.isFile()) throw new Error("Replay video unavailable");
  const hash = createHash("sha256");
  for await (const chunk of createReadStream(absolute))
    hash.update(chunk as Buffer);
  if (hash.digest("hex") !== manifest.source_sha256)
    throw new Error("Video does not match replay source hash");
  return {
    path: absolute,
    size: info.size,
    mtimeMs: info.mtimeMs,
    ino: info.ino,
  };
}

export async function replayStream(
  video: Awaited<ReturnType<typeof replayVideo>>,
  start: number,
  end: number,
) {
  const file = await open(video.path, "r");
  try {
    const info = await file.stat();
    if (
      info.size !== video.size ||
      info.mtimeMs !== video.mtimeMs ||
      info.ino !== video.ino
    ) {
      verifiedVideo = undefined;
      throw new Error("Replay video changed after verification");
    }
    let offset = start;
    let cancelled = false;
    let closing: Promise<void> | undefined;
    const close = () => (closing ??= file.close());
    return new ReadableStream<Uint8Array>({
      async pull(controller) {
        try {
          const buffer = Buffer.alloc(Math.min(64 * 1024, end - offset + 1));
          const { bytesRead } = await file.read(
            buffer,
            0,
            buffer.length,
            offset,
          );
          if (cancelled) return;
          if (!bytesRead)
            throw new Error("Video ended before the requested range");
          offset += bytesRead;
          controller.enqueue(buffer.subarray(0, bytesRead));
          if (offset > end) {
            await close();
            if (!cancelled) controller.close();
          }
        } catch (error) {
          await close();
          if (!cancelled) controller.error(error);
        }
      },
      async cancel() {
        cancelled = true;
        await close();
      },
    });
  } catch (error) {
    await file.close();
    throw error;
  }
}
