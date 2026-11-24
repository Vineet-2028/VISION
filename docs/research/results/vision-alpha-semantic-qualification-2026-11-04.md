# Controlled Alpha semantic measurement — November 4, 2026

Status: paired semantic presentation ablation verified. This is not the final
Alpha release qualification, a realtime result, or a human accuracy evaluation.

## Executed continuous pair

Evidence directory: `benchmark-results/v02/alpha-compute-batch-02`.
Both runs processed 3,000 updates with zero failed/dropped frames over the same
600-second source interval at fixed 200 ms source-time admission. Original PTS
and continuous tracking/fusion/attention state were retained. Evaluation markers
did not influence admission. The source, ontology, configuration except presentation
enablement, runtime metadata and production-source manifests matched.

`paired-result.json` reports no differences in detector, tracks, world, corridor,
trajectory, interaction, risk or attention after the declared session-ID and
presentation-evidence normalization. The 115 runtime files, including the Guardian
JAR, are preserved in `runtime-source.zip`; all archived bytes were checked against
both manifests. Later field-session fixes are outside this measured revision and
were checked separately; do not describe the archive as the final release freeze.

| Delivered wording | A: semantics disabled for presentation | B: semantics enabled |
| ----------------- | -------------------------------------: | -------------------: |
| Specific          |                                      0 |                    6 |
| Broad group       |                                      0 |                    0 |
| Generic           |                                     60 |                   54 |

Six of 60 deliveries (10%) used specific wording in B. This measures presentation
selection, not name correctness, recall, usefulness or physical safety. The six
specific outputs do not establish correspondence to six historical rescued alerts.

All 60 delivered B outputs passed the exact selected-event/world-observation/
intent/presentation lineage checks. The historical 60 alert markers and canonical
188 event markers remain individually `UNRESOLVED`: their frozen records do not
provide shared immutable causal identities for this run. No nearest-time/box/IoU
substitution was used and missing correspondence was not counted as recovery.

B contains 126,740 world-entity observations, including 14,020 specific-stable
observations and 16,736 group-stable observations. These are repeated observations,
not distinct objects or events, and the two stability counts are not disjoint.

## Residual diagnosis

`FINAL_RESIDUAL_SEMANTIC_TARGETS.json` contains all 54 generic delivered outputs,
each tied to its actual original observation. For 26, the same entity later attained
fresh stable specific or group semantics. Later stability does not retroactively
change the generic delivery or remove the original residual from screening.

The trace retains semantic evidence counts but omits repeated evidence histories.
`semantic-blocker-diagnostics.json`, bound to the residual hash, can prove
insufficient supporting observations for one residual. The remaining 53 retain
`UNKNOWN` blockers: individual score/configuration causes cannot be reconstructed
from omitted histories. This is an evidence limitation, not proof of a fusion bug.
Neither support thresholds nor expiry policies were weakened to increase naming.

## Isolated optional candidate screening

Each candidate used the same 54 residual source frames, FP32, verified CUDA model
and output tensors, and a parent-enforced five-minute wall budget. Only one neural
candidate ran at a time. These are single-frame model screenings, not temporal
fusion or end-to-end Guardian qualification.

| Candidate             | Completed residual frames | Provider-call P95 | Peak Torch-reserved VRAM | Sampled process RSS |
| --------------------- | ------------------------: | ----------------: | -----------------------: | ------------------: |
| YOLOE-11s prompt-free |                     54/54 |        125.270 ms |                  514 MiB |            1,498 MB |
| YOLOv8s-World-v2      |                     54/54 |        122.504 ms |                  122 MiB |            1,513 MB |
| Grounding DINO Base   |                Incomplete |     Not qualified |            Not qualified |       Not qualified |

Candidate summaries contain startup/warmup, preprocessing/inference/postprocessing
quantiles, prediction hashes and explicit denominators. RSS samples are not true
allocation peaks; Torch-reserved VRAM is not whole-device memory usage. The teacher
was terminated after about 48 seconds when free system RAM fell below 2 GiB.
Its incomplete output is excluded. All candidate GPU allocations recovered to the
observed baseline after process exit.

Decision in `candidate-selection.json`: pinned PicoDet-S remains primary;
`OPTIONAL_SEMANTIC_ENRICHER = NONE`. The local model registry retains research-only
clearance for YOLOE/YOLO-World, marginal stable semantic recovery is unestablished,
and no contended whole-pipeline qualification exists for either. This is not a new
legal opinion or proof that optional enrichment could never help.

## Performance and remaining gates

A separately supervised optimization probe, `alpha-gpu-optimization-01`, stopped
after ten seconds at the same RAM reserve. There is no completed parity, profiling,
I/O binding, graph-cache or FP16 result from that attempt, and no optimization was
adopted. GPU memory returned to 6,001 MiB free. Further heavy computation is paused
pending more free system RAM; guards were not reduced.

The batch's CPU roll-canvas probe completed, but canvas geometry/timing does not
establish full-pipeline rotation robustness. Full-video/offline/realtime regression,
selected orientation/view-health integration, final full repository verification,
engine freeze and field/web/TTS experience completion remain open. No physical
phone is connected. Human usefulness, physical accuracy and production safety
remain unvalidated. Task019 has not started.
