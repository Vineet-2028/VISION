import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { join } from "node:path";

const root = fileURLToPath(new URL("../apps/perception-lab/", import.meta.url));
const python = join(
  root,
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const commands = {
  check: [
    ["-m", "ruff", "format", "--check", "."],
    ["-m", "ruff", "check", "."],
    [
      "-m",
      "ruff",
      "format",
      "--check",
      "../../tools/curate_coco.py",
      "../../tools/export_detectors.py",
      "../../tools/summarize_detectors.py",
      "../../tools/qualify_detectors.py",
      "../../tools/evaluation_dataset.py",
      "../../tools/prepare_first_person.py",
      "../../tools/review_first_person.py",
      "../../tools/measure_replay.py",
      "../../tools/prepare_tracking.py",
      "../../tools/tracking_benchmark.py",
      "../../tools/depth_benchmark.py",
      "../../tools/download_depth.py",
      "../../tools/depth_parity.py",
      "../../tools/motion_benchmark.py",
      "../../tools/motion_replay.py",
    ],
    [
      "-m",
      "ruff",
      "check",
      "../../tools/curate_coco.py",
      "../../tools/export_detectors.py",
      "../../tools/summarize_detectors.py",
      "../../tools/qualify_detectors.py",
      "../../tools/evaluation_dataset.py",
      "../../tools/prepare_first_person.py",
      "../../tools/review_first_person.py",
      "../../tools/measure_replay.py",
      "../../tools/prepare_tracking.py",
      "../../tools/tracking_benchmark.py",
      "../../tools/depth_benchmark.py",
      "../../tools/download_depth.py",
      "../../tools/depth_parity.py",
      "../../tools/motion_benchmark.py",
      "../../tools/motion_replay.py",
    ],
    ["-m", "mypy"],
    ["-m", "pytest"],
  ],
  format: [
    [
      "-m",
      "ruff",
      "format",
      ".",
      "../../tools/curate_coco.py",
      "../../tools/export_detectors.py",
      "../../tools/summarize_detectors.py",
      "../../tools/qualify_detectors.py",
      "../../tools/evaluation_dataset.py",
      "../../tools/prepare_first_person.py",
      "../../tools/review_first_person.py",
      "../../tools/measure_replay.py",
      "../../tools/prepare_tracking.py",
      "../../tools/tracking_benchmark.py",
      "../../tools/depth_benchmark.py",
      "../../tools/download_depth.py",
      "../../tools/depth_parity.py",
      "../../tools/motion_benchmark.py",
      "../../tools/motion_replay.py",
    ],
  ],
};
const selected = commands[process.argv[2]];
if (!selected || process.argv.length !== 3) {
  console.error("Usage: node tools/lab.mjs <check|format>");
  process.exit(1);
}
for (const args of selected) {
  const result = spawnSync(python, args, {
    cwd: root,
    stdio: "inherit",
    windowsHide: true,
  });
  if (result.error)
    console.error(
      "Lab environment unavailable. Follow apps/perception-lab/README.md.",
    );
  if (result.status !== 0) process.exit(result.status ?? 1);
}
