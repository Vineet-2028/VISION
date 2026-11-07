export default function Login() {
  return (
    <main>
      <p className="eyebrow">Private research workspace</p>
      <h1>VISION Lab</h1>
      <p>
        For authorized local researchers. The public site does not serve private
        recordings. Ask the operator for the Lab access secret.
      </p>
      <form action="/api/lab/login" method="post" className="panel">
        <label>
          Lab access secret
          <input
            name="secret"
            type="password"
            required
            minLength={32}
            maxLength={256}
            autoComplete="current-password"
          />
        </label>
        <button type="submit">Unlock Lab</button>
      </form>
      <p>
        No account is created. Access expires after eight hours. Restart with a
        rotated operator secret to revoke all sessions.
      </p>
    </main>
  );
}
