# Alpha V1.1 final release-closure engineering report

2026-11-18. **Release HOLD**; engineering verification status below is explicit.
This report supersedes the earlier field-root-causes checkpoint for this mission.

## Existing evidence preserved

The opt-in observer, bounded tracking/entity diagnostics, encrypted Android short
clip, private Lab, exact-byte import/recompute and recorded-source comparisons were
already implemented. Frozen manifest SHA256:
`ecd83215cc8f8e144ec9126b61415e8ca38b854a4126cfdbc6e52d55affa6254`.
Runtime archive SHA256:
`c4a928b29f9f6cff2b5281c65bc8f4122d6c5396972ffce3077277f522d7e2ae`.
Both hashes were rechecked this mission. Previous archive comparison checked all
115 runtime entries (`benchmark-results/field-readiness-frozen-check.json`).

PicoDet: `4b717e3f68f170fafd922c3c7978e52b6ad2ab3615d26b407e7d9aba44eb790f`.
Segmentation: `2f0da8aec33e30c25299257a5b54243508528dda521c5c2614d6d250b4cb8205`.
No model files or frozen archives were replaced.

## Changes and confirmed defects

- Offline import now retains later publications for an exact detector source
  session/sequence. It preserves separate publication identity, limits these
  references to 16, checks the two-second capture window and 2 MB joined-packet
  bound before writing. This repairs missing diagnostic evidence, not recall.
- Added a bounded offline 20-stage causal-reference schema. At most 16 pointers
  per stage; unavailable pre-NMS/physical/acoustic evidence stays unavailable.
  No physical-object miss is inferred from an absent or suppressed result.
- Viewer: playback stops/restarts correctly; frame changes clear entity selection;
  malformed clocks/packet identities/boxes fail closed; empty cases, retry and
  disabled/unavailable media have explicit states. Exact-source later detector
  publications can supply overlays without mislabelling the current frame.
- Android: visible buffer/saved-clip state, matching session, explicit encrypted
  save and readable-export confirmation, protected replacement, and PC recording
  status instructions. The PC operator page owns the actual FULL indicator.
  Consent, two-second/24-frame/4 MiB bounds and local encryption are preserved.
- Portal: bounded draining of small rejected POST bodies avoids Windows resetting
  an unauthorized request before delivering its 403. Origin checks remain intact.

## Security and browser QA

Full npm audit: 16 high findings from one unpatched picomatch advisory; zero
critical. Latest official release remains 4.0.7. Supported latest Vitest still
depends on the affected package. No suppression or unsafe replacement adopted.
See [security analysis](../../security/VISION_DEPENDENCY_ADVISORY_STATUS.md).

Isolated Playwright 1.65.1 / downloaded Chromium, synthetic images only, private
loopback server and ephemeral secret. The initial **15 interactive checks passed**:
anonymous page/media rejection, wrong/correct login, accepted/rejected overlays,
stage/feedback/recomputation visibility, entity selection, pause/seek/step/replay,
refresh, mobile width, disconnect/retry, corrupt index, empty case, media disabled,
and no uncaught browser errors. Desktop/mobile/media-disabled screenshots are in
`benchmark-results/final-closure-browser/`. Mobile screenshot was visually inspected.

An expanded final rerun after additional validation changes timed out compiling
the login page during severe host RAM pressure; it is not counted as a pass.
The earlier passing console output is preserved in
`benchmark-results/final-closure-browser.log`; latest attempt:
`benchmark-results/final-closure-browser-final.log`.

Reproduce using synthetic fixtures only:

```powershell
npm.cmd install --prefix .tools/browser-qa --no-audit --no-fund --save-exact playwright@1.65.1
.\.tools\browser-qa\node_modules\.bin\playwright.cmd install chromium
node tools/diagnostic-browser-qa.mjs
```

The install flag skips an auxiliary installation audit, not the repository release
security gate. Root `npm run security` remains mandatory and failing.

## Physical causes and quality claims

ADB listed no attached devices: **BLOCKED_NO_DEVICE**. No physical CameraX,
Keystore, SAF export, Wi-Fi, Bluetooth or TTS route was validated this mission.
Original phone failure: unrecorded, cannot reconstruct. Independently annotated
new field cases: **0**. No model/semantic/risk fix is justified by that absence.

Specific precision, broad-group precision, relevant-object recall, generic-warning
appropriateness, missed-important-warning and unnecessary-interruption changes
are **UNMEASURED**. No accuracy-gain percentage is reported. Existing canonical
60/188 historical scoring is not new physical validation. See the separate
[object](../VISION_OBJECT_ROOT_CAUSE_ANALYSIS.md) and
[semantic](../VISION_SEMANTIC_ROOT_CAUSE_ANALYSIS.md) analyses.

## Reused regression results

18,000 exact source-frame detector comparisons: **0 differing outputs**.
Full source: **1,498.8333 seconds, 27,306 updates, 2 pipeline drops, 0 failures**.

| Ten-minute arm       |      Hz | Publication p95 ms |  p99 ms |
| -------------------- | ------: | -----------------: | ------: |
| Frozen baseline      |  4.9949 |            506.051 | 582.874 |
| Diagnostic observer  | 20.0805 |            155.274 | 190.632 |
| Observer + recording | 20.3555 |            153.991 | 185.735 |

Sequential arms have thermal/background-load confounding: **no causal 4x speedup
claim**. All had zero delivered-after-expiry violations, zero pipeline failures
and input queue peak one. Evidence generation was approximately 0.92–0.95 ms per
update; recording serialization approximately 0.18 ms. Bounded recording omitted
later updates after its byte budget; it did not persist every update.

Artifacts: `benchmark-results/field-readiness-regression/comparison.json`,
`corrected-comparison.json`, `corrected-batch.json`, and
`benchmark-results/field-readiness-full-source-process/process-summary.json`.
No expensive GPU rerun was needed for these offline/UI changes. RTX 3050 6 GB
snapshot: 6,144 MiB total, 6,001 MiB free. Real-model RAM guards remain 3 GiB at
startup and 2 GiB while running.

## Verification status

Initial full run: Guardian **195 passed**, Python **1,381 passed / 1 failed**.
The failure was Windows connection abort on a rejected portal POST; isolated
reproduction passed, and the bounded response-handling fix was then applied.
Final affected import/ledger/portal tests: **12 passed** after the response-handling fix (`benchmark-results/final-closure-targeted-python.log`). Ruff lint and formatting checks passed for all five affected Python files. Strict mypy for the added module passed. The full changed-tree recheck remains required.

Android: **12 JVM tests passed**, assembly and lint passed in 3m 1s:
`benchmark-results/final-closure-android.log`.
Earlier checkpoint: web 45 and API 3 tests passed. Those counts are not substituted
for this mission's final changed-tree checks.

Final repository rerun was stopped at formatting when available RAM fell to
**0.67 GiB**; only the agent-owned verification process tree was stopped. The user
was asked to free memory. Logs: `final-closure-verify.log` and
`final-closure-verify-retry.log`. Public build, final web/API/smoke and final browser
rerun remain pending. Full verification cannot be marked passing even after these
checks until the external dependency advisory is legitimately resolved.

## Release verdict

See [release decision](../../releases/VISION_ALPHA_V1_1_RELEASE_DECISION.md).
Diagnostic functionality, security clearance, physical readiness and demonstrated
perception improvement are separate gates. Alpha V1.1 is **not promoted**.
Production safety and unsupervised public deployment remain **NO**.

## Explicit final verdicts at this checkpoint

| Verdict                                 | Status                                            |
| --------------------------------------- | ------------------------------------------------- |
| SECURITY_ADVISORY_RESOLVED              | NO                                                |
| FULL_SECURITY_GATE_PASSED               | NO                                                |
| LAB_INTERACTIVE_VERIFIED                | NO for final tree; earlier 15-check pass retained |
| PER_OBJECT_CAUSAL_LEDGER                | PARTIAL                                           |
| ANDROID_SOFTWARE_VERIFIED               | YES                                               |
| REAL_ANDROID_HARDWARE_VERIFIED          | NO                                                |
| ENCRYPTED_FIELD_CAPTURE_VERIFIED        | PARTIAL � software only                           |
| READY_FOR_CONTROLLED_FIELD_CAPTURE      | NO                                                |
| REAL_FIELD_ROOT_CAUSES_CONFIRMED        | NO                                                |
| GENERIC_ALERT_ROOT_CAUSES_MEASURED      | NO                                                |
| MISSED_OBJECT_ROOT_CAUSES_MEASURED      | NO                                                |
| SEMANTIC_CORRECTNESS_IMPROVED           | UNMEASURED                                        |
| RELEVANT_OBJECT_RECALL_IMPROVED         | UNMEASURED                                        |
| ALERT_USEFULNESS_IMPROVED               | UNMEASURED                                        |
| REALTIME_REGRESSION_PASSED              | YES � unchanged engine evidence reused            |
| OFFLINE_REGRESSION_PASSED               | YES � unchanged engine evidence reused            |
| FULL_REPOSITORY_VERIFICATION_PASSED     | NO                                                |
| ALPHA_V1_1_DIAGNOSTIC_SOFTWARE_COMPLETE | NO � final verification pending                   |
| ALPHA_V1_1_PROMOTED                     | NO                                                |
| PRODUCTION_SAFETY_VALIDATED             | NO                                                |
| UNSUPERVISED_PUBLIC_DEPLOYMENT_READY    | NO                                                |

## Remaining executable verification after memory is freed

Run sequentially from the repository root, with approximately 4 GiB RAM free.
Do not run a browser development server concurrently with the production build.
No further GPU job is required by the present code changes.

```powershell
npm.cmd run verify
# The known advisory intentionally fails the security stage. Run the omitted
# smoke separately; do not interpret that as making verify pass.
npm.cmd run smoke
npm.cmd run build:public
node tools/diagnostic-browser-qa.mjs
git diff --check
```

Then update this report with actual exit statuses, final counts and browser
artifacts. Do not substitute this command list for executed verification.
