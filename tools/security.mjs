import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";

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
const lock = JSON.parse(
  readFileSync(new URL("../package-lock.json", import.meta.url)),
);
const config = (await import("../apps/web/eslint.config.mjs")).default;
if (config.some((entry) => entry.settings?.next?.rootDir !== undefined)) {
  throw new Error(
    "Reassess the braces advisory before enabling Next rootDir glob expansion.",
  );
}
const chain = new Set([
  "braces",
  "micromatch",
  "fast-glob",
  "@next/eslint-plugin-next",
  "eslint-config-next",
]);
const advisory = "https://github.com/advisories/GHSA-vfj7-8cjw-p6xm";
const reviewedVersions = {
  braces: "3.0.3",
  micromatch: "4.0.8",
  "fast-glob": "3.3.1",
  "@next/eslint-plugin-next": "16.4.0",
  "eslint-config-next": "16.4.0",
};
for (const [name, vulnerability] of Object.entries(report.vulnerabilities)) {
  const reviewed =
    chain.has(name) &&
    vulnerability.nodes.length > 0 &&
    vulnerability.severity === "high" &&
    vulnerability.nodes.every(
      (node) =>
        lock.packages[node]?.dev === true &&
        lock.packages[node]?.version === reviewedVersions[name],
    ) &&
    vulnerability.via.every((via) =>
      typeof via === "string" ? chain.has(via) : via.url === advisory,
    );
  if (!reviewed) {
    console.error(
      `Unreviewed dependency advisory: ${name} (${vulnerability.severity})`,
    );
    process.exitCode = 1;
  }
}
if (process.exitCode) throw new Error("Dependency security gate failed.");
const count = Object.keys(report.vulnerabilities).length;
console.log(
  count === 0
    ? "No npm advisories reported."
    : `No unreviewed advisories. ${count} development entries remain for ${advisory}; see docs/security.md. This is not a zero-vulnerability result.`,
);
