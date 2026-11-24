# VISION V0.2 progress — 2026-10-28

V0.2 is in progress. This is an engineering checkpoint, not a completion or adoption report. Task019 has not started.

## Preserved baseline

`benchmark-results/v02/VISION_V0_RESCUED_BASELINE` contains the rescued source archive and manifest. All 612 archived source hashes were rechecked on October 28 with zero mismatches. Working source changes are intentional V0.2 experiments; the archive is not overwritten. The rescued 4.399 Hz profile and its 60 accepted generic alerts remain the comparison baseline.

## Implemented and tested

- Immutable generic entity observations, arbitrary semantic concepts, explicit confidence basis, bounded ontology resolution, and a provider adapter that retains regions whose semantic name is unavailable. Joint detector scores are not independent objectness probabilities.
- Opt-in geometry-first tracking admission/association. Frozen V0 remains the default. The legacy Detection/ObjectClass boundary is still present downstream.
- Cardinal camera canonicalization using existing Guardian geometry, rotated ideal intrinsics/camera basis, exact frame identity, and composition into detector preprocessing. Tests cover four cardinal rotations and inverse mapping after letterboxing. Arbitrary roll and runtime integration remain pending.
- Bounded deterministic view diagnostics with versioned configuration. They distinguish exposure/texture evidence from unsupported guesses about physical occlusion or camera heading. Runtime gating is not wired yet.
- Checksum-pinned setup-only model acquisition and tests for corrupt/truncated/oversized downloads, idempotence, and preserving existing mismatched files. Weights remain in ignored local benchmark storage.

## Measured view diagnostics

The probe decoded the full source video and evaluated 1,499 frames at one-second intervals, ending at source time 1,498 s. It skipped conversion for 43,466 intervening frames and reported no source issues. Diagnostic P95 was 2.662 ms, mean 1.740 ms; full probe wall time was 325.506 s. These timings exclude decoding and output writes from the diagnostic duration.

1,495 samples had no configured diagnostic problem; four were flagged UNUSABLE. There are no reviewed usability labels, so this is not a classification-accuracy result. Source/configuration hashes and frame diagnostics are recorded in `benchmark-results/v02/view-probe-01`.

## Offline model smoke tests

All candidates used the same frame at 37 seconds, CPU FP32, two intra-op threads, one warm-up, and five repeated measured predictions. Python network access was denied before vendor imports; package auto-installation and telemetry sync were disabled. This is not an OS isolation guarantee. Candidate assets matched published release checksums before loading.

| Research candidate    | Embedded vocabulary | Candidate regions | Five warmed call range |
| --------------------- | ------------------: | ----------------: | ---------------------: |
| YOLOE-26n prompt-free |               4,585 |                24 |     189.129–197.233 ms |
| YOLOE-11s prompt-free |               4,585 |                26 |     132.049–164.515 ms |
| YOLOv8s-Worldv2       |                  80 |                 6 |       72.300–88.290 ms |

The single-frame repeated measurements do not establish recall, specificity, stable semantics, GPU performance, whole-pipeline freshness, or a model ranking. YOLO-World has not yet exercised custom prompts. No candidate was selected for the product. Model registry and license evidence are in `configs/perception/research-models-v02.json` and `V02_MODEL_LICENSES.md`. Detailed outputs are under `benchmark-results/v02/*-smoke-01`.

The first nano probe exposed a vendor settings-directory fallback. The probe now creates its configured local directory before import; the generated settings file was moved into that probe's ignored output. Subsequent runs used their intended directories.

## Executed verification

The continuation added generic world/reasoning integration, bounded track fusion,
the latest-only semantic worker and stable-concept alert wording. The complete
perception suite passed 1,189 tests (`benchmark-results/v02/lab-final-03.log`),
with Ruff and strict mypy passing on 105 source files. The population extraction
test subsequently passed separately. `verify-05.log` completed repository
verification successfully; its earlier perception snapshot contained 1,172 tests,
so the later perception run is the evidence for the final semantic alert changes.

The final `verify-06.log` rerun passed formatting, 193 core tests/static analysis,
Ruff, strict mypy (105 source files), all 1,190 perception tests, web lint/type
checks and 31 web tests. The web build then encountered EPERM deleting a read-only
generated `.next/static` directory. After removing only that verified generated
directory, the production web build passed (`web-build-07.log`). API, advisory and
smoke checks subsequently passed (`api-07.log`, `security-07.log` and
`smoke-07.log`, exit 0). The API ran three tests, npm reported no advisories, and
production loopback checks passed including concurrent health and API outage
handling. Final passing suite total is 1,417 across these runs. Android was not
changed or rerun. `git diff --check` passed; V0 archive hashes remain 612/612.

`benchmark-results/v02/populations-02.json` freezes all 60 accepted alerts and all
188 canonical events, with original evidence/publication timestamps and complete
reference observations. It includes input hashes and marks reference limitations.
There are 5,313 reference observations and no missing alert-to-entity links.
World boxes are explicitly identified as potentially predicted; they must not be
silently treated as original observed boxes. `populations-01.json` is superseded
because it lacked that distinction. This is population preparation, not a model
comparison or semantic-recovery result.

The RTX 3050 was rechecked with the installed NVIDIA utility: 6,144 MiB VRAM,
driver 592.27. This is hardware availability, not candidate GPU qualification.
Current real-model adapters deliberately report observation quality UNKNOWN;
the synthetic GOOD-quality fixtures do not authorize a real-model policy. That
policy must be explicitly evaluated before claiming specific real-world alerts.

Reproduce population extraction without overwriting an existing output:

```powershell
apps/perception-lab/.venv/Scripts/python.exe tools/v02_populations.py --run benchmark-results/v0-rescue/realtime-06-gpu-no-depth --references datasets/tracking_v1/sentinel-track-review-prototype.json --output benchmark-results/v02/populations-new.json
```

### Earlier checkpoint

`npm run verify` completed successfully (`benchmark-results/v02/verify-04.log`): formatting, core static analysis/tests, perception lint/type checks/tests, web lint/type checks/tests, production web/API builds, npm advisory check, and loopback smoke checks. No npm advisories were reported by that run.

Final review then strengthened entity IDs against cross-source/provider collisions. The affected tests and complete lab checks were rerun successfully (`benchmark-results/v02/lab-final-02.log`). Current passing suite counts are 193 core, 1,148 perception, 31 web, and 3 API tests: 1,375 total across those runs. Android was not rerun in this continuation and is not included in that total. The single-frame smoke artifacts predate the ID-strengthening change; inference measurements and labels were not changed by it.

## Remaining acceptance work

1. Qualify the implemented generic entity path on real model outputs. Synthetic integration now covers known, unknown and arbitrary concepts through all reasoning stages; fresh stable semantics can authorize bounded alert wording without changing interruption gates. Remaining compatibility dependencies are documented in `V02_OBJECTNESS.md`.
2. Benchmark the implemented bounded track semantic fusion and asynchronous enrichment on existing tracks. Software tests cover expiry, disagreement, provider bounds, replaced identities, nonblocking pipeline progress and original-entity result application. A real semantic provider/runtime profile still needs integration and qualification.
3. Acquire the offline teacher, evaluate prompted versus prompt-free strategies, and measure candidates against PicoDet on identical inputs. CPU smoke tests cannot select the rescued GPU replacement.
4. Complete arbitrary-roll/gravity handling, user-heading separation, auto-mount research and downstream rotation tests. Wire view health to capability degradation.
5. Run the same 60-alert and 188-event comparisons, complete full-video perception and rotated-video experiments, and rerun offline/realtime regressions. The full-file diagnostics probe does not satisfy the full-pipeline run requirement.
6. Complete adversarial integration review and the requested final A–BB report. Then assess readiness for the demo/field/human-review phase.

No semantic-recovery improvement or real-time regression conclusion is available yet. Human usefulness, physical accuracy, production safety, and production readiness remain unvalidated. The next planned phase is `V0_DEMO_FIELD_APP_AND_HUMAN_REVIEW`, after the V0.2 gates pass.
