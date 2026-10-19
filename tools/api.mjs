import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { join } from "node:path";

const directory = fileURLToPath(new URL("../apps/api/", import.meta.url));
const tasks = new Map([
  ["dev", ["spring-boot:run"]],
  ["check", ["--batch-mode", "--no-transfer-progress", "verify"]],
  ["format", ["--batch-mode", "--no-transfer-progress", "spotless:apply"]],
  [
    "core-check",
    [
      "--batch-mode",
      "--no-transfer-progress",
      "-f",
      "../../packages/guardian-core/pom.xml",
      "clean",
      "verify",
    ],
  ],
  [
    "core-format",
    [
      "--batch-mode",
      "--no-transfer-progress",
      "-f",
      "../../packages/guardian-core/pom.xml",
      "spotless:apply",
    ],
  ],
]);
const args = tasks.get(process.argv[2]);
if (!args || process.argv.length !== 3) {
  console.error(
    "Usage: node tools/api.mjs <dev|check|format|core-check|core-format>",
  );
  process.exit(1);
}

// Only fixed task arguments enter cmd.exe; never accept arbitrary shell input.
const windows = process.platform === "win32";
const command = windows ? (process.env.ComSpec ?? "cmd.exe") : "sh";
const commandArgs = windows
  ? ["/d", "/s", "/c", `""${join(directory, "mvnw.cmd")}" ${args.join(" ")}"`]
  : [join(directory, "mvnw"), ...args];
const result = spawnSync(command, commandArgs, {
  cwd: directory,
  stdio: "inherit",
  windowsHide: true,
  windowsVerbatimArguments: windows,
});
if (result.error) console.error(result.error.message);
process.exit(result.status ?? 1);
