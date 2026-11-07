import { finite, object } from "./replay";

export const relevance = [
  "RELEVANT",
  "IRRELEVANT",
  "AMBIGUOUS",
  "INSUFFICIENT_CONTEXT",
] as const;
export const interruptions = [
  "SHOULD_INTERRUPT",
  "SHOULD_REMAIN_SILENT",
  "TOO_LATE",
  "REPEAT_UNNECESSARY",
] as const;
export type WindowReview = {
  relevance: string;
  interruption: string;
  notes: string;
  kind?: string;
  motion?: string;
};
export const reviewKinds = [
  "ALERT",
  "SILENCE",
  "MISSED_IMPORTANT_EVENT",
  "CAPABILITY_CHANGE",
] as const;
export const motionLabels = [
  "STATIC",
  "MOVING",
  "CAMERA_MOTION",
  "UNKNOWN",
] as const;
export type ReviewPacket = {
  packet_sha256: string;
  source_sha256: string;
  windows: { id: string; start_seconds: number; end_seconds: number }[];
};

export function parseReviewPacket(raw: unknown): ReviewPacket {
  const data = object(raw);
  if (
    ![data.packet_sha256, data.source_sha256].every(
      (h) => typeof h === "string" && /^[a-f0-9]{64}$/.test(h),
    ) ||
    !Array.isArray(data.windows) ||
    data.windows.length !== 30
  )
    throw new Error("Invalid review packet");
  const ids = new Set<string>();
  const windows = data.windows.map((entry) => {
    const row = object(entry),
      start = finite(row.start_seconds),
      end = finite(row.end_seconds);
    if (
      typeof row.id !== "string" ||
      !/^blind-\d{3}$/.test(row.id) ||
      ids.has(row.id) ||
      start < 0 ||
      end <= start
    )
      throw new Error("Invalid review window");
    ids.add(row.id);
    return { id: row.id, start_seconds: start, end_seconds: end };
  });
  return {
    packet_sha256: String(data.packet_sha256),
    source_sha256: String(data.source_sha256),
    windows,
  };
}

export function reviewed(value?: WindowReview): boolean {
  return (
    !!value &&
    relevance.some((x) => x === value.relevance) &&
    interruptions.some((x) => x === value.interruption) &&
    reviewKinds.some((x) => x === value.kind) &&
    motionLabels.some((x) => x === value.motion)
  );
}

export function parseReviewDraft(
  raw: string,
  packet: ReviewPacket,
  now: number,
): Record<string, WindowReview> {
  if (raw.length > 100_000) throw Error("Oversized review draft");
  const data = object(JSON.parse(raw));
  if (
    data.packet_sha256 !== packet.packet_sha256 ||
    typeof data.expires_at !== "number" ||
    data.expires_at <= now ||
    data.expires_at > now + 7 * 86400_000
  )
    throw Error("Expired or mismatched review draft");
  const answers = object(data.answers),
    result: Record<string, WindowReview> = {};
  for (const [id, value] of Object.entries(answers)) {
    if (!packet.windows.some((w) => w.id === id))
      throw Error("Unknown review window");
    const row = object(value);
    if (
      typeof row.notes !== "string" ||
      row.notes.length > 2000 ||
      !["", ...relevance].includes(String(row.relevance)) ||
      !["", ...interruptions].includes(String(row.interruption)) ||
      !["", ...reviewKinds].includes(String(row.kind ?? "")) ||
      !["", ...motionLabels].includes(String(row.motion ?? ""))
    )
      throw Error("Invalid review judgment");
    result[id] = {
      notes: row.notes,
      relevance: String(row.relevance),
      interruption: String(row.interruption),
      kind: String(row.kind ?? ""),
      motion: String(row.motion ?? ""),
    };
  }
  return result;
}
