"use client";
import { useEffect, useRef, useState } from "react";
import {
  finite,
  fitVideo,
  indexAtOrBefore,
  list,
  object,
  parseFrame,
  text,
  type ReplayFrame,
} from "../lib/replay";
import { ScenePanel } from "./scene-panel";
type Layer = "detections" | "tracks" | "corridor";
export function ReplayPlayer() {
  const video = useRef<HTMLVideoElement>(null),
    canvas = useRef<HTMLCanvasElement>(null);
  const [timestamps, setTimestamps] = useState<number[]>([]),
    [frame, setFrame] = useState<ReplayFrame | null>(null),
    [error, setError] = useState<string | null>(null),
    [selected, setSelected] = useState<number | null>(null),
    [playing, setPlaying] = useState(false);
  const [layers, setLayers] = useState<Record<Layer, boolean>>({
    detections: false,
    tracks: true,
    corridor: true,
  });
  const current = useRef<ReplayFrame | null>(null);
  const layerRef = useRef(layers);
  useEffect(() => {
    layerRef.current = layers;
  }, [layers]);
  useEffect(() => {
    const abort = new AbortController();
    fetch("/api/replay/manifest", { signal: abort.signal })
      .then((r) => {
        if (!r.ok)
          throw new Error(
            "Replay evidence is unavailable. Start the local demo service.",
          );
        return r.json();
      })
      .then((v: unknown) => {
        const data = object(v);
        if (
          !Array.isArray(data.timestamps) ||
          !data.timestamps.length ||
          data.timestamps.length > 100000
        )
          throw new Error("Invalid replay index");
        setTimestamps(data.timestamps.map(finite));
      })
      .catch((e) => {
        if (!abort.signal.aborted) setError(String(e));
      });
    return () => abort.abort();
  }, []);
  useEffect(() => {
    if (!timestamps.length) return;
    let stopped = false,
      animation = 0,
      requested = -2,
      wanted = -1,
      busy = false;
    const abort = new AbortController();
    async function load() {
      if (busy || stopped || wanted === requested) return;
      const target = wanted;
      requested = target;
      busy = true;
      current.current = null;
      setFrame(null);
      try {
        if (target < 0) {
          current.current = null;
          setFrame(null);
          return;
        }
        const response = await fetch(
          `/api/replay/frame?pts=${timestamps[target]}`,
          { signal: abort.signal },
        );
        if (!response.ok) throw new Error("Cannot read this replay state");
        const parsed = parseFrame(await response.json());
        if (!stopped && wanted === target) {
          current.current = parsed;
          setFrame(parsed);
          setError(null);
        }
      } catch (e) {
        if (!stopped) setError(String(e));
      } finally {
        busy = false;
        if (!stopped && wanted !== requested) void load();
      }
    }
    function paint() {
      const player = video.current,
        overlay = canvas.current;
      if (!player || !overlay) return;
      wanted = indexAtOrBefore(
        timestamps,
        Math.floor(player.currentTime * 1e9),
      );
      void load();
      const r = current.current,
        ctx = overlay.getContext("2d");
      if (ctx) {
        const rect = player.getBoundingClientRect();
        const ratio = window.devicePixelRatio || 1;
        const w = Math.round(rect.width * ratio),
          h = Math.round(rect.height * ratio);
        if (overlay.width !== w || overlay.height !== h) {
          overlay.width = w;
          overlay.height = h;
        }
        ctx.clearRect(0, 0, w, h);
        if (
          r &&
          player.videoWidth === r.dimensions.width &&
          player.videoHeight === r.dimensions.height &&
          indexAtOrBefore(timestamps, Math.floor(player.currentTime * 1e9)) ===
            requested &&
          r.frame.observation_ns === timestamps[wanted]
        ) {
          const fit = fitVideo(r.dimensions.width, r.dimensions.height, w, h);
          ctx.save();
          ctx.translate(fit.x, fit.y);
          ctx.scale(fit.scale, fit.scale);
          ctx.lineWidth = 2 / fit.scale;
          ctx.font = `${13 / fit.scale}px system-ui`;
          try {
            const box = (v: unknown, label: string, color: string) => {
              const b = object(v);
              const x = finite(b.x1),
                y = finite(b.y1);
              ctx.strokeStyle = color;
              ctx.fillStyle = color;
              ctx.strokeRect(x, y, finite(b.x2) - x, finite(b.y2) - y);
              ctx.fillText(
                label,
                x,
                Math.max(15 / fit.scale, y - 5 / fit.scale),
              );
            };
            if (layerRef.current.detections)
              for (const d of list(r.detector?.detections))
                box(d.box, text(d.label), "#f2c46e");
            if (layerRef.current.tracks)
              for (const t of list(r.tracks?.tracks))
                box(
                  t.bbox,
                  `#${object(t.track_id).serial} ${text(t.category, "Unknown object")}`,
                  "#a8e7ee",
                );
            if (layerRef.current.corridor && r.corridor) {
              const polygon = object(r.corridor.corridor).image_polygon;
              if (Array.isArray(polygon) && polygon.length >= 3) {
                ctx.beginPath();
                polygon.forEach((p, i) => {
                  if (!Array.isArray(p)) throw new Error("Invalid polygon");
                  const x = finite(p[0]),
                    y = finite(p[1]);
                  if (i === 0) ctx.moveTo(x, y);
                  else ctx.lineTo(x, y);
                });
                ctx.closePath();
                ctx.fillStyle = "rgba(109,196,211,.14)";
                ctx.strokeStyle = "#8ad4de";
                ctx.fill();
                ctx.stroke();
              }
            }
          } catch {
            setError("Overlay geometry is malformed; overlay unavailable.");
          } finally {
            ctx.restore();
          }
        }
      }
      animation = requestAnimationFrame(paint);
    }
    animation = requestAnimationFrame(paint);
    return () => {
      stopped = true;
      abort.abort();
      cancelAnimationFrame(animation);
    };
  }, [timestamps]);
  const seek = (ns: number) => {
    if (video.current) {
      video.current.currentTime = ns / 1e9;
      current.current = null;
      setFrame(null);
    }
  };
  function step(direction: number) {
    if (!video.current) return;
    video.current.pause();
    const index = indexAtOrBefore(
      timestamps,
      Math.floor(video.current.currentTime * 1e9),
    );
    const next =
      timestamps[
        Math.max(0, Math.min(timestamps.length - 1, index + direction))
      ];
    if (next !== undefined) seek(next);
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">A window into Vision</div>
          <h1>
            See the scene.
            <br />
            Understand the decision.
          </h1>
          <p>
            Explore what Vision noticed, what mattered, and why it stayed
            silent.
          </p>
        </div>
        <span className="badge">◷ Offline replay</span>
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="workspace">
        <section className="panel video-panel">
          <div className="video-stage">
            <video
              ref={video}
              src="/api/replay/video"
              controls
              playsInline
              preload="metadata"
              onLoadedMetadata={(event) => {
                const raw = new URLSearchParams(window.location.search).get(
                  "pts",
                );
                const pts = raw === null ? NaN : Number(raw);
                if (
                  Number.isSafeInteger(pts) &&
                  pts >= 0 &&
                  pts / 1e9 < event.currentTarget.duration
                )
                  event.currentTarget.currentTime = pts / 1e9;
              }}
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
              onError={() =>
                setError("Local source video is unavailable or unsupported.")
              }
              aria-label="Recorded prototype scene"
            />
            <canvas ref={canvas} aria-hidden="true" />
          </div>
          <div className="transport">
            <button
              onClick={() => {
                if (video.current) {
                  if (playing) video.current.pause();
                  else
                    void video.current
                      .play()
                      .catch(() => setError("Playback could not start"));
                }
              }}
            >
              {playing ? "Pause" : "Play replay"}
            </button>
            <button onClick={() => step(-1)}>← Previous state</button>
            <button onClick={() => step(1)}>Next state →</button>
            <label>
              Speed
              <select
                defaultValue="1"
                onChange={(e) => {
                  if (video.current)
                    video.current.playbackRate = Number(e.target.value);
                }}
              >
                {[0.25, 0.5, 1, 2].map((rate) => (
                  <option key={rate} value={rate}>
                    {rate}×
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="layers">
            <span>Show overlays</span>
            {(Object.keys(layers) as Layer[]).map((layer) => (
              <label key={layer}>
                <input
                  type="checkbox"
                  checked={layers[layer]}
                  onChange={(e) =>
                    setLayers({ ...layers, [layer]: e.target.checked })
                  }
                />
                {layer}
              </label>
            ))}
          </div>
          <label className="seek-label">
            Jump to recorded moment
            <select
              defaultValue=""
              onChange={(e) => seek(Number(e.target.value))}
            >
              <option value="" disabled>
                Choose a timestamp
              </option>
              {timestamps
                .filter((_, i) => i === 0 || i % 100 === 0)
                .map((ns) => (
                  <option key={ns} value={ns}>
                    {(ns / 1e9).toFixed(1)} seconds
                  </option>
                ))}
            </select>
          </label>
          <div className="status-strip">
            <span>
              ◷ {frame ? (frame.frame.observation_ns / 1e9).toFixed(2) : "—"} s
              source PTS
            </span>
            <span>◇ Depth unavailable</span>
            <span>Recorded realtime experiment · not live</span>
          </div>
          <p className="muted">
            Prototype evidence. Silence is not a safety verdict. This replay is
            not navigation guidance.
          </p>
        </section>
        <ScenePanel frame={frame} selected={selected} onSelect={setSelected} />
      </div>
    </>
  );
}
