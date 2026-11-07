import {
  entitySerial,
  list,
  object,
  sameIdentity,
  text,
  type ReplayFrame,
} from "../lib/replay";
const human = (value: string) => value.replaceAll("_", " ").toLowerCase();
export function ScenePanel({
  frame,
  selected,
  onSelect,
}: {
  frame: ReplayFrame | null;
  selected: number | null;
  onSelect: (id: number) => void;
}) {
  if (!frame)
    return (
      <aside className="panel">
        <h2>Current scene</h2>
        <p>Choose a moment in the replay to explore Vision’s decisions.</p>
      </aside>
    );
  const tracks = list(frame.tracks?.tracks);
  const track =
    tracks.find((t) => entitySerial(t.track_id) === selected) ?? tracks[0];
  const id = track ? entitySerial(track.track_id) : null;
  const entity = list(frame.world?.entities).find((e) =>
    sameIdentity(e.source_track_id, track?.track_id),
  );
  const semantics = entity?.track_semantics
    ? object(entity.track_semantics)
    : null;
  const freshConcept =
    semantics?.quality === "STABLE" &&
    typeof semantics.valid_until_ns === "number" &&
    frame.frame.observation_ns < semantics.valid_until_ns &&
    semantics.selected_concept
      ? object(semantics.selected_concept)
      : null;
  const freshGroup =
    semantics?.group_quality === "STABLE" &&
    typeof semantics.group_valid_until_ns === "number" &&
    frame.frame.observation_ns < semantics.group_valid_until_ns
      ? semantics.group_spoken_label
      : null;
  const match = (value: unknown) =>
    list(value).find((x) => sameIdentity(x.entity_id, entity?.entity_id));
  const relation = match(frame.corridor?.entity_relations),
    trajectory = match(frame.trajectory?.trajectories),
    risk = match(frame.risk?.assessments),
    interaction = match(frame.interaction?.entity_interactions);
  const decisions = list(frame.attention?.selected);
  const suppressed = list(frame.attention?.suppressed).filter((x) =>
    sameIdentity(object(x.decision).entity_id, entity?.entity_id),
  );
  const decision =
    decisions.find((x) => sameIdentity(x.entity_id, entity?.entity_id)) ??
    (suppressed[0] ? object(suppressed[0].decision) : undefined);
  const reasons = decision?.reason_codes;
  const alerts = list(frame.alerts?.outputs);
  return (
    <aside className="panel scene-panel">
      <div className="eyebrow">Understanding the scene</div>
      <h2>What matters here?</h2>
      <label>
        Explore an entity
        <select
          value={id ?? ""}
          onChange={(e) => onSelect(Number(e.target.value))}
        >
          <option value="" disabled>
            No entity selected
          </option>
          {tracks.map((t) => {
            const key = entitySerial(t.track_id);
            return (
              <option key={key} value={key ?? ""}>
                #{key} · {human(text(t.category, "Unknown object"))}
              </option>
            );
          })}
        </select>
      </label>
      <div className="entity-title">
        {track
          ? human(text(track.category, "Unknown object"))
          : "No tracked entity"}{" "}
        <span className="badge">#{id ?? "—"}</span>
      </div>
      <p className="muted">
        {human(text(track?.observation_status))} · quality{" "}
        {typeof track?.quality === "number"
          ? track.quality.toFixed(2)
          : "unavailable"}
      </p>
      <dl className="decision-list">
        <dt>Recorded object label</dt>
        <dd>
          {text(freshConcept?.normalized_label, text(freshGroup, "Unknown"))}
        </dd>
        <dt>Camera view</dt>
        <dd>{human(text(frame.camera_view_quality?.status))}</dd>
        <dt>Orientation source</dt>
        <dd>{human(text(frame.camera_orientation?.source))}</dd>
        <dt>User heading</dt>
        <dd>{human(text(frame.heading?.direction))}</dd>
        <dt>Corridor</dt>
        <dd>{human(text(relation?.relation))}</dd>
        <dt>Trajectory</dt>
        <dd>
          {human(text(trajectory?.coordinate_space))} ·{" "}
          {human(text(trajectory?.quality))}
        </dd>
        <dt>Interaction</dt>
        <dd>{human(text(interaction?.quality))}</dd>
        <dt>Risk</dt>
        <dd>◇ {human(text(risk?.risk_level))}</dd>
        <dt>Attention</dt>
        <dd>{human(text(decision?.decision))}</dd>
      </dl>
      <div className="silence">
        <h3>
          {text(decision?.decision) === "ANNOUNCE"
            ? "Why Vision selected this entity"
            : "Why Vision stayed silent"}
        </h3>
        {Array.isArray(reasons) && reasons.length ? (
          <ul>
            {reasons.map((r, i) => (
              <li key={i}>{human(text(r))}</li>
            ))}
          </ul>
        ) : (
          <p>No recorded explanation is available for this entity.</p>
        )}
      </div>
      <section>
        <h3>Scene alerts</h3>
        {alerts.map((a, i) => (
          <p key={i}>
            {a.presentation
              ? text(object(a.presentation).short_text)
              : "No text presentation"}{" "}
            <span className="badge">{human(text(a.status))}</span>
          </p>
        ))}
      </section>
      <details>
        <summary>Engineering details</summary>
        <p>Session {text(frame.tracks?.session_id)}</p>
        <p>
          Recorded source age:{" "}
          {frame.source_to_publication_age_ns === null
            ? "unavailable"
            : `${(frame.source_to_publication_age_ns / 1e6).toFixed(0)} ms`}
        </p>
        <p>
          Predicted path samples are unavailable in the frozen export; no path
          is reconstructed.
        </p>
        <pre>
          {JSON.stringify(
            {
              providers: frame.provider_state,
              relation,
              trajectory,
              interaction,
              risk,
              decision,
              errors: frame.errors,
              warnings: frame.warnings,
            },
            null,
            2,
          )}
        </pre>
      </details>
    </aside>
  );
}
