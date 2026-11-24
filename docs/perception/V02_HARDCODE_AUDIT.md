# V0.2 pre-change hard-code audit

2026-10-27. Read-only inspection preceded V0.2 implementation. Frozen V0 remains
the comparison baseline. No fixture is deleted for containing a category name.

## Scope and evidence

The initial scan read 609 repository text files and found 9347 matching lines.
This includes configuration/evaluation JSON, not 9347 source defects. The
reproducible `tools/v02_audit.py` classifies every matching line and writes its
path, line, matched terms and rationale to the named baseline's
`occurrences.jsonl`. Build outputs, dependency trees, virtual environments,
binaries and ignored private data are excluded. Broad keyword classification is
triage; the runtime findings below were inspected directly.

Four categories are used: LEGITIMATE TEST FIXTURE, CONFIGURATION, DISPLAY COPY,
ARCHITECTURAL HARD-CODING. Model adapter label tables are legitimate provider
metadata only when they stay at that boundary; current P0 filtering does not.

## Confirmed runtime findings

| Severity | File                                                        | Finding and consequence                                                                                             | Required V0.2 change                                                                                                            |
| -------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Critical | `apps/perception-lab/src/perception_lab/tracking.py:175`    | Explicit UNKNOWN filter discards valid unknown detections before tracking. Geometry-first risk never receives them. | Opt-in V0.2 objectness admission; geometric identity independent of semantic label. Preserve frozen V0 behavior for regression. |
| High     | `apps/perception-lab/src/perception_lab/detection.py:12`    | Eight-class enum, taxonomy lock, provider class ID/name in shared Detection.                                        | Immutable generic entity observation, optional semantic concept/group, provider IDs confined to adapter.                        |
| High     | `apps/perception-lab/src/perception_lab/edge_runtime.py:26` | Non-P0 COCO classes lose meaningful names.                                                                          | Versioned complete provider vocabulary data; retain unknown physical entities.                                                  |
| High     | `apps/perception-lab/src/perception_lab/tracking.py:110`    | Class disagreement adds association cost; duplicate suppression also depends on class.                              | Measure geometry-only association and semantic-independent duplicate policy in V0.2.                                            |
| High     | `apps/perception-lab/src/perception_lab/corridor.py:304`    | Metric relation branch requires selected known classes.                                                             | Replace class-derived grounding with explicit geometric/evidence validity. Do not simply assert every object is grounded.       |
| High     | `apps/perception-lab/src/perception_lab/world_types.py:70`  | World entities carry detector taxonomy enum.                                                                        | Optional model-independent concept and domain group.                                                                            |
| Medium   | `apps/perception-lab/src/perception_lab/world_model.py:517` | Class-to-segmentation expectations are source mappings. Currently diagnostic only.                                  | Move mapping to versioned ontology; preserve disagreement rather than overwrite identity.                                       |
| High     | `apps/perception-lab/src/perception_lab/alerts.py:26`       | Narrow category aliases and renderer vocabulary limit semantic specificity.                                         | Reliability/stability-gated concept → group → generic label, preserving existing expiry and direction evidence.                 |
| High     | `apps/perception-lab/src/perception_lab/preprocessing.py`   | Live cardinal rotation is not connected to the preprocessing path.                                                  | Explicit canonicalization with transform provenance and intrinsics/basis handling.                                              |

## Existing behavior that should be retained

- `risk.py` assesses each supplied world entity; no raw car/dog/etc. risk switch
  was found. The major semantic exclusion is upstream, not a need to rewrite risk.
- `corridor.py` already reports `CAMERA_FORWARD_NOT_BODY_HEADING` in image mode.
  The fallback is partly explicit; dynamic user-motion heading is still missing.
- Guardian `ImageTransform` supports cardinal buffer mappings;
  `RotatedIntrinsics` explicitly changes optical-axis basis. Reuse these instead
  of maintaining a contradictory geometry implementation.
- Task004/009 timestamp alignment and unavailable-motion states should remain.
  A 2D roll correction cannot remove pitch/yaw or recover an occluded field of view.
- COCO-specific evaluation metrics, class fixtures and parity checks are valid
  for their declared populations. They are not a universal object taxonomy.
- Android harness metadata carries rotation but has no gravity/orientation
  quality contract yet. It is an unfinished engineering client, not Task019.

## Baseline and adoption policy

`VISION_V0_RESCUED_BASELINE` snapshots current working source (including uncommitted
rescue work), records source hashes, and references the 96 previously frozen
source/evidence hashes. It refuses an existing output directory or changed rescue
hash. Original models, recordings and benchmark outputs are not overwritten.

No candidate is selected or integrated into the realtime path by this audit.
The 60-alert and 188-event comparisons, full-video run, orientation experiments,
license assessment and complete verification remain mandatory.
