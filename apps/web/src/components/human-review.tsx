"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  interruptions,
  reviewKinds,
  motionLabels,
  parseReviewDraft,
  parseReviewPacket,
  relevance,
  reviewed,
  type ReviewPacket,
  type WindowReview,
} from "../lib/human-review";

const blank: WindowReview = { relevance: "", interruption: "", notes: "" };
export function HumanReview() {
  const [packet, setPacket] = useState<ReviewPacket | null>(null),
    [index, setIndex] = useState(0),
    [error, setError] = useState(""),
    [answers, setAnswers] = useState<Record<string, WindowReview>>({});
  const [saveDraft, setSaveDraft] = useState(false),
    [draftStatus, setDraftStatus] = useState("Draft storage is off"),
    [reviewer, setReviewer] = useState("");
  const video = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const abort = new AbortController();
    fetch("/api/replay/review", { signal: abort.signal, cache: "no-store" })
      .then(async (response) => {
        if (!response.ok)
          throw new Error("The local review packet is unavailable.");
        const next = parseReviewPacket(await response.json());
        setPacket(next);
        try {
          const key = `vision-review-${next.packet_sha256}`,
            raw = localStorage.getItem(key);
          if (raw) {
            setAnswers(parseReviewDraft(raw, next, Date.now()));
            setSaveDraft(true);
            setDraftStatus(
              "Restored local draft; judgments remain yours to verify",
            );
          }
        } catch {
          setDraftStatus(
            "Draft unavailable or expired; original evidence unchanged",
          );
        }
      })
      .catch((e) => {
        if (!abort.signal.aborted) setError(String(e));
      });
    return () => abort.abort();
  }, []);
  function persist(next: Record<string, WindowReview>, enabled = saveDraft) {
    if (!packet || !enabled) return;
    try {
      localStorage.setItem(
        `vision-review-${packet.packet_sha256}`,
        JSON.stringify({
          packet_sha256: packet.packet_sha256,
          expires_at: Date.now() + 7 * 86400_000,
          answers: next,
        }),
      );
      setDraftStatus("Draft saved on this browser for up to 7 days");
    } catch {
      setDraftStatus(
        "Draft could not be saved. Download your review before closing.",
      );
    }
  }
  const clip = packet?.windows[index],
    answer = (clip && answers[clip.id]) || blank;
  useEffect(() => {
    const element = video.current;
    if (!element || !clip) return;
    const seek = () => {
      element.pause();
      element.currentTime = clip.start_seconds;
    };
    if (element.readyState >= 1) seek();
    else element.addEventListener("loadedmetadata", seek, { once: true });
    return () => element.removeEventListener("loadedmetadata", seek);
  }, [clip]);
  function edit(key: keyof WindowReview, value: string) {
    if (clip) {
      const next = {
        ...answers,
        [clip.id]: { ...(answers[clip.id] ?? blank), [key]: value },
      };
      setAnswers(next);
      persist(next);
    }
  }
  function download() {
    if (!packet) return;
    const rows = packet.windows.map((w) => ({
      ...w,
      judgment: answers[w.id] ?? null,
      review_status: reviewed(answers[w.id]) ? "REVIEWED" : "PENDING",
    }));
    const payload = {
      schema_version: 1,
      review_schema: "vision.review.v2",
      reviewer_reference: reviewer.trim() || null,
      training_consent: false,
      source_sha256: packet.source_sha256,
      original_packet_sha256: packet.packet_sha256,
      human_review_complete:
        !!reviewer.trim() && rows.every((w) => w.review_status === "REVIEWED"),
      windows: rows,
    };
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(payload, null, 2)], {
        type: "application/json",
      }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = "vision-human-review.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <main className="wide">
      <h1>Review recorded footage</h1>
      <p>
        Judge each clip from the footage. Leave uncertain answers pending.
        Download your work before closing the page. This recording includes
        non-walking segments; do not treat those as walking-scenario evidence.
      </p>
      {error && <p role="alert">{error}</p>}
      {!packet && !error && <p role="status">Loading review windowsâ€¦</p>}
      {packet && clip && (
        <section className="panel">
          <label>
            Reviewer reference (not a name requirement)
            <input
              value={reviewer}
              maxLength={80}
              onChange={(e) => setReviewer(e.target.value)}
            />
          </label>
          <label>
            <input
              type="checkbox"
              checked={saveDraft}
              onChange={(e) => {
                setSaveDraft(e.target.checked);
                if (e.target.checked) persist(answers, true);
                else
                  try {
                    localStorage.removeItem(
                      `vision-review-${packet.packet_sha256}`,
                    );
                    setDraftStatus(
                      "Local draft removed; current answers remain until closing",
                    );
                  } catch {
                    setDraftStatus(
                      "Browser refused deletion. Clear this site's storage in browser settings.",
                    );
                  }
              }}
            />
            Save draft on this private browser
          </label>
          <p role="status">{draftStatus}</p>
          <label>
            Window{" "}
            <select
              value={index}
              onChange={(e) => setIndex(Number(e.target.value))}
            >
              {packet.windows.map((w, i) => (
                <option key={w.id} value={i}>
                  {i + 1} of {packet.windows.length} Â·{" "}
                  {w.start_seconds.toFixed(1)} s
                </option>
              ))}
            </select>
          </label>
          <video
            ref={video}
            src="/api/replay/video"
            controls
            preload="metadata"
            playsInline
            style={{ width: "100%", maxHeight: "50vh" }}
            aria-label="Source footage for the selected window"
            onError={() =>
              setError(
                "Source footage could not be loaded. Check the configured local video.",
              )
            }
            onPlay={(e) => {
              const v = e.currentTarget;
              if (
                v.currentTime < clip.start_seconds ||
                v.currentTime >= clip.end_seconds
              )
                v.currentTime = clip.start_seconds;
            }}
            onTimeUpdate={(e) => {
              const v = e.currentTarget;
              if (!v.paused && v.currentTime >= clip.end_seconds) {
                v.pause();
                v.currentTime = clip.end_seconds;
              }
            }}
          />
          <p>
            {clip.start_seconds.toFixed(2)}â€“{clip.end_seconds.toFixed(2)} s
          </p>
          <Link
            href={`/lab/replay?pts=${Math.floor(clip.start_seconds * 1e9)}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            Inspect recorded decisions at this time
          </Link>
          <label>
            Relevance{" "}
            <select
              value={answer.relevance}
              onChange={(e) => edit("relevance", e.target.value)}
            >
              <option value="">Choose a judgment</option>
              {relevance.map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
          <label>
            Observed event type
            <select
              value={answer.kind ?? ""}
              onChange={(e) => edit("kind", e.target.value)}
            >
              <option value="">Choose from footage</option>
              {reviewKinds.map((k) => (
                <option key={k}>{k}</option>
              ))}
            </select>
          </label>
          <label>
            Motion evidence
            <select
              value={answer.motion ?? ""}
              onChange={(e) => edit("motion", e.target.value)}
            >
              <option value="">Choose a judgment</option>
              {motionLabels.map((k) => (
                <option key={k}>{k}</option>
              ))}
            </select>
          </label>
          <label>
            Interruption{" "}
            <select
              value={answer.interruption}
              onChange={(e) => edit("interruption", e.target.value)}
            >
              <option value="">Choose a judgment</option>
              {interruptions.map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
          <label>
            Notes{" "}
            <textarea
              value={answer.notes}
              maxLength={2000}
              onChange={(e) => edit("notes", e.target.value)}
            />
          </label>
          <p role="status">
            {Object.values(answers).filter(reviewed).length} of{" "}
            {packet.windows.length} windows reviewed
          </p>
          <button
            type="button"
            disabled={index === 0}
            onClick={() => setIndex((i) => i - 1)}
          >
            Previous window
          </button>{" "}
          <button
            type="button"
            disabled={index === packet.windows.length - 1}
            onClick={() => setIndex((i) => i + 1)}
          >
            Next window
          </button>{" "}
          <button type="button" onClick={download}>
            Download review
          </button>
        </section>
      )}
    </main>
  );
}
