import { describe, expect, it } from "vitest";
import { parseReviewPacket, reviewed, parseReviewDraft } from "./human-review";

describe("human review", () => {
  it("drafts cannot cross packet boundaries or restore expired judgments", () => {
    const packet = {
      packet_sha256: "a".repeat(64),
      source_sha256: "b".repeat(64),
      windows: [{ id: "blind-001", start_seconds: 0, end_seconds: 6 }],
    };
    const draft = {
      packet_sha256: packet.packet_sha256,
      expires_at: 2000,
      answers: {
        "blind-001": {
          relevance: "",
          interruption: "",
          notes: "uncertain",
          kind: "",
          motion: "",
        },
      },
    };
    expect(
      parseReviewDraft(JSON.stringify(draft), packet, 1000)["blind-001"]?.notes,
    ).toBe("uncertain");
    expect(() => parseReviewDraft(JSON.stringify(draft), packet, 2000)).toThrow(
      /Expired/,
    );
    expect(() =>
      parseReviewDraft(
        JSON.stringify({ ...draft, packet_sha256: "c".repeat(64) }),
        packet,
        1000,
      ),
    ).toThrow(/mismatched/);
  });
  it("requires explicit relevance, interruption, event type and motion judgments", () => {
    expect(reviewed()).toBe(false);
    expect(
      reviewed({ relevance: "RELEVANT", interruption: "", notes: "" }),
    ).toBe(false);
    expect(
      reviewed({
        relevance: "AMBIGUOUS",
        interruption: "TOO_LATE",
        notes: "",
        kind: "MISSED_IMPORTANT_EVENT",
        motion: "UNKNOWN",
      }),
    ).toBe(true);
  });
  it("preserves the fixed windows and rejects duplicate identities", () => {
    const rows = Array.from({ length: 30 }, (_, i) => ({
      id: "blind-" + String(i + 1).padStart(3, "0"),
      start_seconds: i * 7,
      end_seconds: i * 7 + 6,
    }));
    const data = {
      source_sha256: "f".repeat(64),
      packet_sha256: "a".repeat(64),
      windows: rows,
    };
    expect(parseReviewPacket(data).windows).toEqual(rows);
    rows[1] = rows[0]!;
    expect(() => parseReviewPacket(data)).toThrow(/window/);
  });
});
