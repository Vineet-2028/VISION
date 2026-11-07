/** Versioned export boundary. No prediction, risk or silence reason is invented here. */
export type JsonObject = Record<string, unknown>;
export type Point = readonly [number, number];
export interface ReplayFrame {
  schema_version: 1;
  mode: "REALTIME" | "OFFLINE_REPLAY";
  frame: { sequence: number; observation_ns: number; source_id: string };
  dimensions: { width: number; height: number };
  source_to_publication_age_ns: number | null;
  detector: JsonObject | null;
  tracks: JsonObject | null;
  world: JsonObject | null;
  corridor: JsonObject | null;
  trajectory: JsonObject | null;
  interaction: JsonObject | null;
  risk: JsonObject | null;
  attention: JsonObject | null;
  alerts: JsonObject | null;
  provider_state: JsonObject | null;
  camera_view_quality?: JsonObject | null;
  camera_orientation?: JsonObject | null;
  heading?: JsonObject | null;
  errors: string[];
  warnings: string[];
}
export function object(value: unknown): JsonObject {
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new Error("Expected an object");
  return value as JsonObject;
}
export function finite(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value))
    throw new Error("Expected finite number");
  return value;
}
export function text(value: unknown, fallback = "Unavailable"): string {
  return typeof value === "string" ? value : fallback;
}
export function list(value: unknown, limit = 512): JsonObject[] {
  if (value === undefined || value === null) return [];
  if (!Array.isArray(value) || value.length > limit)
    throw new Error("Invalid or oversized list");
  return value.map(object);
}
export function parseFrame(value: unknown): ReplayFrame {
  const row = object(value),
    frame = object(row.frame),
    dimensions = object(row.dimensions);
  if (
    row.schema_version !== 1 ||
    !["REALTIME", "OFFLINE_REPLAY"].includes(text(row.mode))
  )
    throw new Error("Unsupported replay version/mode");
  const pts = finite(frame.observation_ns),
    sequence = finite(frame.sequence);
  if (
    !Number.isSafeInteger(pts) ||
    pts < 0 ||
    !Number.isSafeInteger(sequence) ||
    sequence < 0 ||
    typeof frame.source_id !== "string"
  )
    throw new Error("Invalid frame identity");
  const width = finite(dimensions.width),
    height = finite(dimensions.height);
  if (![width, height].every((n) => Number.isInteger(n) && n > 0 && n <= 8192))
    throw new Error("Invalid dimensions");
  const age = row.source_to_publication_age_ns;
  if (age !== null && finite(age) < 0) throw new Error("Invalid age");
  const stages = [
    "detector",
    "tracks",
    "world",
    "corridor",
    "trajectory",
    "interaction",
    "risk",
    "attention",
    "alerts",
    "provider_state",
  ] as const;
  const values = Object.fromEntries(
    stages.map((key) => [key, row[key] === null ? null : object(row[key])]),
  ) as Pick<ReplayFrame, (typeof stages)[number]>;
  const strings = (v: unknown): string[] => {
    if (
      !Array.isArray(v) ||
      v.length > 512 ||
      !v.every((x) => typeof x === "string")
    )
      throw new Error("Invalid diagnostics");
    return v;
  };
  return {
    schema_version: 1,
    mode: row.mode as ReplayFrame["mode"],
    frame: { sequence, observation_ns: pts, source_id: frame.source_id },
    dimensions: { width, height },
    source_to_publication_age_ns: age as number | null,
    ...values,
    camera_view_quality: row.camera_view_quality
      ? object(row.camera_view_quality)
      : null,
    camera_orientation: row.camera_orientation
      ? object(row.camera_orientation)
      : null,
    heading:
      row.heading || row.user_motion_heading
        ? object(row.heading ?? row.user_motion_heading)
        : null,
    errors: strings(row.errors),
    warnings: strings(row.warnings),
  };
}
export function indexAtOrBefore(
  timestamps: readonly number[],
  pts: number,
): number {
  if (!Number.isFinite(pts)) throw new Error("Invalid seek");
  let lo = 0,
    hi = timestamps.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (timestamps[mid]! <= pts) lo = mid + 1;
    else hi = mid;
  }
  return lo - 1;
}
export function fitVideo(
  sourceWidth: number,
  sourceHeight: number,
  width: number,
  height: number,
) {
  if (
    ![sourceWidth, sourceHeight, width, height].every(
      (n) => Number.isFinite(n) && n > 0,
    )
  )
    throw new Error("Invalid overlay size");
  const scale = Math.min(width / sourceWidth, height / sourceHeight);
  return {
    scale,
    x: (width - sourceWidth * scale) / 2,
    y: (height - sourceHeight * scale) / 2,
  };
}
export function entitySerial(value: unknown): number | null {
  if (value === undefined || value === null) return null;
  const serial = object(value).serial;
  return typeof serial === "number" && Number.isSafeInteger(serial)
    ? serial
    : null;
}

export function sameIdentity(left: unknown, right: unknown): boolean {
  if (!left || !right) return false;
  const a = object(left),
    b = object(right);
  return (
    typeof a.session_id === "string" &&
    a.session_id === b.session_id &&
    entitySerial(a) !== null &&
    entitySerial(a) === entitySerial(b)
  );
}
export function silenceReasons(frame: ReplayFrame): string[] {
  const reasons = list(frame.attention?.suppressed).map((s) => text(s.reason));
  return [...new Set(reasons)];
}
