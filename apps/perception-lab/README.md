# Sentinel perception laboratory

Task008 depth adapters and replay configuration are documented in
[depth runtime](../../docs/depth/DEPTH_RUNTIME.md). Download verified checkpoints
explicitly using `tools/download_depth.py` from the repository root. Model acquisition
is separate from offline inference and normal CI. The
[depth report](../../docs/research/results/task008-depth-2026-10-19.md) distinguishes
tested geometry, measured research outputs and unvalidated physical accuracy.

Local desktop R&D infrastructure; no production detector, risk score or safety
claim. Python 3.12 and a 64-bit JDK 21 are required. The Python/JVM architectures
must match. Guardian geometry executes in the existing Java core.

From the repository root in PowerShell:

```powershell
python --version
java -version
python -m venv apps/perception-lab/.venv
apps/perception-lab/.venv/Scripts/python.exe -m pip install -r apps/perception-lab/requirements.lock
apps/perception-lab/.venv/Scripts/python.exe -m pip install --no-deps -e apps/perception-lab
apps/perception-lab/.venv/Scripts/python.exe -m pip check
npm run check:core
npm run check:lab
apps/perception-lab/.venv/Scripts/python.exe -m perception_lab.cli replay --help
apps/perception-lab/.venv/Scripts/python.exe -m perception_lab.cli inspect --calibration configs/calibration.synthetic.example.json --u 4 --v 3
npm run verify
```

On Linux use `.venv/bin/python` in place of `.venv/Scripts/python.exe`.
The root runner selects the platform automatically. No activation is required.
Install/download happens only during setup, never replay. The test suite generates
a tiny FFV1/Matroska VFR fixture locally. No webcam, GUI, model or dataset is needed.

Copy `configs/perception-lab.example.json` and supply a local video and its actual
calibration. The example calibration is **synthetic 8x6**, not usable for real
cameras. All relative paths, including CLI overrides, resolve against the config
directory. Example rates are demonstration settings, not production targets.

```powershell
apps/perception-lab/.venv/Scripts/python.exe -m perception_lab.cli replay --config configs/perception-lab.example.json --headless
```

Optional flags: `--input`, `--calibration`, `--record-session`, `--output`, `--start`
and `--end` (inclusive/exclusive integer nanoseconds on the media timeline).
Use `visualization: true` for the optional standard-library Tk viewer; `--headless`
overrides it. Tk must be installed separately on systems that omit it. Closing the
viewer cancels replay. No GUI dependency is imported in headless runs.

Recording and debug frames default OFF. Recording creates a unique UUID directory
under the selected output root with `manifest.json`, `frames.jsonl`, `metrics.json`.
Debug PPM requires both `debug_every_n` and `debug_max_frames` plus recording.
Protect those opt-in artifacts as sensitive media. Input videos are never copied.

See [architecture](../../docs/perception/PERCEPTION_LAB_ARCHITECTURE.md),
[lifecycle](../../docs/perception/FRAME_LIFECYCLE.md), and
[benchmark interpretation](../../docs/perception/BENCHMARKING.md).

Task 006 adds optional local YOLO and RT-DETR research adapters. Install their
separate `requirements-models.txt` only when running model experiments. The
`requirements-models.lock` records the tested Windows CPU environment; generic CI
uses the smaller `requirements.lock` and does not download models. See
[detector benchmarking](../../docs/perception/DETECTOR_BENCHMARKING.md) and
[licensing](../../docs/perception/DETECTOR_LICENSING.md). Normal replay still defaults
to NoOp. Never use the synthetic calibration as real camera calibration.

Task007 opt-in tracking uses the existing detector configuration with its proposal
`confidence` set to `0.1`, plus the following top-level configuration:

```json
{
  "tracker": {
    "schema_version": 1,
    "tracker_type": "two_stage",
    "motion_model": "alpha_beta",
    "publication_threshold": 0.25,
    "recovery_threshold": 0.1
  }
}
```

This is a fragment to merge into a valid replay configuration, not a standalone
configuration. PicoDet uses publication .25; YOLOX uses .15. Model paths and SHA256
remain in `detector`; tracking imports neither adapter. Prediction runs on every
processed frame and never means a detector observation occurred. Session recording
with tracking writes schema2; ordinary replay retains schema1.

See [tracking contracts](../../docs/tracking/TRACKING_ARCHITECTURE.md),
[cadence](../../docs/tracking/DETECTOR_CADENCE.md), and the
[300-frame review workflow](../../datasets/tracking_v1/README.md).
These settings remain provisional until reviewed tracking evidence supports selection.

## Task009 motion

Optional `motion` configuration enables LK or DIS, frame-pair observations and conservative visual rotation/Essential estimation. Add an `optical_flow` scheduler interval; use RGB NHWC. See [motion architecture](../../docs/motion/OPTICAL_FLOW_ARCHITECTURE.md) and [evaluation](../../docs/motion/MOTION_EVALUATION.md). No model weights are needed. OpenCV is pinned in the standard lab lock file.

Use `configs/perception-lab.motion.example.json` as a template, replacing its video and synthetic calibration with explicitly identified local inputs. Run replay with the existing CLI. Run `npm run verify` only after replay exits, because Windows locks the JVM's JAR during execution. Research depth/IMU estimators are explicit APIs, not automatic runtime fusion. Task010 has not started.
