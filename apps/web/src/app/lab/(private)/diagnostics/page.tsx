"use client";

import { useCallback, useEffect, useState } from "react";

type CaseIndex = {
  session_id: string;
  frames: { index: number; sequence: number; camera_ns: string }[];
};

type Candidate = {
  original_box: number[] | null;
  class_name?: string;
  score: number;
};
type RecordedEvent = {
  detector_diagnostics?: {
    source_sequence: number;
    source_id: string;
    accepted_samples?: Candidate[];
    rejected_samples?: Candidate[];
  };
  object_diagnostics?: { objects?: unknown[] };
};
type Packet = {
  sequence: number;
  width: number;
  height: number;
  recorded_events: RecordedEvent[];
  detector_source_events?: RecordedEvent[];
  feedback?: unknown[];
};

export default function Diagnostics() {
  const [index, setIndex] = useState<CaseIndex>();
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [packet, setPacket] = useState<{ frame: number; data: Packet }>();
  const [accepted, setAccepted] = useState(true);
  const [rejected, setRejected] = useState(false);
  const [selection, setSelection] = useState({ frame: -1, entity: -1 });
  const entity = selection.frame === frame ? selection.entity : -1;
  const [mediaFailure, setMediaFailure] = useState(-1);
  const [retry, setRetry] = useState(0);
  const [error, setError] = useState("");
  const moveFrame = useCallback((value: number) => {
    setSelection({ frame: -1, entity: -1 });
    setFrame(value);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/diagnostics", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok)
          throw new Error(
            "Import a case and configure VISION_DIAGNOSTIC_CASE on the local server.",
          );
        const data = await response.json();
        if (!controller.signal.aborted) {
          setIndex(data);
          moveFrame(0);
          setError("");
        }
      })
      .catch((reason) => {
        if (!controller.signal.aborted) {
          setPlaying(false);
          setError(String(reason));
        }
      });
    return () => controller.abort();
  }, [retry, moveFrame]);
  useEffect(() => {
    if (!index || index.frames.length === 0) return;
    const controller = new AbortController();
    fetch(`/api/diagnostics?frame=${frame}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Frame evidence unavailable");
        const data = await response.json();
        if (!controller.signal.aborted) {
          setPacket({ frame, data });
          setError("");
        }
      })
      .catch((reason) => {
        if (!controller.signal.aborted) {
          setPlaying(false);
          setError(String(reason));
        }
      });
    return () => controller.abort();
  }, [index, frame]);
  useEffect(() => {
    if (!playing || !index) return;
    const next = index.frames[frame + 1];
    if (!next) return;
    const delay = Math.max(
      20,
      Math.min(
        2000,
        Number(
          BigInt(next.camera_ns) - BigInt(index.frames[frame]!.camera_ns),
        ) / 1e6,
      ),
    );
    const timer = setTimeout(() => {
      moveFrame(frame + 1);
      if (frame + 1 === index.frames.length - 1) setPlaying(false);
    }, delay);
    return () => clearTimeout(timer);
  }, [playing, index, frame, moveFrame]);
  const current = packet?.frame === frame ? packet.data : undefined;
  const diagnostic = (
    current
      ? [...current.recorded_events, ...(current.detector_source_events ?? [])]
      : []
  )
    .map((event) => event.detector_diagnostics)
    .find(
      (value) =>
        value?.source_sequence === current?.sequence &&
        value.source_id === index?.session_id,
    );
  const objects =
    current?.recorded_events.flatMap(
      (event) => event.object_diagnostics?.objects ?? [],
    ) ?? [];
  const boxes = [
    ...(accepted
      ? (diagnostic?.accepted_samples ?? []).map((box) => ({
          ...box,
          color: "lime",
        }))
      : []),
    ...(rejected
      ? (diagnostic?.rejected_samples ?? []).map((box) => ({
          ...box,
          color: "orange",
        }))
      : []),
  ];
  return (
    <main>
      <h1>Diagnostic capture</h1>
      <p>
        Recorded evidence. Missing stages and object correspondence remain
        UNKNOWN.
      </p>
      {error && (
        <p role="alert">
          {error}{" "}
          <button
            onClick={() => {
              setPlaying(false);
              setPacket(undefined);
              setIndex(undefined);
              setRetry(retry + 1);
            }}
          >
            Retry case
          </button>
        </p>
      )}
      {index?.frames.length === 0 && (
        <p role="status">This case contains no captures.</p>
      )}
      {index && index.frames.length > 0 && (
        <>
          <p>
            Session {index.session_id} · Capture {index.frames[frame]?.sequence}
          </p>
          <button
            disabled={index.frames.length < 2 || !!error}
            onClick={() => {
              if (!playing && frame === index.frames.length - 1) moveFrame(0);
              setPlaying(!playing);
            }}
          >
            {playing ? "Pause" : "Play"}
          </button>
          <button
            disabled={frame === 0}
            onClick={() => {
              setPlaying(false);
              moveFrame(frame - 1);
            }}
          >
            Previous frame
          </button>
          <button
            disabled={frame >= index.frames.length - 1}
            onClick={() => {
              setPlaying(false);
              moveFrame(frame + 1);
            }}
          >
            Next frame
          </button>
          <input
            aria-label="Capture position"
            type="range"
            min={0}
            max={index.frames.length - 1}
            value={frame}
            onChange={(event) => {
              setPlaying(false);
              moveFrame(Number(event.target.value));
            }}
          />
          <label>
            <input
              type="checkbox"
              checked={accepted}
              onChange={(event) => setAccepted(event.target.checked)}
            />
            Accepted candidates
          </label>
          <label>
            <input
              type="checkbox"
              checked={rejected}
              onChange={(event) => setRejected(event.target.checked)}
            />
            Rejected candidates
          </label>
          {!diagnostic && (
            <p>Candidate overlay unavailable for this exact source frame.</p>
          )}
          {mediaFailure === frame && (
            <p role="status">
              Image unavailable. Media consent may be disabled, or the capture
              failed validation.
            </p>
          )}
          <div style={{ position: "relative", display: "inline-block" }}>
            {/* Raw images remain behind the authenticated media-consent gate. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              key={`${retry}-${frame}`}
              onError={() => setMediaFailure(frame)}
              onLoad={() => setMediaFailure(-1)}
              src={`/api/diagnostics?frame=${frame}&media=1`}
              alt="Selected source capture; media requires operator consent"
              style={{
                display: "block",
                maxWidth: "100%",
                maxHeight: "60vh",
                objectFit: "contain",
              }}
            />
            {current && mediaFailure !== frame && (
              <svg
                aria-label="Candidate boxes in original image coordinates"
                viewBox={"0 0 " + current.width + " " + current.height}
                style={{
                  position: "absolute",
                  inset: 0,
                  width: "100%",
                  height: "100%",
                  pointerEvents: "none",
                }}
              >
                {boxes.map(
                  (candidate, i) =>
                    candidate.original_box && (
                      <rect
                        key={i}
                        x={candidate.original_box[0]}
                        y={candidate.original_box[1]}
                        width={
                          candidate.original_box[2]! -
                          candidate.original_box[0]!
                        }
                        height={
                          candidate.original_box[3]! -
                          candidate.original_box[1]!
                        }
                        fill="none"
                        stroke={candidate.color}
                        strokeWidth={2}
                      />
                    ),
                )}
              </svg>
            )}
          </div>
          <label>
            Entity evidence{" "}
            <select
              value={entity}
              onChange={(event) =>
                setSelection({ frame, entity: Number(event.target.value) })
              }
            >
              <option value={-1}>All recorded evidence</option>
              {objects.map((_, i) => (
                <option key={i} value={i}>
                  Entity record {i + 1}
                </option>
              ))}
            </select>
          </label>
          <h2>Recorded pipeline evidence</h2>
          <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
            {packet?.frame === frame
              ? JSON.stringify(
                  entity >= 0
                    ? (objects[entity] ?? { status: "UNKNOWN" })
                    : packet.data,
                  null,
                  2,
                )
              : "Loading evidence…"}
          </pre>
        </>
      )}
    </main>
  );
}
