# Controlled Alpha closure checkpoint — October 29

Status: INCOMPLETE. No `VISION_CONTROLLED_ALPHA_V1` release is frozen. Task019
has not started. This report distinguishes measured revisions from current code.

## A–C. Historical evidence and continuous A/B

Historical rescued V0 remains unchanged. Its compact telemetry did not retain
semantic fusion evidence; exact detector/track correspondence is established for
38/60 references, not all 60. Missing historical lineage is not reconstructed.
See [the forensic ledger](ALPHA_SEMANTIC_LOSS_FUNNEL.md).

The new continuous CPU runner admits the first authoritative source frame at or
after each fixed 200 ms deadline over [0, 600 seconds). It decodes monotonically,
preserves source sequence/PTS, keeps all tracking/semantic/attention state, and
does not read evaluation markers. Detector cadence remains 200 ms. It performs
no target-specific invocations or successful-frame selection. This is offline
admission, not the historical latest-frame realtime schedule.

Both arms retain the generic adapter and fusion. A disables only semantic
presentation attachment; B enables it. Motion, segmentation and depth are absent
in both. No fusion, risk, cooldown, expiry or novelty thresholds differ.

| Result                     |     A |     B |
| -------------------------- | ----: | ----: |
| Admitted/processed updates | 3,000 | 3,000 |
| Dropped/failed frames      | 0 / 0 | 0 / 0 |
| Specific presentations     |     0 |     6 |
| Group presentations        |     0 |     0 |
| Generic presentations      |    60 |    54 |

The pair checker verified identical admission identities, detector outputs,
tracking, world state, corridor, trajectory, interaction, risk and attention
decisions on every update. Only session UUIDs, detector timing fields and the
declared semantic attachment fields are excluded from equivalence comparison.
Configuration differences are restricted to presentation enablement and output
directory; runtime source manifests match. Thus the measured presentation-only
ablation reduces generic outputs by 10%. This does not establish naming accuracy.

Artifacts under `benchmark-results/v02/`:

- `alpha-continuous-a-01/`, `alpha-continuous-b-04/`
- `alpha-continuous-pair-01.json`
- `alpha-continuous-runtime-01.zip`: 109 source files verified against run A's
  manifest before archival.

**Revision boundary:** this pair predates first-class lineage and semantic
fusion policy v2. Its metrics must not be assigned to the current revision.

## D. Event/alert lineage

Current code adds immutable `EventLineage` to attention decisions, alert intents
and presentations. Links identify the actual observation, source identity,
world entity, track generation, world record, interaction record, risk record,
attention event and episode. Presentation and intent retain the same lineage
and alert ID. Track generation uses the existing monotonic track serial within
its session; it is not a frame number.

Record keys refer to records consumed in the same Guardian update. An interaction
record key is not a claim of physical event identity across time or runs.
Unavailable upstream links are explicitly listed. Duplicate records, mismatched
sessions, future records, observation mismatches and mismatched alert lineage
are rejected. No matching uses box proximity or timestamp coincidence.

Five dedicated tests pass. `alpha-lineage-smoke-01/` ran 100 real updates over
20 source seconds: all six delivered outputs (3 specific, 3 generic) had matching
intent/presentation lineage and no missing links. This is bounded software
verification, not full-population lineage qualification.

## E–G. Frozen populations

| Population               | Established continuous-run correspondence | Unresolved |
| ------------------------ | ----------------------------------------: | ---------: |
| Historical 60 references |                                         0 |         60 |
| Canonical 188 events     |                                         0 |        188 |

No heuristic cross-run substitution is used. Therefore historical-event
semantic recovery, lineage-linked presentation counts and canonical-event stage
coverage are not yet qualified. Do not transfer the prior context probe's
187/188 coverage into this continuous experiment.

Continuous B has 126,740 **world-entity observations**, including 12,782
specific-stable and 15,296 group-stable observations. These overlap and are not
counts of unique objects, canonical events, correct labels or useful alerts.

## H–I. Instability and independent groups

The original 34 unstable markers remain unclassified against continuous-run
entities until correspondence exists. They are not relabeled as recovered by
nearby stable tracks.

The audit found a genuine source-stream split: nameless PicoDet observations
used `JOINT_DETECTION_SCORE`, while named concepts used `DETECTOR_JOINT_SCORE`.
These describe the same runtime joint-score stream. Policy v2 canonicalizes
that alias, isolates provider configuration changes, and includes the policy
version in the configuration hash. Tests prove that a nameless observation
does not invent support or refresh expiry, and that configuration changes
cannot pool support. Minimum score 0.5, agreement 0.7, three source frames and
two-second expiry remain unchanged. Full continuous results for v2 are pending.

Prediction-only ticks preserve fresh specific/group state in both fusion and
world-model tests; replacement tracks inherit none. Independent broad-group
fusion remains active. The measured pair had group-stable states but no group
presentations; silence is not scored as incorrect without independent review.

## J–N. Residuals, enrichment and architecture

`alpha-residual-semantic-targets-01.json` retains all 54 generic delivered outputs
from archived B-04. All 54 join to exact attention-event and entity IDs in that
run, with source observation and semantic state retained. This is a screening
population from the measured revision, not final-v2 residual qualification.

Marginal YOLOE-11s/YOLO-World/teacher comparison on qualified final residuals
remains pending. No GPU was used in this checkpoint. No candidate was adopted,
no model was downloaded, and no training began. Primary candidate remains
PicoDet; optional semantic enricher remains NONE. Grounding DINO remains an
offline teacher, not truth. Final runtime architecture selection is not claimed.
With no optional neural provider selected, its native-hang path is excluded;
enabling one later would require hard isolation and bounded qualification.

## O–T. Remaining qualification

Arbitrary-roll measurement, authoritative orientation integration, user-heading
integration into the corridor, full view-health qualification, complete-source
run, rotated clips, 18,000-frame regression and ten-minute realtime regression
remain open. Current footage supplies no authorized gravity/mount evidence.
No camera-forward assumption may be silently promoted to user heading.
Auto-mount remains research. These gates are not satisfied by the CPU A/B run.

## U. Instrumentation and resources

| Diagnostic measurement            |             A |             B |
| --------------------------------- | ------------: | ------------: |
| Trace bytes                       | 1,768,581,689 | 1,779,592,028 |
| Bytes per update                  |       589,527 |       593,197 |
| Sampled process RSS peak, bytes   |   218,202,112 |   213,409,792 |
| Writer queue peak / drops         |         0 / 0 |         0 / 0 |
| Instrumentation mean wall time    |      19.54 ms |      18.60 ms |
| Instrumentation recent-window P95 |      82.13 ms |      34.66 ms |

The writer was synchronous. Quantiles cover the final 2,048 updates; means cover
all 3,000. Instrumentation CPU time was not measured. Machine load/headroom
differed, so these are not controlled performance comparisons. Diagnostic volume
remains too large to assume negligible realtime impact; compact diagnostics and
final realtime overhead qualification remain mandatory.

B-01 and B-02 stopped with sanitized `SOURCE_FAILED`; the original artifacts do
not retain the underlying cause. System RAM was subsequently measured at
1.83 GiB, below the unchanged reserve. They remain incomplete. After the user
freed RAM, 5.14 GiB was available. A superseded B-03 setup attempt was explicitly
terminated; only its own process was stopped. B-04 completed using A's archived
harness. No unrelated user process was terminated and no guard was lowered.
The current runner now persists bounded machine-readable failure reasons and
RAM at guard stops. Dedicated tests cover RAM and wall-budget rejection before
pixel conversion. Its deadline is checked between calls, not a native-call
preemptive timeout.

## V–W. Audit and verification

Fixed: semantic score-basis alias split; missing provider-configuration stream
isolation; missing immutable alert lineage; missing machine reason on aborted
continuous runs. No historical association or calibration claim was invented.

`npm.cmd run verify` passed after these changes, with 1,241 perception tests,
193 Guardian tests, 31 web tests and 3 API tests: 1,468 total across those
subsystems. Ruff, strict mypy (108 source files), ESLint, TypeScript, Spotless,
SpotBugs, production builds, dependency security and runtime smoke checks passed.
Log: `benchmark-results/v02/alpha-closure-verify-02.log`.

## X–Z. Freeze and verdict

No Alpha release profile exists yet. The archived paired experiment is evidence,
not a release freeze. Current code still needs its final continuous measurement,
population correspondence/result tables, residual assessment, architecture
selection and the orientation/full-video/realtime gates above.

- VISION_CONTROLLED_ALPHA_V1_ENGINE_COMPLETE: NO
- PRIMARY_REALTIME_PERCEPTION: PicoDet candidate; final profile not frozen
- OPTIONAL_SEMANTIC_ENRICHER: NONE
- OFFLINE_TEACHER: Grounding DINO Base
- CONTINUOUS_SEMANTIC_RECOVERY_MEASURED: YES for archived presentation ablation;
  NO for final-v2 and historical populations
- PAIRED_SEMANTIC_AB_COMPLETE: YES for archived presentation ablation;
  NO for final revision qualification
- EVENT_ALERT_LINEAGE_COMPLETE: implemented and bounded-smoke verified;
  full-population qualification pending
- SPECIFIC / GROUP / GENERIC PRESENTATIONS: 6 / 0 / 54 in archived B-04
- UNKNOWN_OBJECTS_END_TO_END: supported; final qualification pending
- CLASS_SPECIFIC_RISK_DEPENDENCY_REMOVED: not newly qualified here
- ARBITRARY_ROLL_ROBUST: PARTIAL
- CAMERA_FORWARD_ASSUMPTION_REMOVED: NO, integration incomplete
- USER_HEADING_CORRIDOR_INTEGRATED: NO
- CAMERA_VIEW_HEALTH_ACTIVE: opt-in, final profile not selected
- OPTIONAL_PROVIDER_HANG_CONTAINED: NOT_APPLICABLE while provider is NONE
- REALTIME_REGRESSION / OFFLINE_REGRESSION: NO for final Alpha
- CUSTOM_TRAINING_REQUIRED: NO; no closure evidence establishes a need
- HUMAN_TEST_TECHNICALLY_READY / CONTROLLED_ALPHA_ENGINE_READY: NO
- HUMAN_USEFULNESS_VALIDATED / PHYSICAL_ACCURACY_VALIDATED: NO
- PRODUCTION_SAFETY_VALIDATED / UNSUPERVISED_PUBLIC_DEPLOYMENT_READY: NO

Next phase after mandatory gates pass: ALPHA_V1_FIELD_EXPERIENCE. Not Task019.
