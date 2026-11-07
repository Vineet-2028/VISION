"use client";
import { useState } from "react";
// Minimal public projection of measured updates 0 and 1, Alpha full realtime 01.
// No media, person/track identity, source location or per-user data is distributed.
const events = [
  {
    title: "An interruption",
    decision: "ANNOUNCE",
    message: "Object.",
    reason: "NEW_RELEVANT_ENTITY",
    semantic: "SEMANTIC_UNSTABLE",
    result: "TEXT_SINK_ACCEPTED_NOT_AUDIO",
    explanation:
      "The object label was uncertain. Guardian retained the physical event and used generic wording. The text sink accepted this message; no physical speech is implied.",
  },
  {
    title: "A silent decision",
    decision: "SILENT",
    message: "No presentation",
    reason: "NO_INTERRUPT_NOT_A_SAFETY_VERDICT",
    semantic: "TRACK_NOT_ASSOCIATED",
    result: "ATTENTION_SILENT",
    explanation:
      "This recorded decision did not produce an interruption. It does not establish that the scene was safe or that every important object was detected.",
  },
] as const;
export function ProductDemo() {
  const [index, setIndex] = useState(0);
  const event = events[index]!;
  return (
    <section className="demo-explainer">
      <div className="demo-choices" aria-label="Choose a recorded outcome">
        {events.map((e, i) => (
          <button
            key={e.title}
            aria-pressed={index === i}
            onClick={() => setIndex(i)}
          >
            {e.title}
          </button>
        ))}
      </div>
      <div className="decision-stage">
        <div className="decision-orbit" aria-hidden="true">
          <span>Observe</span>
          <span>Track</span>
          <span>Consider</span>
          <strong>{event.decision === "SILENT" ? "Silence" : "Present"}</strong>
        </div>
        <div aria-live="polite" className="decision-explanation">
          <p className="eyebrow">Recorded software outcome</p>
          <h2>{event.message}</h2>
          <p>{event.explanation}</p>
          <details>
            <summary>Inspect recorded reasons</summary>
            <dl>
              <dt>Attention</dt>
              <dd>{event.reason}</dd>
              <dt>Semantics</dt>
              <dd>{event.semantic}</dd>
              <dt>Presentation</dt>
              <dd>{event.result}</dd>
            </dl>
          </details>
        </div>
      </div>
      <p className="microcopy">
        VISION_CONTROLLED_ALPHA_V1 · Text-only projection · No human accuracy
        label
      </p>
    </section>
  );
}
