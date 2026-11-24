# Human-test-ready semantic dependency audit — 2026-10-28

The first pass was read-only. It searched production Python, Java, Kotlin and
TypeScript under applications and Guardian core for ObjectClass, provider class
IDs/names, COCO and the requested object names. Follow-up inspection traced
category-dependent admission, association, masks, grounding and presentation.
This is an engineering audit, not human usefulness or safety validation.

## Findings and disposition

| Classification           | Files / boundary                                                                                                                                                      | Finding and action                                                                                                                                                                                                                    |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ARCHITECTURAL_DEPENDENCY | `motion_masking.py`                                                                                                                                                   | HIGH: UNKNOWN regions were excluded from motion masks, allowing their features to enter static-background estimation. Fixed generic observations in both detection and observed-track paths; four combined motion/surface tests pass. |
| ARCHITECTURAL_DEPENDENCY | `surfaces.py`                                                                                                                                                         | HIGH: UNKNOWN generic regions were omitted from occupancy overlays. Fixed both observation paths without relabeling segmentation or changing freshness/area limits.                                                                   |
| COMPATIBILITY            | `detection.py`, `entity_compatibility.py`, `tracking_types.py`, `world_types.py`                                                                                      | Legacy enum/index fields remain carriers. Generic observations retain source identity, box, concept, transform and provenance; missing concepts are not discarded. Full removal of the carrier is not claimed.                        |
| COMPATIBILITY            | `tracking.py`                                                                                                                                                         | Default legacy mode retains category admission, match penalty and duplicate rules. Opt-in geometry-first mode bypasses these dependencies. Runtime selection must explicitly enable that mode.                                        |
| COMPATIBILITY            | `corridor.py`                                                                                                                                                         | Legacy metric path retains its class whitelist. Generic path instead requires supported metric evidence and plane proximity, with image evidence fallback. No generic class whitelist.                                                |
| COMPATIBILITY            | `world_model.py`                                                                                                                                                      | Legacy segmentation-center category comparison emits an unverified disagreement diagnostic; it does not reject or rename a generic entity.                                                                                            |
| COMPATIBILITY            | `detector_runtime.py`, `edge_runtime.py`, `rtdetr_runtime.py`                                                                                                         | Vendor vocabulary validation/mapping is provider-specific. Generic adapters must stop provider indices at the perception boundary. Existing V0 provider taxonomy is preserved for reproduction.                                       |
| CONFIGURATION            | `semantics.py`, `semantic_runtime.py`, `surfaces.py`                                                                                                                  | Segmentation taxonomy defines ground/obstacle evidence, not exact-object risk bonuses. Replacing this taxonomy requires a compatible surface adapter; it is not an arbitrary-concept detector.                                        |
| DISPLAY_ONLY             | `alert_renderer.py`, `alert_types.py`, `alerts.py`                                                                                                                    | Legacy phrase aliases remain; stable arbitrary concepts use bounded authorized text. Bare names and low-quality/stale evidence cannot authorize specificity. Broad-group fallback remains to be completed.                            |
| CONFIGURATION            | `perceived_entity.py`, `configs/perception/ontology/vision-domain-v1.json`                                                                                            | Eleven broad semantic groups, including UNKNOWN, are contextual metadata. The hierarchy is currently empty; embedding/group coverage is not yet measured.                                                                             |
| CONFIGURATION            | `detection_metrics.py`, `detection_parity.py`, `detector_benchmark.py`, `tracking_evaluation.py`, `evaluation_dataset.py`, `semantic_evaluation.py`, evaluation tools | Closed-taxonomy historical metrics remain intentional. They must not be presented as generic V0.2 entity coverage. Exact 60/188 populations are separately frozen.                                                                    |
| TEST_FIXTURE             | `apps/perception-lab/tests`, Guardian/API/web tests                                                                                                                   | Named concepts are test inputs or expected presentation, not product risk policy. Preserve historical fixtures and test unknown/arbitrary concepts separately.                                                                        |
| DISPLAY_ONLY             | Documentation, web labels and overlays                                                                                                                                | Human-readable descriptions are not evidence of a semantic admission rule.                                                                                                                                                            |

No exact-object-label branch was found in trajectory, interaction, risk or
attention policy. The statement is scoped to inspected production modules; it
does not mean the whole runtime is generic by default. The archived V0 path
intentionally remains reproducible and separate from an eventual selected V0.2
profile.

## Remaining acceptance blockers

- Real provider integration and measured quality policy: current adapters report
  UNKNOWN quality, while semantic stability tests use explicit synthetic GOOD
  evidence. Do not silently promote model scores to validated quality.
- Class-independent candidate benchmarks, teacher comparison and GPU qualification.
- Explicit user-heading evidence and active camera-health capability propagation.
- Rotation/full-video/offline/realtime qualification and final release freeze.

No custom training, large image-dataset download, model adoption or Task019 work
was performed as part of this audit. Teacher asset acquisition is a separate
research setup step; teacher output remains MODEL_PSEUDO_LABEL.
