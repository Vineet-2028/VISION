import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { join } from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const python = join(
  root,
  "apps",
  "perception-lab",
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const result = spawnSync(
  python,
  [join(root, "tools/evaluate_v0.py"), ...process.argv.slice(2)],
  {
    cwd: root,
    stdio: "inherit",
    env: { ...process.env, PYTHONIOENCODING: "utf-8" },
  },
);
if (result.error) console.error(result.error.message);
process.exit(result.status ?? 1);
