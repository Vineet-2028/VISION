import { describe, it, expect } from "vitest";
import {
  fitVideo,
  indexAtOrBefore,
  parseFrame,
  sameIdentity,
  silenceReasons,
} from "./replay";
it("requires an exact session and serial before joining recorded entity evidence", () => {
  expect(
    sameIdentity(
      { session_id: "s", serial: 4 },
      { session_id: "s", serial: 4 },
    ),
  ).toBe(true);
  expect(
    sameIdentity(
      { session_id: "old", serial: 4 },
      { session_id: "new", serial: 4 },
    ),
  ).toBe(false);
  expect(sameIdentity(undefined, undefined)).toBe(false);
});
const fixture = {
  schema_version: 1,
  mode: "REALTIME",
  frame: { sequence: 0, observation_ns: 100, source_id: "test" },
  dimensions: { width: 640, height: 480 },
  source_to_publication_age_ns: 30,
  detector: null,
  tracks: null,
  world: null,
  corridor: null,
  trajectory: null,
  interaction: null,
  risk: null,
  attention: null,
  alerts: null,
  provider_state: null,
  errors: [],
  warnings: [],
};
describe("replay boundary", () => {
  it("does not present future states when seeking", () => {
    expect(indexAtOrBefore([100, 210, 900], 209)).toBe(0);
    expect(indexAtOrBefore([100], 0)).toBe(-1);
    expect(indexAtOrBefore([100, 210], 210)).toBe(1);
  });
  it("accounts for letterboxing", () => {
    expect(fitVideo(640, 480, 800, 800)).toEqual({ scale: 1.25, x: 0, y: 100 });
  });
  it("rejects malformed versions and timing", () => {
    expect(() => parseFrame({ ...fixture, schema_version: 2 })).toThrow();
    expect(() =>
      parseFrame({ ...fixture, source_to_publication_age_ns: -1 }),
    ).toThrow();
    expect(() =>
      parseFrame({ ...fixture, dimensions: { width: Infinity, height: 480 } }),
    ).toThrow();
  });
  it("preserves recorded mode separately from playback and does not invent silence", () => {
    const frame = parseFrame(fixture);
    expect(frame.mode).toBe("REALTIME");
    expect(silenceReasons(frame)).toEqual([]);
  });
  it("renders actual suppression reasons only", () => {
    const frame = parseFrame({
      ...fixture,
      attention: {
        suppressed: [
          { reason: "EVENT_EXPIRED" },
          { reason: "COOLDOWN_ACTIVE" },
        ],
      },
    });
    expect(silenceReasons(frame)).toEqual(["EVENT_EXPIRED", "COOLDOWN_ACTIVE"]);
  });
});
