# Evidence fusion policy

IMPLEMENTED deterministic policy; no Bayesian probability or confidence averaging.

| Input                       | Updates                                           | Constraints                                                                                                   |
| --------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| DetectionBatch              | Detector source status/provenance                 | Explicit session envelope; success-empty distinct from no run/failure; no identity creation without tracks    |
| TrackSet                    | Entity map, category, box, lifecycle/history      | Session/source/clock validated; current observed versus predicted preserved; duplicate IDs rejected           |
| TrackDepthObservation       | Selected depth summary and candidate camera point | Exact observed track FrameIdentity; no nearest join; relative depth never becomes meters                      |
| SuppliedDepthPose           | Camera pose, optional world-point derivation      | Explicit session, exact depth identity, valid device frame, finite unit rotation; no latest-pose substitution |
| CameraMotionEstimate        | Camera pair/quality/scale                         | No translation integration or physical velocity inference                                                     |
| TrackImageMotionObservation | Pixel displacement/rate/residual                  | Exact observed track endpoint, explicit flow/ego provenance; never meters/second                              |
| SemanticFrame               | Class summary and optional center consistency     | Source time retained; UNVERIFIED; never changes track category                                                |
| SurfaceEvidenceFrame        | Compact surface regions/counts                    | No dense history; UNVERIFIED and age retained                                                                 |
| Failure                     | Subsystem FAILED/reason                           | Existing entities remain; retained payload time is unchanged                                                  |

DepthFrame is consumed by existing Task008 exact region sampling, then world receives TrackDepthObservation; dense maps are not stored. Camera-point and world-point geometry delegates to Task008/Guardian. Model metric depth remains MODEL_ESTIMATED_METRIC_DEPTH with METRIC_DEPTH_UNVALIDATED provenance. World coordinates require fresh exact depth plus matching non-unreliable supplied pose and extrinsics. Unknown calibration yields no metric point. Relative evidence remains useful without a point.

Conflict diagnostics include track category changes, semantic-center disagreement, mismatched object-depth/motion frame, pose/depth mismatch, lateness, duplicate/older events, capacity and source failure. Diagnostic deque is bounded (default 32). No unbounded graph, averaging of depth providers, track merging or extra temporal filtering.

Raw observations are not rewritten. Original acquisition/recording owns diagnostics recovery; world retains compact references/provenance, not an unlimited observation archive. Recording is opt-in.
