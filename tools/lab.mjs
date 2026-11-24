import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { join } from "node:path";

const root = fileURLToPath(new URL("../apps/perception-lab/", import.meta.url));
const python = join(
  root,
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const toolPaths = [
  "../../tools/field_diagnostic_summary.py",
  "../../tools/field_diagnostic_regression.py",
  "../../tools/import_field_case.py",
  "../../tools/replay_field_case.py",
  "../../tools/field_failure_report.py",
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
  "../../tools/export_pidnet.py",
  "../../tools/semantic_benchmark.py",
  "../../tools/evaluate_semantics.py",
  "../../tools/semantic_replay.py",
  "../../tools/world_benchmark.py",
  "../../tools/corridor_benchmark.py",
  "../../tools/trajectory_benchmark.py",
  "../../tools/interaction_benchmark.py",
  "../../tools/risk_benchmark.py",
  "../../tools/risk_review.py",
  "../../tools/attention_benchmark.py",
  "../../tools/attention_review.py",
  "../../tools/alert_benchmark.py",
  "../../tools/alert_review.py",
  "../../tools/v0_replay.py",
  "../../tools/rescue_gpu_validate.py",
  "../../tools/rescue_runtime.py",
  "../../tools/rescue_gpu_probe.py",
  "../../tools/rescue_cadence.py",
  "../../tools/rescue_trace.py",
  "../../tools/alpha_trace.py",
  "../../tools/alpha_residuals.py",
  "../../tools/alpha_roll_probe.py",
  "../../tools/alpha_candidate_isolate.py",
  "../../tools/alpha_compute_batch.py",
  "../../tools/alpha_realtime_report.py",
  "../../tools/alpha_offline_gate.py",
  "../../tools/alpha_rotated_clip.py",
  "../../tools/alpha_rotated_suite.py",
  "../../tools/alpha_offline_comparison.py",
  "../../tools/alpha_freeze_engine.py",
  "../../tools/alpha_demo_index.py",
  "../../tools/alpha_field_gateway.py",
  "../../tools/alpha_field_worker.py",
  "../../tools/alpha_field_smoke.py",
  "../../tools/wireless_alpha.py",
  "../../tools/product_dataset.py",
  "../../tools/rescue_export.py",
  "../../tools/rescue_tracking.py",
  "../../tools/rescue_profile.py",
  "../../tools/v0_analyze.py",
  "../../tools/v0_review.py",
  "../../tools/v0_ablation.py",
  "../../tools/v0_reasoning.py",
  "../../tools/evaluate_v0.py",
  "../../tools/v02_audit.py",
  "../../tools/v02_view_probe.py",
  "../../tools/v02_model_probe.py",
  "../../tools/v02_populations.py",
  "../../tools/acquire_offline_teacher.py",
  "../../tools/v02_candidate_population.py",
  "../../tools/v02_picodet_population.py",
  "../../tools/v02_teacher_population.py",
  "../../tools/v02_score_population.py",
  "../../tools/semantic_event_ledger.py",
  "../../tools/alpha_semantic_probe.py",
  "../../tools/alpha_continuous_replay.py",
  "../../tools/alpha_compare_continuous.py",
  "../../tools/alpha_semantic_score.py",
  "../../tools/v02_compare_population.py",
  "../../tools/acquire_v02_models.py",
];
const commands = {
  check: [
    ["-m", "ruff", "format", "--check", "."],
    ["-m", "ruff", "check", "."],
    ["-m", "ruff", "format", "--check", ...toolPaths],
    ["-m", "ruff", "check", ...toolPaths],
    ["-m", "mypy"],
    ["-m", "pytest"],
  ],
  format: [["-m", "ruff", "format", ".", ...toolPaths]],
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
