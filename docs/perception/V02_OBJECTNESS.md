# Objectness-first research boundary

`PerceivedEntityObservation` is immutable and contains source frame identity,
region geometry, confidence basis, optional concept/group, transform provenance,
quality and model identity. Provider class indices are absent.

Unknown physical candidates do not require a known category. An optional mask is
a bounded reference, not an arbitrary buffer embedded in each observation.
Source timestamps are retained. This does not establish physical accuracy.

The current detector's joint class/detection score must not be mislabeled as an
independently measured objectness probability. `region_confidence` retains it;
`objectness_confidence` remains unavailable unless the provider actually supplies
that quantity. Probability calibration is not claimed for either score.

`AssociationTracker(..., objectness_first=True)` is an opt-in V0.2 experiment. It
admits UNKNOWN detections, removes semantic association cost, and deduplicates
overlapping observations without class equality. Temporal/geometric bounds and
single-writer ownership stay unchanged. The default false branch preserves V0's
policy and configuration hash. V0 source is archived in the named baseline;
the working tracker source now differs intentionally.

`JointScoreEntityAdapter` now converts provider regions and a supplied vocabulary
into generic observations. Missing vocabulary entries retain the physical region
with unavailable semantics. Eleven adapter tests cover arbitrary concepts, missing
labels, immutable vocabulary ownership, source/provider ID separation and invalid inputs. Provider indices stop
at this boundary; joint scores are not fabricated into objectness probabilities.

The opt-in generic path now carries the original immutable observation through
tracking and world state. Synthetic integration tests exercise bollard, unnamed
objects and electric scooter through corridor, trajectory, interaction, risk,
attention and alert processing. Generic metric grounding requires proximity to
the supplied ground plane; it does not claim physical ground contact. Otherwise,
available image-space evidence remains usable under existing quality gates.

Track semantic fusion retains bounded provider evidence, disagreement and expiry.
The asynchronous semantic worker has one active job, one replaceable pending job
and one replaceable result. The world model checks original frame history and
entity/track generation before admitting a result. Stable fresh semantics may
authorize bounded alert wording; they cannot change interruption admission or
extend source/delivery deadlines. These are software-policy tests, not semantic
accuracy or human language validation.

Remaining compatibility dependencies:

| Boundary                                                            | Remaining legacy use                                               | V0.2 behavior                                                                                                   |
| ------------------------------------------------------------------- | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| detection.py / entity_compatibility.py                              | Detection carries ObjectClass and class index                      | Generic carrier is UNKNOWN with the complete observation attached; vocabulary indices never define survival.    |
| tracking.py / tracking_types.py                                     | Category votes and serialized category                             | Geometry-first opt-in ignores category for admission, matching and duplicate suppression.                       |
| world_types.py / world_model.py                                     | Legacy category/history and segmentation compatibility diagnostics | Generic observations and independent track semantics are retained; semantic names do not define identity.       |
| corridor.py                                                         | Legacy metric class whitelist                                      | Only the legacy branch uses it; generic entities use measured plane proximity and existing geometry gates.      |
| attention_types.py / alert_types.py / alerts.py / alert_renderer.py | Legacy category aliases/templates                                  | Fresh stable arbitrary concepts use a bounded text field; invalid/unavailable semantics retain generic wording. |
| tracking_evaluation.py and existing V0 evaluation tools             | Class-matched reference metrics                                    | Preserve historical comparability; not sufficient for V0.2 class-independent coverage measurements.             |

Trajectory, interaction and risk do not introduce a generic-concept whitelist.
The runtime candidate profile and real model enrichment adapters still need
qualification. Working schemas gained optional fields and corridor configuration
gained a ground-plane tolerance, so working serialized outputs/configuration hashes
are not claimed identical to archived V0. The immutable source archive remains
the reproduction reference. The 60-alert/188-event comparisons remain pending.
