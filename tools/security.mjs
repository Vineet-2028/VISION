import { spawnSync } from "node:child_process";

// npm provides its CLI path when this is invoked through npm run security.
if (!process.env.npm_execpath) throw new Error("Run npm run security.");
const result = spawnSync(
  process.execPath,
  [process.env.npm_execpath, "audit", "--json"],
  {
    encoding: "utf8",
    windowsHide: true,
  },
);
if (result.error || ![0, 1].includes(result.status)) {
  throw new Error("npm audit could not run; security verification failed.");
}
const report = JSON.parse(result.stdout);
if (report.error || !report.vulnerabilities || !report.metadata) {
  throw new Error("npm audit did not return a complete advisory report.");
}
const entries = Object.entries(report.vulnerabilities);
for (const [name, finding] of entries) {
  console.error(`Dependency advisory: ${name} (${finding.severity})`);
}
if (result.status !== 0 || entries.length > 0) {
  throw new Error("Dependency security gate failed.");
}
console.log("No npm advisories reported.");
