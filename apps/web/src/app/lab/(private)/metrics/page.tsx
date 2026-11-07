const rows = [
  ["Published updates in 600 seconds", "2,641", "6,300"],
  ["Publication age Â· P95", "567.211 ms", "257.657 ms"],
  ["Publication age Â· P99", "716.824 ms", "307.794 ms"],
  ["Failed frames", "0", "0"],
  ["Specific / group / generic text alerts", "0 / 0 / 60", "13 / 2 / 58"],
  ["Offline frames processed", "18,000", "18,000"],
];
export default function Metrics() {
  return (
    <main className="wide">
      <h1>Replay measurements</h1>
      <section className="panel">
        <h2>First ten minutes of the same recording</h2>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Measure</th>
                <th scope="col">Rescued V0</th>
                <th scope="col">Controlled Alpha V1</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(([label, before, after]) => (
                <tr key={label}>
                  <th scope="row">{label}</th>
                  <td>{before}</td>
                  <td>{after}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <div className="card-grid">
        <article className="panel">
          <h2>141 unusable views</h2>
          <p>
            Across the full Alpha replay, no text alert was delivered from an
            unusable camera view.
          </p>
        </article>
        <article className="panel">
          <h2>21 rotation cases</h2>
          <p>
            Each case ran 60 frames. Correcting rotation recovered some tracks,
            with results varying by clip.
          </p>
        </article>
        <article className="panel">
          <h2>133 generic text alerts</h2>
          <p>
            The full Alpha replay also delivered 37 specific and two group
            alerts. Human usefulness remains unverified.
          </p>
        </article>
      </div>
      <p className="muted">
        Local Windows measurements, November 2026. Offline processing took 49.8
        minutes for Alpha and 16.9 minutes for V0. Both processed the same
        18,000 frames.
      </p>
    </main>
  );
}
