> Historical checkpoint. For the subsequent release-closure work and current gates, see [Alpha V1.1 final report](VISION_ALPHA_V1_1_FINAL.md).

# Alpha V1.1 field diagnostic readiness

Final checkpoint: **2026-11-18**. Local implementation and recorded-source
regression are finished. **Overall verification and readiness remain HOLD**
because the dependency security gate fails. Alpha V1.1 is not promoted.

The original phone failure was not recorded. No physical root cause, recall
improvement or production safety qualification is claimed.

## 1. RAM diagnosis and remediation

The host snapshot showed 15.64 GiB physical RAM, 5.11 GiB available and 15.70 GiB
committed against a 25.14 GiB commit limit. Windows reports an automatically
selected pagefile (`?:\\pagefile.sys`). Performance-counter-based pagefile queries
were unavailable; commit figures came from Windows GetPerformanceInfo. Initial
GPU readings were 6,144 MiB total, zero MiB used and 6,001 MiB free; driver-reserved
memory accounts for the difference. No duplicate VISION benchmark workers were
found in the visible process list. No unrelated application was terminated.

The earlier startup refusal was an available-system-RAM guard, not proof of a
model leak. Replay did unnecessarily instantiate two copies of PicoDet. It now
uses **one native session in an isolated child**, comparing baseline inference
with observer-enabled inference on that same session. The parent loads no model.
The **3 GiB startup and 2 GiB runtime guards were preserved**.

The final synthetic JPEG smoke used about 177 MiB peak worker RSS and no model
VRAM. This is software evidence, not real phone footage. GPU engine runs peaked
at approximately 1.14–1.15 GiB process-tree RSS; the full-source run peaked near
1.31 GiB. Minimum sampled device-free VRAM was at least 5,781 MiB. These are
device-wide measurements, not a claim of precise per-process GPU allocation.

Evidence:
`benchmark-results/field-loop-memory-20261117.json`,
`benchmark-results/field-readiness-isolated-recompute/case/detector-replay.json`,
`benchmark-results/field-readiness-regression/corrected-batch.json`.

## 2. Real-model replay and equivalence

The isolated real PicoDet smoke passed original JPEG checksum, session, sequence,
timestamp and recorded-rotation checks. It requires the pinned release/model
hashes and records configuration, transform identity and stage timings.
Recomputed detections remain separate from recorded decisions. Candidate
inference-stage timing includes observer work; single warmup timing pairs are
not an isolated-kernel performance measurement.

Both GPU offline arms processed **18,000 matching source frames**, with matching
identity hashes and **zero differing detector outputs**. Each decoded 18,001
source frames, processed 18,000, excluded one boundary frame and failed zero.
No detector confidence or stability threshold was relaxed.

Short clips lack the complete pre-clip tracker, semantics, policy and original
scheduling state. Full temporal-engine equivalence therefore remains unavailable.

Evidence: `benchmark-results/field-readiness-regression/comparison.json`.

## 3. Corrected diagnostic overhead and realtime regression

All three ten-minute engine runs completed. The corrected observer/recording
runs generated diagnostics for **every** processed update, including after the
write budget filled.

| Metric                              | Baseline | Observer | Observer + recording |
| ----------------------------------- | -------: | -------: | -------------------: |
| Processed updates                   |    2,999 |   12,050 |               12,215 |
| Effective updates/s                 |     4.99 |    20.08 |                20.36 |
| Publication P50, ms                 |    335.3 |     54.0 |                 53.6 |
| Publication P95, ms                 |    506.1 |    155.3 |                154.0 |
| Publication P99, ms                 |    582.9 |    190.6 |                185.7 |
| Acquisition frames skipped/replaced |   15,001 |    5,950 |                5,785 |
| Pipeline failed updates             |        0 |        0 |                    0 |
| Text-sink expiry violations         |        0 |        0 |                    0 |
| Input queue peak                    |        1 |        1 |                    1 |
| Benchmark trace writer queue peak   |        1 |        2 |                    2 |

Per-object evidence generation averaged **0.95 ms/update** without recording and
**0.92 ms/update** with recording. Recording serialization averaged an additional
**0.18 ms/update**. The diagnostic writer is synchronous, with no separate queue.
The benchmark trace writer is separately bounded to 16 entries.

The predeclared engineering screen passed: candidate throughput at least 90% of
baseline, publication P95 within baseline +10% +5 ms, no text-sink expiry
violations and input queue bounded to one. Sequential runs have substantial
background-load/thermal confounding: faster results do **not** establish a
speed improvement caused by diagnostics, semantic correctness or physical safety.
This is an engine comparison, not phone transport or acoustic delivery timing.

Detailed recording is bounded: 308 updates were retained and 11,907 omitted
after budget/size limits in the corrected recording arm. Generation continued
for all 12,215 updates. Do not present these results as unlimited full-session
evidence retention.

The initial harness incorrectly stopped generation after its write budget filled.
That was corrected and both affected ten-minute arms were rerun. Initial artifacts
remain preserved and are superseded for diagnostic overhead conclusions.
An initial one-packet budget overshoot was also fixed; the corrected diagnostic
file was 4,190,305 bytes, below 4 MiB.

Evidence: `benchmark-results/field-readiness-regression/corrected-comparison.json`
and the corresponding `diagnostic-summary.json` files.

## 4. Full-source and canonical checks

The complete 1,498.8333-second archived video replay finished successfully:
27,306 processed updates, two pipeline drops, zero failures, and source coverage
through 1,498.8 seconds. The supervisor observed clean shutdown with no RAM/VRAM
reserve stop. This run establishes full-source coverage; corrected ten-minute
runs above supply the all-update overhead comparison.

The fixed **60-alert/188-event** population and original probe checksums passed
rescoring. This reused historical offline-context probe outputs. It is not a
fresh 60/188 physical accuracy qualification, and IoU correspondence is not
independent object-identity truth. Original denominators were preserved.

Evidence: `benchmark-results/field-readiness-full-source/replay/manifest.json`,
`benchmark-results/field-readiness-full-source-process/process-summary.json`,
`benchmark-results/field-readiness-canonical-rescore.json`.

## 5. Causal evidence, capture and export fixes

- The opt-in detector observer preserves inference/filtering while recording
  source identity, model/configuration hashes and bounded accepted/rejected boxes
  in original-image coordinates. Embedded vendor pre-NMS evidence remains UNKNOWN.
- Tracking diagnostics record actual association-cost gate reasons, update
  diagnostics, removed generations and bounded track outcomes without changing
  assignment. A finite cost is not presented as a confirmed assignment.
- Exact entity-ID joins expose source observations, corridor, semantics,
  interaction, risk, attention and intent. Gateway rejections distinguish
  missing/upstream lineage, mismatched lineage, unavailable source captures and
  expiry. Contributing reasons and unknown evidence remain distinct.
- Oversized per-publication diagnostics now retain partial evidence with explicit
  omission counters. Cost observations are bounded at 64, track outcomes at 16,
  and entity/alert records also have limits. The ledger is **PARTIAL**, not an
  exhaustive trace of every physical object or every rejected candidate.
- Gateway recording has an **8 MiB total-event budget**, plus its event-count and
  detailed-entity limits. It stops cleanly, preserves retained evidence and reports
  full status. The PC portal shows status and retained bytes when refreshed.
  This fixes exports that could otherwise exceed importer limits.
- Android retains opt-in encrypted two-second/24-frame/4 MiB clips, recent capture
  selection, explicit export/deletion and protection against silently replacing a
  saved clip. Stopping revokes buffering consent.
- Imports reject mixed session, sequence/time correspondence and rotation errors.
  The authenticated Lab checks recomputed session/frame/time/JPEG identities before
  exposing separately stored recomputation. Private media needs explicit permission.

No original physical failure was reconstructed. No model replacement or training
was performed.

## 6. Verification and security blocker

| Check                                               | Final result                                                                        |
| --------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Python                                              | 1,379 tests passed; formatting, Ruff and mypy passed                                |
| Guardian core                                       | 195 tests; build and static analysis passed                                         |
| Web                                                 | 45 tests; lint, strict type checks and production build passed                      |
| Spring API                                          | 3 tests; package and SpotBugs passed                                                |
| Android                                             | Debug assembly, 12 JVM tests and lint passed                                        |
| Gateway/portal                                      | Recording, export, origin rejection, expiry/reconnect and byte-limit tests passed   |
| Integration smoke                                   | Passed separately after the security gate stopped the aggregate command             |
| Git whitespace check                                | Passed; existing CRLF normalization notices are not whitespace failures             |
| Interactive Lab                                     | UNVERIFIED: computer-use permission was denied; user elected to leave it unverified |
| Physical Android/Keystore/export/deletion/Bluetooth | UNVERIFIED on hardware                                                              |
| Dependency audit                                    | **FAIL: one root advisory propagating to 16 high-severity dependency findings**     |
| Full `npm.cmd run verify`                           | **FAIL at the security gate**, despite preceding checks passing                     |

The blocker is
[GHSA-fc5q-39xc-vjpf](https://github.com/advisories/GHSA-fc5q-39xc-vjpf):
picomatch through 4.0.7 can exhibit regular-expression denial of service with
crafted repeated extglob patterns. The advisory lists no patched version.
The registry and [upstream releases](https://github.com/micromatch/picomatch/releases)
reported 4.0.7 as latest when checked on 2026-11-18. Installed paths include
ESLint/fast-glob and Vitest/Vite dependencies. Exploitability of an externally
reachable application path was not demonstrated; that is not a waiver.

Recommended resolution: adopt a verifiably patched upstream release or separately
reviewed replacement, regenerate the lockfile, rerun web/build/security checks and
the aggregate gate. Do not suppress the advisory, falsify package versions, apply
unreviewed vendor patches or downgrade unrelated frameworks to manufacture a pass.
No dependency exception was added.

One intermediate Maven attempt failed because an active replay held the Guardian
JAR open. The later post-regression build succeeded after workers exited.
Always finish inference before cleaning/rebuilding that JAR.

Logs:
`benchmark-results/field-readiness-post-regression-verify.log`,
`benchmark-results/field-readiness-bounded-audit.json`,
`benchmark-results/field-readiness-final-smoke.log`,
`benchmark-results/field-readiness-android.log`.

The frozen release/archive hashes and all **115 archived runtime entries**
matched: `benchmark-results/field-readiness-frozen-check.json`.

## 7. Supervised field guide and remaining blockers

Use [the diagnostic capture guide](../../field/VISION_DIAGNOSTIC_CAPTURE_GUIDE.md)
for exact local commands and six stationary or controlled sighted-developer cases:
correct naming, generic Object, visibly missed object, relevant silence, correct
silence and naturally observed stale/unnecessary warnings. Do not rely on VISION
for navigation. Export clip, History and matching gateway data immediately and
independently annotate objects actually present.

Real captures should be kept in a non-synced local directory, such as LocalAppData,
rather than this OneDrive-backed repository. Git ignore rules do not control
filesystem synchronization.

Remaining blockers are the dependency advisory, independent phone evidence and
hardware checks. Interactive browser review remains explicitly waived/unverified.
No additional GPU regression is currently required unless code or experiment
conditions change.

## Final verdicts

REAL_MODEL_REPLAY_PASSED: YES.

MEMORY_GUARD_PRESERVED: YES.

BASELINE_DETECTOR_OUTPUT_IDENTICAL: YES (18,000 matched offline frames).

PER_OBJECT_CAUSAL_LEDGER_COMPLETE: PARTIAL.

LAB_INTERACTIVE_VERIFIED: NO.

DIAGNOSTIC_OVERHEAD_MEASURED: YES (bounded engine diagnostics, not phone transport).

OFFLINE_REGRESSION_PASSED: YES.

REALTIME_REGRESSION_PASSED: YES (recorded-source engineering screen).

FULL_REPOSITORY_VERIFICATION_PASSED: NO (dependency security gate).

SOFTWARE_FIELD_CAPTURE_READY: NO (security hold; functional checks passed).

PHYSICAL_FIELD_CAPTURE_VERIFIED: NO.

READY_FOR_NEW_DIAGNOSTIC_FIELD_SESSION: NO (security hold).

REAL_FIELD_CAUSES_CONFIRMED: NO.

ALPHA_V1_1_PROMOTED: NO.
