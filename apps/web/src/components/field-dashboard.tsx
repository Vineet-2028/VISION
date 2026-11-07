"use client";
import { useEffect, useRef, useState } from "react";
import { currentAge, localGateway } from "../lib/field";
import {
  object,
  parseFrame,
  text,
  type JsonObject,
  type ReplayFrame,
} from "../lib/replay";
import { ScenePanel } from "./scene-panel";
const RESULT_LIFETIME_MS = 500;
export function FieldDashboard({
  sessionView = false,
}: {
  sessionView?: boolean;
}) {
  const freshness = useRef<{
    base: string;
    received: number;
    rtt: number;
  } | null>(null);
  const [address, setAddress] = useState("http://127.0.0.1:8765"),
    [token, setToken] = useState(""),
    [connection, setConnection] = useState<{
      address: string;
      token: string;
    } | null>(null);
  const [status, setStatus] = useState("DISCONNECTED"),
    [error, setError] = useState<string | null>(null),
    [snapshot, setSnapshot] = useState<JsonObject | null>(null),
    [frame, setFrame] = useState<ReplayFrame | null>(null),
    [selected, setSelected] = useState<number | null>(null),
    [age, setAge] = useState<number | null>(null),
    [rtt, setRtt] = useState<number | null>(null);
  useEffect(() => {
    const timer = setInterval(() => {
      const sample = freshness.current;
      if (!sample) return;
      const value = currentAge(
        sample.base,
        sample.received,
        performance.now(),
        sample.rtt,
      );
      setAge(value);
      if (value >= RESULT_LIFETIME_MS) {
        setFrame(null);
        setStatus("STALE");
      }
    }, 100);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (!connection) return;
    let stopped = false,
      timer: ReturnType<typeof setTimeout> | undefined,
      expiry: ReturnType<typeof setTimeout> | undefined;
    const abort = new AbortController();
    async function poll() {
      const started = performance.now();
      try {
        const response = await fetch(`${connection!.address}/v1/status`, {
          headers: { Authorization: `Bearer ${connection!.token}` },
          signal: AbortSignal.any([abort.signal, AbortSignal.timeout(2000)]),
          cache: "no-store",
        });
        if (!response.ok)
          throw new Error(`Gateway rejected request (${response.status})`);
        const data = object(await response.json());
        if (stopped) return;
        clearTimeout(expiry);
        setSnapshot(data);
        setStatus(text(data.status, "DISCONNECTED"));
        setError(null);
        const elapsed = performance.now() - started;
        setRtt(elapsed);
        if (data.status !== "CONNECTED" || !data.result) {
          if (data.result_status === "EXPIRED_OR_FUTURE") setStatus("STALE");
          freshness.current = null;
          setFrame(null);
          setAge(null);
        } else {
          const result = object(data.result);
          const received = performance.now();
          const base = text(result.age_at_response_ns, "");
          const nextAge = currentAge(base, received, received, elapsed);
          freshness.current = { base, received, rtt: elapsed };
          setAge(nextAge);
          setFrame(
            nextAge < RESULT_LIFETIME_MS && result.scene
              ? parseFrame(result.scene)
              : null,
          );
          if (nextAge >= RESULT_LIFETIME_MS) setStatus("STALE");
          else
            expiry = setTimeout(() => {
              setFrame(null);
              setStatus("STALE");
            }, RESULT_LIFETIME_MS - nextAge);
        }
      } catch (e) {
        if (!stopped) {
          clearTimeout(expiry);
          freshness.current = null;
          setStatus("DISCONNECTED");
          setError(String(e));
          setFrame(null);
          setAge(null);
        }
      } finally {
        if (!stopped) timer = setTimeout(poll, 250);
      }
    }
    void poll();
    return () => {
      stopped = true;
      freshness.current = null;
      abort.abort();
      clearTimeout(expiry);
      if (timer) clearTimeout(timer);
    };
  }, [connection]);
  async function command(path: string, body: JsonObject) {
    if (!connection || !snapshot?.session_id) return;
    try {
      const response = await fetch(connection.address + path, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${connection.token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ ...body, session_id: snapshot.session_id }),
        signal: AbortSignal.timeout(2000),
      });
      if (!response.ok)
        throw new Error(`Command rejected (${response.status})`);
    } catch (e) {
      setError(String(e));
    }
  }
  async function download() {
    if (!connection) return;
    try {
      const response = await fetch(connection.address + "/v1/export", {
        headers: { Authorization: `Bearer ${connection.token}` },
        signal: AbortSignal.timeout(5000),
      });
      if (!response.ok) throw new Error("Session export failed");
      const url = URL.createObjectURL(await response.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = "vision-field-session.zip";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError(String(e));
    }
  }
  return (
    <main className="wide">
      <div className="page-heading">
        <div>
          <div className="eyebrow">Local field lab</div>
          <h1>
            {sessionView ? "Your test session." : "A live view, with context."}
          </h1>
          <p>
            The phone captures. The desktop reasons. This dashboard observes
            without controlling the alert path.
          </p>
        </div>
        <span className="badge">◇ {status}</span>
      </div>
      <section className="panel">
        <form
          className="transport"
          onSubmit={(e) => {
            e.preventDefault();
            try {
              setConnection({ address: localGateway(address), token });
              setStatus("CONNECTING");
            } catch (error) {
              setError(String(error));
            }
          }}
        >
          <label>
            Gateway
            <input
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              autoComplete="off"
            />
          </label>
          <label>
            Ephemeral token
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              autoComplete="off"
              required
            />
          </label>
          <button disabled={!!connection}>Connect</button>
          <button
            type="button"
            onClick={() => {
              setConnection(null);
              setFrame(null);
              setSnapshot(null);
              setStatus("DISCONNECTED");
              setToken("");
            }}
          >
            Disconnect
          </button>
        </form>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <div className="status-strip">
          <span>Mode: {text(snapshot?.mode)}</span>
          <span>
            Response RTT:{" "}
            {rtt === null ? "unavailable" : `${rtt.toFixed(0)} ms`}
          </span>
          <span>
            Conservative source age:{" "}
            {age === null ? "unavailable" : `${age.toFixed(0)} ms`}
          </span>
          <span>Recording: {snapshot?.recording ? "ON" : "OFF"}</span>
        </div>
      </section>
      <div className="workspace" style={{ marginTop: 24 }}>
        <section className="panel">
          <h2>{sessionView ? "Session summary" : "Vision receiving"}</h2>
          <p>
            {frame
              ? "A structured result is available. Raw camera preview is not transmitted to this dashboard."
              : "No current scene. Old results are cleared on disconnect or stale age."}
          </p>
          <dl className="decision-list">
            {Object.entries(
              snapshot?.counts ? object(snapshot.counts) : {},
            ).map(([key, value]) => (
              <div key={key}>
                <dt>{key.replaceAll("_", " ")}</dt>
                <dd>{String(value)}</dd>
              </div>
            ))}
          </dl>
          <div className="transport">
            <button
              disabled={!connection}
              onClick={() =>
                void command("/v1/recording", { enabled: !snapshot?.recording })
              }
            >
              {snapshot?.recording ? "Stop recording" : "Record test session"}
            </button>
            <button disabled={!connection} onClick={() => void download()}>
              Export session
            </button>
          </div>
          <p className="muted">
            Recording is off by default. Exports contain structured events,
            never raw camera frames. This is an engineering test, not navigation
            guidance.
          </p>
          <label>
            Scenario
            <select id="scenario" defaultValue="STATIC_OBSTACLE">
              {[
                "STATIC_OBSTACLE",
                "PERSON_CROSSING",
                "PARALLEL_PERSON",
                "BICYCLE_PUSHED",
                "CAMERA_TURN",
                "LOW_LIGHT",
                "CROWD",
                "OTHER",
              ].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          <div className="transport">
            {["START_SCENARIO", "END_SCENARIO"].map((kind) => (
              <button
                key={kind}
                disabled={!connection}
                onClick={() =>
                  void command("/v1/event", {
                    kind,
                    scenario: (
                      document.getElementById("scenario") as HTMLSelectElement
                    ).value,
                  })
                }
              >
                {kind.replaceAll("_", " ")}
              </button>
            ))}
          </div>
          <p className="muted">
            Scenario markers are developer annotations, not ground truth.
          </p>
        </section>
        <ScenePanel frame={frame} selected={selected} onSelect={setSelected} />
      </div>
    </main>
  );
}
