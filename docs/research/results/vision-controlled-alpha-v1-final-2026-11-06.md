# Controlled Alpha V1 closure — November 6, 2026

Scope: local supervised engineering prototype. This release does not qualify
VISION as a navigation aid. Task019 has not started. The next phase is
`CONTROLLED_HUMAN_REVIEW_AND_FIELD_EVALUATION`.

## Evidence and comparison

The frozen engine manifest is
`benchmark-results/v02/VISION_CONTROLLED_ALPHA_V1/manifest.json`, SHA-256
`ecd83215cc8f8e144ec9126b61415e8ca38b854a4126cfdbc6e52d55affa6254`.
It preserves the measured runtime, model/configuration hashes and evidence.
Field consumers are separately tested; changing them does not silently replace
the frozen inference implementation. Evidence and media are local ignored files,
so a clean clone alone cannot reproduce the recording or GPU qualification.
The field/web source hashes, APK hash, verification log hashes and explicit
external blockers are recorded in
`benchmark-results/v02/alpha-software-closure-2026-11-06.json`, SHA-256
`6e59c6905011efca6ca37d160642cfd4dd779a6f2a594d877ce8a3da9a776ec4`.

| Comparable first 600 source seconds      | Rescued V0 |    Alpha V1 |
| ---------------------------------------- | ---------: | ----------: |
| Published updates                        |      2,641 |       6,300 |
| Effective updates/source second          |      4.399 |       10.50 |
| Publication P50                          | 264.379 ms |  125.572 ms |
| Publication P95                          | 567.211 ms |  257.657 ms |
| Publication P99                          | 716.824 ms |  307.794 ms |
| Frame failures                           |          0 |           0 |
| Specific / group / generic presentations | 0 / 0 / 60 | 13 / 2 / 58 |

This is about 2.39 times the update rate and 54.6% lower P95. Different realtime
frame admission prevents interpreting this as an accuracy improvement.

The complete 1,498.8-second recording produced 18,541 updates (12.368 Hz),
P95 241.947 ms and P99 294.941 ms. Maximum age was 1,552.570 ms; there is no
worst-case realtime guarantee. Delivered presentations were 37 specific,
2 group and 133 generic. All 172 deliveries preceded their deadlines; 70
upstream candidates expired. No ordinary alert was delivered on 141 unusable
view updates. Peak process-tree RSS was 1,186,734,080 bytes. Sampled free GPU
memory never fell below 5,777 MiB. These samples do not measure an instantaneous
VRAM peak. Full diagnostic output occupied 4.24 GB; field exports omit raw media.

Both offline arms processed exactly the same 18,000 canonical frame identities,
with zero failures. Candidate replay took 2,987.6 seconds versus 1,011.5 seconds.
Track counts changed on 16,267 usable frames; detector counts differed on one.
These are regression observations, not annotated recall. Baseline NVRTC warnings
and different pipelines preclude attributing the cost difference to semantics alone.

Semantic presentation A/B used 3,000 updates per arm with zero differences in
physical stages. Six of sixty presentations became specific. Historical
60/canonical 188 event correspondence remains unresolved without shared causal
IDs. No optional semantic model was adopted. The 21 transformed rotation arms
processed 1,260 frames without failure: correction recovered track observations
in six of seven contexts, with a regression in the darkened context. Arbitrary
roll robustness and real walking direction remain partial.

Evidence: `alpha-full-realtime-01-report.json`,
`alpha-offline-18k-comparison-01.json`, `alpha-rotated-suite-01/suite.json`,
and the hashed evidence listed in the engine manifest, all under
`benchmark-results/v02/`.

## Executed verification

- Final repository verification: see `alpha-controlled-final.log` (closure result below).
- Android: `alpha-android-field-final.log`, assembleDebug, eight JVM tests and
  lintDebug passed. APK is in `%LOCALAPPDATA%\VISION\field-build\outputs\apk\debug`.
- Frozen engine through authenticated field HTTP: `alpha-field-smoke-final.json`
  passed. The supervised GPU process exited successfully in 12.953 seconds.
  Synthetic desktop inputs produced three checked fresh results aged 350.718,
  239.970 and 123.100 ms. Compact phone projection, expiry, recording/export and
  session close passed. Four recorded publications had P95 capture-to-publication
  249.510 ms. This tiny fixture is an integration check, not a performance study.
- Physical camera, phone TTS and Bluetooth have not been tested. No human review
  was created by these checks. Review judgments remain pending.

## Final adversarial audit

CRITICAL: no unresolved critical defect identified in the reviewed local scope.
This is not a claim of exhaustive proof or production safety.

HIGH resolved during this pass:

| Files                                                          | Problem and consequence                                                                                                 | Resolution / evidence                                                                                                                         |
| -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `field_state.py`, `field_gateway.py`, `alpha_field_worker.py`  | Capture-history eviction and reconnect races could associate work with a superseded session or discard active identity. | Pin active capture, scope commands/results to session, bound admission, reject stale/future results; session, burst and spawned-worker tests. |
| `field_protocol.py`                                            | Invalid JPEG dimensions/structure could reach native decoding.                                                          | Bounded structural preflight before decode, malformed-input tests and real JPEG fixture.                                                      |
| `field_gateway.py`, `field_export.py`                          | ZIP compression could hold the frame-admission lock.                                                                    | Snapshot/pin session then compress outside gateway lock; concurrent export test.                                                              |
| `apps/web/src/components/scene-panel.tsx`, `src/lib/replay.ts` | Numeric identity joins or fallback decisions could show another entity's explanation.                                   | Join session and serial through source track to world entity; no unrelated decision fallback, identity test.                                  |
| `FieldTransport.kt`, `FieldSpeech.kt`, `MainActivity.kt`       | Superseded sessions and expired callbacks could retain speech state.                                                    | Session-scoped transport, expiry/deduplication and lifecycle cleanup; eight JVM policy tests. Physical behavior remains unverified.           |
| `package.json`, `package-lock.json`, `tools/security.mjs`      | Vulnerable minimatch parser dependency and an obsolete advisory exception weakened the npm gate.                        | Scoped patched override; fail on all advisories or incomplete audit responses.                                                                |

The final browser pass also exposed an interrupted-video stream controller race
in `apps/web/src/lib/replay-store.ts` and `apps/web/src/app/api/replay/[kind]/route.ts`.
Removing a duplicate abort handler alone did not eliminate it. The final fix
replaces the Node stream bridge with bounded Web Stream file reads and one
idempotent file close; cancellation suppresses subsequent controller operations.
Two added tests cover exact range contents and cancellation during pending reads.
The final web check has 36 passing tests; see `alpha-web-stream-closure.log`.

MEDIUM remaining:

- `.github/workflows/`: Android has local build/test/lint evidence but no dedicated
  CI job. Java, Python and Android vulnerability scanning is not equivalent to
  the npm audit. Add those automated gates before broader distribution.
- `docs/releases/VISION_ALPHA_V1_LIMITATIONS.md` and qualification artifacts:
  one recording, synthetic orientation scenarios and no independent physical or
  human ground truth. Consequence: usefulness, generalization and safety remain
  unproven. Collect consented independent scenarios and actual phone measurements.
- `apps/web/src/components/human-review.tsx`: answers are held in page memory;
  reload loses unexported work. The UI instructs downloading before closing.
  Add explicit draft import/persistence if longer review sessions require it.
- Local release artifacts are ignored by Git. Back up the immutable archive,
  manifest, permitted source media and evidence together before moving machines.

LOW:

- Android SDK metadata XML version warning remains; build and lint passed.
  Align installed command-line tools during the next SDK maintenance update.
- README's stale statement that attention/audio are future work was corrected.
  Historical task reports remain historical evidence, not current release claims.

Architecture: Guardian retains mathematical/domain ownership; Python owns
perception scheduling and bounded field orchestration; the phone captures and
speaks authorized results; the website reads evidence and reviews it. The live
browser is outside the alert-delivery path. Optional enrichment is disabled.
No new runtime framework was needed. The system is adaptable within this local
scope; many-user service operation and on-device inference are separate work.

Security/privacy: loopback default, ephemeral bearer pairing, explicit TLS for
LAN, bounded requests, no trust-all certificates, no persistent phone token,
no raw field media in exports and no automatic human approval. npm audit does
not certify models, all ecosystems or deployment security. Docker is optional
and was not started or requalified in this non-Docker release pass.

## Remaining external evaluation

Use the [field guide](../../releases/VISION_ALPHA_V1_FIELD_GUIDE.md) to connect
a physical phone. Test camera timestamp support, reconnect/background behavior,
sensor orientation, local voice availability and actual audio routing. Measure
acoustic onset separately from app callbacks. Use the
[review guide](../../releases/VISION_ALPHA_V1_HUMAN_REVIEW_GUIDE.md) for real
participant judgments. These cannot be substituted with software tests.

## Verification closure

`npm.cmd run verify` exited zero: format, Java checks (195 Guardian tests and
3 API tests), Ruff, strict mypy (111 files), 1,342 pytest tests, ESLint, strict
TypeScript, 34 Vitest tests, production Next build, zero npm advisories and
API/web health/outage smoke checks passed. Log: `alpha-controlled-final.log`.
The later browser-audit wording and video cancellation changes are checked
separately in `alpha-web-closure.log` and `alpha-web-stream-closure.log`.

Browser inspection loaded the indexed full replay and actual video, stepped
between engine states, and advanced the review window while retaining
0 of 30 reviewed. It also revealed an advertisement at approximately 27 seconds.
The review heading now says recorded footage and explicitly warns about
non-walking segments. The immutable source/evidence was not silently curated or
re-scored. This is a substantive dataset suitability limitation for future field
claims, even though the same-source software regressions remain valid.

## Readiness matrix

| Gate                                  | Status                                                          |
| ------------------------------------- | --------------------------------------------------------------- |
| CORE_GUARDIAN_PERCEPTION_ARCHITECTURE | COMPLETE for local prototype                                    |
| SEMANTIC_ARCHITECTURE_CODE            | COMPLETE                                                        |
| FINAL_SEMANTIC_QUALIFICATION          | COMPLETE engineering pair; historical correspondence unresolved |
| ORIENTATION_HEADING_ROBUSTNESS        | PARTIAL                                                         |
| REALTIME_OFFLINE_QUALIFICATION        | COMPLETE for recorded source                                    |
| CONTROLLED_ALPHA_V1_ENGINE            | COMPLETE                                                        |
| HUMAN_TEST_EXPERIENCE_LAYER           | COMPLETE for local software; physical evaluation pending        |

Camera-to-text below means physical camera-to-text measurement, which has not
occurred. Recorded source-to-text P95 is 280.064 ms (172 text events); desktop
synthetic capture-to-publication is separately measured above. Neither is
physical phone-to-audio latency. Controlled readiness means supervised local
engineering evaluation only, not unassisted navigation.

| Required verdict                           | Result                                                      |
| ------------------------------------------ | ----------------------------------------------------------- |
| VISION_CONTROLLED_ALPHA_V1_ENGINE_COMPLETE | YES                                                         |
| VISION_CONTROLLED_ALPHA_V1_RELEASE_FROZEN  | YES — engine manifest above                                 |
| PRIMARY_REALTIME_PERCEPTION                | PicoDet-S FP32 CUDA + LK flow CPU + PIDNet-S CUDA; no depth |
| OPTIONAL_SEMANTIC_ENRICHER                 | NONE                                                        |
| OFFLINE_TEACHER                            | GroundingDINO, research only                                |
| UNKNOWN_OBJECTS_END_TO_END                 | YES                                                         |
| CLASS_SPECIFIC_RISK_DEPENDENCY_REMOVED     | YES in qualified engine                                     |
| FINAL_SEMANTIC_QUALIFICATION_COMPLETE      | YES, scoped engineering evidence above                      |
| SPECIFIC_PRESENTATIONS                     | 37 full replay; 13 first 600 seconds                        |
| GROUP_PRESENTATIONS                        | 2 full replay; 2 first 600 seconds                          |
| GENERIC_PRESENTATIONS                      | 133 full replay; 58 first 600 seconds                       |
| ARBITRARY_ROLL_ROBUST                      | PARTIAL                                                     |
| CAMERA_FORWARD_ASSUMPTION_REMOVED          | YES; unavailable heading stays unknown                      |
| USER_HEADING_CORRIDOR_INTEGRATED           | YES in software; physical heading unvalidated               |
| CAMERA_VIEW_HEALTH_ACTIVE                  | YES                                                         |
| OPTIONAL_PROVIDER_HANG_CONTAINED           | NOT_APPLICABLE to release; optional provider disabled       |
| OFFLINE_REGRESSION_COMPLETE                | YES                                                         |
| REALTIME_REGRESSION_COMPLETE               | YES                                                         |
| REALTIME_RATE_HZ                           | 12.368 full recording; 10.50 first 600 source seconds       |
| PUBLICATION_P95_MS                         | 241.947 full recording; 257.657 first 600 seconds           |
| ANDROID_FIELD_HARNESS_READY                | YES, software build/test/lint                               |
| REAL_PHONE_CAMERA_TESTED                   | NO                                                          |
| BLUETOOTH_TTS_TESTED                       | NO                                                          |
| CAMERA_TO_TEXT_MEASURED                    | NO for physical camera                                      |
| CAMERA_TO_TTS_START_MEASURED               | NO                                                          |
| HUMAN_USEFULNESS_VALIDATED                 | NO                                                          |
| PHYSICAL_ACCURACY_VALIDATED                | NO                                                          |
| PRODUCTION_SAFETY_VALIDATED                | NO                                                          |
| UNSUPERVISED_PUBLIC_DEPLOYMENT_READY       | NO                                                          |

No Android device was attached when `adb devices` was executed on November 6.
Do not close that blocker by marking software-generated records human reviewed.

| Final experience verdict     | Result                                          |
| ---------------------------- | ----------------------------------------------- |
| INTERACTIVE_WEBSITE_READY    | YES                                             |
| HUMAN_REVIEW_UI_READY        | YES                                             |
| HUMAN_TEST_TECHNICALLY_READY | YES for supervised local prototype evaluation   |
| CONTROLLED_ALPHA_READY       | YES for supervised local engineering scope only |

Final production HTTP verification (`alpha-web-stream-http-final.json`) passed:
seven page routes returned 200, the manifest exposed 18,541 measured updates,
the review packet contained 30 windows, invalid timestamps/ranges and cross-site
requests were rejected, and 30 interrupted video streams completed without
server errors. The final server log is `alpha-web-stream-final-server.log`.
The health page correctly shows the API unavailable when it is stopped. Initial
launch without the required API origin failed; the demo/field guides now include
the environment setting explicitly.

Desktop browser inspection confirmed video, overlays, next-state navigation,
review navigation and pending judgments. A requested narrow viewport override
did not change the browser's actual 1280-pixel width; narrow-screen visual QA is
unverified. CSS breakpoints were statically inspected, not claimed device-tested.

Software readiness does not close the physical-device, human-usefulness,
dataset-suitability or production-safety gates. No Task019 work was started.
