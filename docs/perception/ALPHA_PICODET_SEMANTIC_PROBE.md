# Real PicoDet semantic probe — October 29

Status: first real offline semantic-path measurement completed. Alpha qualification
and exact-cohort before/after alert recovery remain incomplete. Task019 not started.

## A. PicoDet generic semantic adapter

The opt-in `entity_semantics_ontology` profile enables a pinned PicoDet boundary in
both the CLI and replay runner. It retains frame, timestamp, original-coordinate
box, raw concept, joint score, transform hash, model hash and provider configuration
hash. The compatibility carrier uses UNKNOWN; its semantic concept never becomes
an authoritative legacy risk class. Tracking uses its existing objectness-first
mode for this profile. Missing vocabulary entries retain their physical regions.
The existing deployed/default profile is not switched automatically.

## B. Quality and confidence model

The legacy `quality` field alone conflated observation usability with semantic
trust. The new source-validity field records validated, pinned, finite runtime
output and inverse mapping, while `quality` remains UNKNOWN and score calibration
remains UNCALIBRATED. The confidence basis is DETECTOR_JOINT_SCORE; independent
objectness remains null. Track/world identity, source, timestamp and box checks
still establish association before semantic fusion.

Fusion keeps three supporting source frames, minimum score 0.5, agreement 0.7,
two-second expiry, bounded history and provider limits. Explicit source validity
can establish usable evidence without claiming calibrated confidence. Unreliable
or degraded quality cannot use this route. Different provider/model/score streams
cannot jointly authorize a stable label or group. Raw uncalibrated scores are not
claimed to be directly comparable across providers. The legacy function named
`probability` only validates the unit interval; its name does not establish calibration.

## C–E. Frozen 60 targets, semantic funnel and loss

Every exact frozen target timestamp was decoded, without frame substitution.
At the 60 alert target frames, cross-run IoU association gives:

| State                                       | Count /60 |
| ------------------------------------------- | --------: |
| Stable specific, authorized at attention    |        18 |
| Stable broad group, authorized at attention |         3 |
| Unstable semantic evidence                  |        34 |
| No matched entity                           |         5 |

All 34 unstable cases had fewer than three qualifying observations of the same
specific concept in the recorded bounded evidence. No threshold was reduced.
The 21 authorized states did not produce a presentation at their exact target
frame. This is not evidence of semantic loss: attention can legitimately remain
silent. The scorer retains attention actions and reason codes separately.

Across the entire probe, 60 actual text-sink outputs were accepted: 3 SPECIFIC
(Car, Person, Truck) and 57 GENERIC. These came from the new context schedule,
not a proven one-to-one mapping to the frozen 60 original alert events. Therefore
**do not report this as a qualified reduction from 60 generic alerts to 57**.
At the exact target frames, the matched presentation count is NOT_PRESENTED=60.
No audible delivery or semantic accuracy is established.

## F. Independent broad-group recovery

Version 2 domain ontology supplies seven explicit hierarchy relationships for
the existing P0 vocabulary. The domain grouping is curated configuration, not an
external taxonomy or measured classifier. Specific and group support are computed
separately. Tests show car/truck/bus disagreement authorizes Vehicle after three
qualifying frames while the specific concept remains unstable. Rendering retains
the group level and uses specific > group > generic without inventing direction.

## G. Canonical 188 events

All 5,313 reference observations and all 188 events remain in scoring. The reference
is prototype data, not independent truth. Coverage means at least one associated
record, not correct inference or continuous tracking.

| Stage                                              | Covered events /188 |
| -------------------------------------------------- | ------------------: |
| Entity, track, world                               |            187 each |
| Corridor, trajectory, interaction, risk, attention |            187 each |
| Accepted alert at a reference frame                |                   6 |
| At least one specific-stable observation           |                 133 |
| At least one group-stable observation              |                  64 |

Group/specific event counts overlap across observations. They must not be summed.

## H–K. Remaining causes and architecture decision

Remaining issues are inadequate temporal support under this bounded context
schedule, five unmatched targets and changed alert timing/selection. Historical
unknown associations remain unknown; this probe does not reconstruct them.

Open-vocabulary marginal value is NOT MEASURED. Additional vocabulary does not
by itself fix insufficient temporal support or attention silence. No new GPU
benchmark or teacher inference ran. The 2 GiB RAM reserve remains enforced.
PicoDet with corrected semantics is a viable architecture candidate, not a selected
or frozen Alpha release. Optional enrichment remains unadopted.

## Execution and limitations

October 29 verification: `npm run verify` exited 0. Guardian: 193 tests;
perception lab: 1,225; web: 31; API: 3. Configured formatting/lint, strict type
analysis, web/API builds and security smoke checks passed. Log:
`benchmark-results/v02/alpha-picodet-verify-01.log`. This establishes repository
checks, not perceptual accuracy or release qualification.

`benchmark-results/v02/alpha-semantic-probe-02/` contains configuration, schema-2
trace, summary and scoring. `semantic-score-v2.json` distinguishes actual outputs
from authorized states; the earlier score's ATTENTION_SELECTION label was not a
demonstrated semantic loss and is superseded by the explicit no-presentation label.

The CPU run used ONNX Runtime 1.24.4, FP32, two threads, all 354 exact source frames
and 220 context frames. Context extends 0.8 seconds before a target, sampled at
200 ms; exact targets are always forced. This differs from rescued realtime cadence.
Motion and segmentation inputs were disabled; their unavailable evidence remains
explicit in downstream reasoning. No final runtime speed comparison is claimed.

The first attempt failed on a generic-carrier invariant. The correction moves
semantics out of the legacy enum, and tests now use real P0 legacy labels rather
than already-UNKNOWN fixtures. The successful run did not weaken this invariant.

The probe exposed excessive repeated diagnostic history (477 MB for 574 trace
rows). New traces retain the complete current fusion summary and evidence count,
but omit repeated raw evidence history from each frame. Current detector/track
observations still carry source validity, score basis and provenance. The existing
bounded asynchronous writer remains in use for rescued realtime instrumentation;
its instrumentation cost must be measured in final realtime qualification.

Next: preserve continuous original admission cadence and establish explicit
one-to-one event/output association before claiming the exact 60 before/after.
Then evaluate marginal enrichment, select architecture and finish roll, heading,
view health and full offline/realtime qualification. No Alpha freeze yet.
