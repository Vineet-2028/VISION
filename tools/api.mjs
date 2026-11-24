import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { chmodSync, existsSync, lstatSync, readdirSync } from "node:fs";

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
// OneDrive can restore READONLY on generated directories after a successful build.
// Maven clean cannot remove those directories on Windows. Only normalize this
// fixed generated tree; never follow junctions/symlinks or touch source files.
if (windows && process.argv[2] === "core-check") {
  const target = fileURLToPath(
    new URL("../packages/guardian-core/target/", import.meta.url),
  );
  const pending = existsSync(target) ? [target] : [];
  while (pending.length) {
    const current = pending.pop();
    const entry = lstatSync(current);
    if (entry.isSymbolicLink()) {
      throw new Error("Refusing to prepare a linked Guardian build directory");
    }
    if (!entry.isDirectory()) continue;
    chmodSync(current, 0o777);
    for (const child of readdirSync(current, { withFileTypes: true })) {
      if (child.isDirectory() || child.isSymbolicLink()) {
        pending.push(join(current, child.name));
      }
    }
  }
}
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
