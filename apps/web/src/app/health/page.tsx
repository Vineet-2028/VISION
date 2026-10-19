import { getApiHealth } from "../../lib/health";
import { getApiBaseUrl } from "../../lib/server-config";

export const dynamic = "force-dynamic";

export default async function HealthPage() {
  const health = await getApiHealth(getApiBaseUrl(process.env));
  return (
    <main>
      <h1>Sentinel health</h1>
      <dl>
        <dt>Web</dt>
        <dd>Running</dd>
        <dt>API</dt>
        <dd>{health === "healthy" ? "Healthy" : "Unavailable"}</dd>
        <dt>Guardian</dt>
        <dd>Disabled</dd>
      </dl>
      <p>No monitoring or perception is active.</p>
    </main>
  );
}
