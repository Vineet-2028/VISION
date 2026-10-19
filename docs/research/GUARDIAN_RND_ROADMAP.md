# Guardian R&D roadmap

All entries are **PLANNED / UNTESTED**. Hypotheses are proposals, not findings.
Pre-register datasets, privacy/consent, baselines, device matrix and quantitative
acceptance limits before an experiment. Do not tune limits to passing results.
User studies require appropriate consent, supervision and accessibility review.
No neural model, mobile runtime or risk policy is selected by this document.

## A. CAMERA / OPTICS

| Topic / question                                                     | Why it matters                              | Hypothesis                                            | Experiment                                           | Metric                                     | Decision criterion                                                                           | Status             |
| -------------------------------------------------------------------- | ------------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------- | ------------------------------------------ | -------------------------------------------------------------------------------------------- | ------------------ |
| **Camera intrinsics:** How stable are intrinsics across focus modes? | Projection error biases geometry            | Focus changes require separate calibration            | Calibrate at multiple focus settings                 | Reprojection error                         | Choose calibration partition with held-out residuals within a predeclared geometry tolerance | Planned / untested |
| **Field of view:** Which FOV preserves peripheral hazard visibility? | Narrow views miss side hazards              | Wider FOV improves peripheral recall at a detail cost | Replay paired narrow/wide captures                   | Peripheral recall and pixels per hazard    | Select Pareto option against predeclared recall and detail goals                             | Planned / untested |
| **Distortion:** Is undistortion needed before geometry?              | Edge distortion biases distance and bearing | Calibration reduces edge bias                         | Compare calibrated and raw geometric estimates       | Bearing error by image radius              | Require lower held-out edge error without unacceptable latency                               | Planned / untested |
| **Rolling shutter:** How much motion skew affects tracking?          | Rows represent different capture times      | Row-time compensation reduces fast-turn bias          | Replay known angular motion at several exposures     | Track residual versus row and angular rate | Adopt compensation only with reproducible error reduction                                    | Planned / untested |
| **Low light:** When must perception declare degradation?             | Missed hazards increase in darkness         | Exposure metadata predicts recall loss                | Measure replay recall across controlled illumination | Recall versus lux and exposure             | Calibrate degradation signal on held-out scenes                                              | Planned / untested |
| **Motion blur:** Can blur scores predict unreliable observations?    | Fast motion removes details                 | Blur score tracks detection failure                   | Compare motion speeds and shutter settings           | Recall and blur-score calibration          | Choose criterion using held-out error costs                                                  | Planned / untested |
| **Calibration:** How is calibration validity detected?               | Stale calibration creates systematic error  | Residual monitoring detects drift                     | Perturb mounts/crops and replay reference targets    | Drift detection recall and false positives | Require early drift detection with an agreed false-alarm budget                              | Planned / untested |

## B. SENSOR FUSION

| Topic / question                                                                     | Why it matters                                | Hypothesis                                 | Experiment                                                 | Metric                                     | Decision criterion                                             | Status             |
| ------------------------------------------------------------------------------------ | --------------------------------------------- | ------------------------------------------ | ---------------------------------------------------------- | ------------------------------------------ | -------------------------------------------------------------- | ------------------ |
| **Accelerometer:** What biases vary by device and temperature?                       | Bias corrupts motion estimates                | Stationary calibration reduces bias        | Collect consented stationary and controlled-motion samples | Bias and Allan deviation                   | Select correction validated across temperature and devices     | Planned / untested |
| **Gyroscope:** How fast does yaw drift accumulate?                                   | Yaw error changes relative geometry           | Bias estimation limits short-horizon drift | Replay reference rotations and stationary periods          | Angular drift per minute                   | Meet a predeclared short-horizon angular error limit           | Planned / untested |
| **Gravity:** How reliably can gravity be separated from translation?                 | Incorrect subtraction fabricates acceleration | Fusion beats accelerometer-only separation | Compare controlled tilts and translations                  | Linear-acceleration error                  | Choose method with lower held-out error during both conditions | Planned / untested |
| **Device orientation:** Which orientation estimator survives walking motion?         | Device pose differs from user heading         | Fusion improves tilt estimates             | Compare walking/carry poses against reference              | Orientation error percentiles              | Select estimator meeting error and latency goals               | Planned / untested |
| **Timestamp synchronization:** What camera/IMU clock offset and drift remain?        | Misalignment creates false relative motion    | Offset estimation reduces fusion residuals | Use synchronized motion events over long captures          | Offset and drift uncertainty               | Bound residual time error before fusion is trusted             | Planned / untested |
| **Camera/IMU extrinsics:** How do orientation and camera selection alter extrinsics? | Hard-coded transforms fail across devices     | Per-configuration calibration is necessary | Calibrate multiple cameras and orientations                | Rotation/translation calibration residuals | Require validated transform provenance for each configuration  | Planned / untested |

## C. OBJECT DETECTION

| Topic / question                                                                       | Why it matters                                | Hypothesis                                                       | Experiment                                                    | Metric                             | Decision criterion                                   | Status             |
| -------------------------------------------------------------------------------------- | --------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------- | ---------------------------------- | ---------------------------------------------------- | ------------------ |
| **Model architecture comparison:** Which detector maximizes hazard recall per latency? | Missed hazards and delayed output both matter | A smaller specialized model can outperform a generic large model | Evaluate licensed held-out hazard scenes on candidate devices | Hazard recall and P95 latency      | Select a validated recall/latency Pareto frontier    | Planned / untested |
| **Small-object recall:** How early are small hazards detected?                         | Late detections reduce warning lead time      | Multi-scale inputs improve small-object recall                   | Stratify evaluation by pixel area and range                   | Recall by size/range               | Require benefit at a predeclared compute budget      | Planned / untested |
| **Mobile latency:** How does sustained detector latency vary?                          | Warm timing hides throttling                  | Steady-state tails dominate usefulness                           | Run sustained inference at controlled ambient temperatures    | P50/P90/P95/P99 latency            | Meet predeclared sustained tail budget               | Planned / untested |
| **Quantization:** What recall is lost with reduced precision?                          | Speedups can erase rare hazards               | Representative calibration preserves recall                      | Compare floating-point and quantized held-out outputs         | Per-class recall delta and latency | Reject changes exceeding agreed critical-recall loss | Planned / untested |
| **Class coverage:** Which relevant obstacles are out of taxonomy?                      | Unrecognized obstacles still matter           | Geometry complements semantic labels                             | Audit scenario inventory against candidate classes            | Hazard taxonomy coverage           | Document blind spots and require a fallback strategy | Planned / untested |

## D. TRACKING

| Topic / question                                                                | Why it matters                          | Hypothesis                                    | Experiment                                               | Metric                                    | Decision criterion                                        | Status             |
| ------------------------------------------------------------------------------- | --------------------------------------- | --------------------------------------------- | -------------------------------------------------------- | ----------------------------------------- | --------------------------------------------------------- | ------------------ |
| **ByteTrack-like methods:** Does low-confidence association improve continuity? | Track gaps destabilize motion           | Two-stage association reduces gaps            | Replay identical detections through association variants | HOTA, ID switches, motion error           | Require continuity gain without unacceptable false tracks | Planned / untested |
| **Kalman filtering:** Which process model matches pedestrian motion?            | Wrong noise assumptions hide changes    | Adaptive uncertainty improves coverage        | Replay turns, starts and stops                           | Innovation consistency and velocity error | Require calibrated residual coverage on held-out motion   | Planned / untested |
| **Occlusion:** How long should uncertain tracks be retained?                    | Stale tracks can cause false alerts     | Retention should depend on uncertainty        | Vary occlusion duration in replay                        | Recovery recall and stale-track rate      | Choose policy after measuring both error costs            | Planned / untested |
| **ID switches:** Which scenes cause identity swaps?                             | Swaps create false velocity jumps       | Geometry gating reduces swaps                 | Replay crossings and crowds                              | ID switches and induced motion outliers   | Require lower outlier rate without recall loss            | Planned / untested |
| **Re-identification necessity:** Is appearance re-ID worth its cost?            | Embeddings add privacy and compute cost | Short-lived local tracking may not need re-ID | Ablate re-ID in representative occlusions                | Continuity gain, memory and latency       | Add only if measured benefit exceeds agreed cost          | Planned / untested |

## E. DEPTH

| Topic / question                                                                | Why it matters                                | Hypothesis                                       | Experiment                                           | Metric                                           | Decision criterion                                      | Status             |
| ------------------------------------------------------------------------------- | --------------------------------------------- | ------------------------------------------------ | ---------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------------- | ------------------ |
| **Monocular relative depth:** Is relative ordering temporally stable?           | Unstable depth causes unstable motion         | Temporal consistency can improve ordering        | Replay static and moving scenes                      | Rank consistency and temporal variance           | Use only if held-out ordering is reliable               | Planned / untested |
| **Monocular metric depth:** Can absolute scale generalize to new devices?       | Scale errors bias TTC                         | Device-aware calibration reduces scale error     | Evaluate measured ranges across devices/scenes       | Absolute relative error and calibration coverage | Require validated metric error bounds before SI use     | Planned / untested |
| **Temporal scaling:** Can metric scale be maintained over time?                 | Scale drift appears as motion                 | Motion constraints stabilize scale               | Evaluate long sequences with reference geometry      | Scale drift and range error                      | Reject methods with unbounded drift                     | Planned / untested |
| **Known-size constraints:** When are size priors informative?                   | Object size varies greatly                    | Broad uncertainty avoids false precision         | Compare priors across object-size distributions      | Range error and uncertainty coverage             | Accept only calibrated intervals on varied instances    | Planned / untested |
| **Motion parallax:** Does user motion provide useful scale cues?                | Pure rotation provides no translational depth | Translation helps when pose is accurate          | Replay translation and rotation separately           | Depth error versus baseline and pose error       | Gate use on observability and measured uncertainty      | Planned / untested |
| **Future stereo/depth hardware:** What hardware improves adverse-scene ranging? | Active sensors have range/light limits        | Stereo or depth sensors fill some monocular gaps | Compare candidate hardware across lighting/materials | Valid range fraction and error tails             | Adopt only with clear coverage benefit and power budget | Planned / untested |

## F. OPTICAL FLOW

| Topic / question                                                          | Why it matters                                 | Hypothesis                                                | Experiment                                      | Metric                                | Decision criterion                                       | Status             |
| ------------------------------------------------------------------------- | ---------------------------------------------- | --------------------------------------------------------- | ----------------------------------------------- | ------------------------------------- | -------------------------------------------------------- | ------------------ |
| **Sparse versus dense flow:** Which flow representation is sufficient?    | Dense flow is more costly                      | Sparse flow may cover ego-motion needs                    | Compare both on identical replay                | Motion residuals and P95 latency      | Select least costly method meeting residual goals        | Planned / untested |
| **Camera ego-motion:** Can flow separate rotation and translation?        | Camera movement affects every pixel            | IMU rotation compensation improves flow                   | Compare compensated and uncompensated flow      | Background residual motion            | Require reduction across carry poses and lighting        | Planned / untested |
| **Moving-object separation:** Can foreground motion survive compensation? | Incorrect background assumptions erase hazards | Robust background estimation preserves independent motion | Evaluate crowded and dominant-foreground scenes | Moving-object recall and false motion | Require reliable separation in held-out difficult scenes | Planned / untested |

## G. WALKABLE SPACE

| Topic / question                                                              | Why it matters                                  | Hypothesis                                      | Experiment                                          | Metric                                       | Decision criterion                                         | Status             |
| ----------------------------------------------------------------------------- | ----------------------------------------------- | ----------------------------------------------- | --------------------------------------------------- | -------------------------------------------- | ---------------------------------------------------------- | ------------------ |
| **Semantic segmentation:** Does segmentation transfer across environments?    | Sidewalk labels do not guarantee traversability | Geometry improves semantic free-space inference | Replay varied surfaces and regions                  | Walkable-space precision/recall              | Require held-out generalization and documented blind spots | Planned / untested |
| **Geometric free space:** Can occupied volume be estimated without semantics? | Unknown classes may still obstruct travel       | Geometry complements semantic detection         | Evaluate unlabeled obstacles and open routes        | Obstacle recall and false blocked space      | Select fusion only after measured gain                     | Planned / untested |
| **Curbs:** Which cues expose small elevation changes?                         | Low vertical features are easily missed         | Depth edges plus appearance improve recall      | Measure curb approaches at varied angles            | Recall versus distance and curb height       | Meet a predeclared lead-time recall criterion              | Planned / untested |
| **Stairs:** Can ascending and descending stairs be distinguished?             | Descending edges may be visually subtle         | Temporal geometry helps staircase direction     | Evaluate both directions and lighting               | Direction confusion and detection lead time  | Require adequate held-out recall for both directions       | Planned / untested |
| **Holes:** How are negative obstacles observed?                               | Absence of depth is not proof of a hole         | Multiple cues reduce false hole detections      | Compare shadows, drains and real depressions safely | Negative-obstacle recall and false positives | Require reliable distinction before user warnings          | Planned / untested |
| **Obstacles:** What ground-level objects evade detectors?                     | Small clutter can be a trip hazard              | Near-field geometry complements classes         | Curate licensed/consented ground-hazard scenes      | Ground-level recall by size/material         | Document minimum observable sizes and failure modes        | Planned / untested |

## H. MOTION / PHYSICS

| Topic / question                                                           | Why it matters                            | Hypothesis                                            | Experiment                                                     | Metric                                       | Decision criterion                                      | Status             |
| -------------------------------------------------------------------------- | ----------------------------------------- | ----------------------------------------------------- | -------------------------------------------------------------- | -------------------------------------------- | ------------------------------------------------------- | ------------------ |
| **Differentiation:** How does timing error affect raw derivatives?         | Small dt amplifies noise                  | Timestamp uncertainty predicts error growth           | Inject controlled noise into analytical trajectories           | Velocity/acceleration error versus dt        | Validate error model before downstream use              | Planned / untested |
| **Filtering:** Which filter improves noise without late warnings?          | Smoothing adds lag                        | A bounded filter can reduce noise with acceptable lag | Replay abrupt turns and steady motion                          | Error, phase lag and settling time           | Choose only after agreeing lag/error tradeoff           | Planned / untested |
| **Velocity:** How accurate is world-frame relative velocity?               | Ego-motion errors mimic object motion     | Pose compensation lowers bias                         | Compare against reference relative trajectories                | Velocity error by axis                       | Require bounded held-out error and uncertainty coverage | Planned / untested |
| **Acceleration:** When does acceleration improve short-horizon prediction? | Second derivatives amplify noise          | Acceleration helps only above observability limits    | Compare constant-velocity and accelerated predictions          | Prediction error versus horizon              | Use only where measured improvement is repeatable       | Planned / untested |
| **TTC:** When is radial TTC informative?                                   | Sideways motion can give misleading TTC   | CPA context reduces TTC misinterpretation             | Evaluate collision and near-miss trajectories                  | TTC error and false-collision interpretation | Restrict use to validated geometry regimes              | Planned / untested |
| **CPA:** How robust is constant-velocity CPA under turns?                  | Future motion need not remain linear      | Uncertainty grows with horizon and curvature          | Replay controlled turns and acceleration                       | Closest-distance/time error                  | Define horizon limits from held-out residuals           | Planned / untested |
| **Trajectory uncertainty:** How should joint uncertainty propagate?        | Point estimates hide risk-relevant spread | Covariance-aware propagation improves coverage        | Compare sampling and linearization on known noisy trajectories | Coverage and compute cost                    | Require calibrated intervals before risk policy         | Planned / untested |

## I. RISK

| Topic / question                                                      | Why it matters                              | Hypothesis                                           | Experiment                                                  | Metric                                      | Decision criterion                                | Status             |
| --------------------------------------------------------------------- | ------------------------------------------- | ---------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------- | ------------------ |
| **Risk calibration:** How should geometric evidence map to decisions? | Physics alone cannot define useful warnings | Evaluation-based calibration beats arbitrary weights | Replay labeled consented scenarios after physics validation | Calibration and hazard recall               | Pre-register criteria with domain and user review | Planned / untested |
| **Critical hazard recall:** Which failures have greatest consequence? | Average recall hides severe misses          | Severity-stratified evaluation exposes gaps          | Evaluate a reviewed scenario taxonomy                       | Recall by hazard and condition              | Require agreed per-stratum acceptance criteria    | Planned / untested |
| **False alerts:** What false-alert rate becomes annoying?             | Frequent errors reduce trust                | Tolerance depends on context and repetition          | Conduct approved controlled user studies                    | False alerts per hour and annoyance ratings | Set policy only from study evidence               | Planned / untested |
| **Warning lead time:** Which lead time is useful without being early? | Late and premature alerts both burden users | Useful intervals depend on action and walking speed  | Conduct controlled supervised studies                       | Response success and perceived timing       | Choose ranges supported by user-study results     | Planned / untested |

## J. ATTENTION

| Topic / question                                                        | Why it matters                              | Hypothesis                                       | Experiment                                    | Metric                                       | Decision criterion                                            | Status             |
| ----------------------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------ | --------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------- | ------------------ |
| **Suppression:** When should redundant alerts be suppressed?            | Suppression may hide a changing hazard      | State-aware suppression reduces noise            | Replay repeated and escalating hazards        | Missed updates and alert count               | Require fewer redundant alerts without critical-update loss   | Planned / untested |
| **Deduplication:** How are multiple observations linked to one alert?   | Duplicate detections create repeated speech | Track-aware grouping improves consistency        | Replay overlapping detections and ID switches | Duplicate-alert and merged-hazard rates      | Avoid merging distinct hazards while reducing duplicates      | Planned / untested |
| **Alert frequency:** What cadence preserves awareness?                  | Excessive speech overloads attention        | Cadence should depend on change and user context | Approved cadence comparison study             | Comprehension and annoyance                  | Adopt only evidence-backed cadence policy                     | Planned / untested |
| **Speech interruption:** When should an alert interrupt speech?         | Long utterances delay urgent information    | Priority-aware interruption improves lead time   | Simulate competing messages under supervision | Time to actionable content and comprehension | Require improved response without confusion                   | Planned / untested |
| **User cognitive load:** How much concurrent information is manageable? | Detailed output competes with navigation    | Minimal actionable cues lower workload           | Approved comparative user study               | Task success and workload ratings            | Select design supported by both performance and user feedback | Planned / untested |

## K. USER EXPERIENCE

| Topic / question                                                                 | Why it matters                               | Hypothesis                                         | Experiment                                    | Metric                                 | Decision criterion                                        | Status             |
| -------------------------------------------------------------------------------- | -------------------------------------------- | -------------------------------------------------- | --------------------------------------------- | -------------------------------------- | --------------------------------------------------------- | ------------------ |
| **Verbosity:** Which detail level is useful by context?                          | More words delay action                      | Context-sensitive verbosity improves comprehension | Compare short and detailed supervised prompts | Comprehension and response latency     | Require usefulness without increased response delay       | Planned / untested |
| **Spatial audio:** Does spatial rendering improve localization?                  | Hearing and headphones vary                  | Spatial cues improve bearing comprehension         | Controlled localization study                 | Angular response error                 | Adopt with accessibility fallback and measured benefit    | Planned / untested |
| **Haptics:** Which patterns are distinguishable while walking?                   | Patterns may be confused or missed           | Small pattern sets improve recognition             | Approved walking/simulated-motion study       | Recognition/confusion matrix           | Require reliable distinctions before adding patterns      | Planned / untested |
| **Direction wording:** Which directional language is least ambiguous?            | Device heading may differ from body heading  | Body-referenced wording reduces confusion          | Compare wording under varied carry poses      | Direction comprehension error          | Choose only after reference-frame comprehension testing   | Planned / untested |
| **Blind-user studies:** How should evaluation reflect real assistive needs?      | Sighted simulation misses important needs    | Co-design reveals overlooked failure modes         | Ethically approved participatory study        | Qualitative findings and task outcomes | Require participant-informed acceptance criteria          | Planned / untested |
| **Personalization:** Which preferences help without hiding critical information? | Users differ in experience and sensory needs | Limited explicit preferences improve usability     | Compare configurable versus fixed interfaces  | Preference stability and task outcomes | Permit only settings with understood failure implications | Planned / untested |

## L. MOBILE PERFORMANCE

| Topic / question                                                      | Why it matters                                        | Hypothesis                                            | Experiment                                                  | Metric                                      | Decision criterion                                          | Status             |
| --------------------------------------------------------------------- | ----------------------------------------------------- | ----------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------- | ----------------------------------------------------------- | ------------------ |
| **CPU:** Which workloads dominate CPU time?                           | Contention increases tail latency                     | Scheduling can reduce contention                      | Profile sustained representative workloads                  | CPU time and latency tails                  | Keep workload within predeclared sustained budget           | Planned / untested |
| **GPU:** Does GPU acceleration reduce end-to-end latency?             | Transfers may erase kernel speedups                   | GPU helps only some graph shapes                      | Compare complete paths including transfers                  | End-to-end latency and power                | Choose by measured total cost rather than kernel timing     | Planned / untested |
| **NPU:** Which operators actually execute on accelerators?            | Fallback can cause unpredictable stalls               | Supported graphs improve sustained efficiency         | Inspect delegation and profile candidate devices            | Delegated fraction and tail latency         | Require stable full-path gains across target devices        | Planned / untested |
| **NNAPI:** Is platform delegation viable on supported devices?        | Driver/support behavior varies                        | Device-specific benchmarking is necessary             | Review current platform support and run compatibility tests | Failure rate and sustained latency          | Select only supported validated device/runtime combinations | Planned / untested |
| **XNNPACK:** Is CPU delegation a reliable fallback?                   | Accelerator availability is inconsistent              | Optimized CPU path provides predictable fallback      | Benchmark candidate graphs and thread counts                | P95/P99 latency and power                   | Require usable sustained fallback before selection          | Planned / untested |
| **Quantization:** What memory and energy benefits persist?            | Precision changes alter both performance and accuracy | Reduced precision improves sustained efficiency       | Joint accuracy/energy benchmark                             | Recall delta, joules/frame, peak memory     | Accept only within predeclared accuracy constraints         | Planned / untested |
| **Frame scheduling:** Which computations need 30 Hz?                  | Running every stage each frame wastes work            | Mixed-rate scheduling preserves useful response time  | Replay varied rates with time-correct evaluation            | Hazard lead time, freshness and power       | Choose rates from measured lead-time/freshness needs        | Planned / untested |
| **Thermal throttling:** At what temperature does performance degrade? | Short benchmarks conceal sustained slowdown           | Thermal-aware workload adjustment limits tail growth  | Sustained runs across ambient/device temperatures           | Temperature and latency versus elapsed time | Define degradation policy from reproducible throttle curves | Planned / untested |
| **Battery:** What runtime is achievable under sustained use?          | High drain limits practical use                       | Duty cycling reduces energy with acceptable freshness | Measure controlled long-running sessions                    | Energy per hour and alert freshness         | Set product budget only after representative measurements   | Planned / untested |

## M. FAILURE MODES

| Topic / question                                               | Why it matters                                  | Hypothesis                                           | Experiment                                              | Metric                                     | Decision criterion                                            | Status             |
| -------------------------------------------------------------- | ----------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------ | ------------------------------------------------------------- | ------------------ |
| **Dark scenes:** When should output be explicitly degraded?    | Uncertain perception must not imply clear space | Quality signals predict dark-scene failure           | Sweep illumination and camera exposure                  | Degradation detection and missed hazards   | Require calibrated degradation without claiming safety        | Planned / untested |
| **Rain:** Which artifacts cause persistent errors?             | Drops and reflections alter the image           | Temporal quality checks detect obscuration           | Safely replay rain/covered-lens scenes                  | Failure detection and false alerts         | Document operating limits and reliable degradation behavior   | Planned / untested |
| **Glare:** How do saturation and sun angle affect recall?      | Glare hides obstacles                           | Saturation metrics expose some failures              | Evaluate controlled glare angles                        | Recall and degraded-state accuracy         | Require detection of harmful glare regimes                    | Planned / untested |
| **Occlusion:** How should hidden hazards affect uncertainty?   | Hidden does not mean absent                     | Uncertainty-aware retention is better than certainty | Replay progressive and abrupt occlusion                 | Miss rate and false retained hazards       | Choose behavior using evaluated uncertainty and user feedback | Planned / untested |
| **Camera blocked:** How quickly is obstruction recognized?     | A running camera may provide no useful scene    | Image-quality checks can detect blockage             | Replay covers, blur and dark surfaces                   | Detection latency and false positives      | Meet a predeclared detection and false-alarm budget           | Planned / untested |
| **Dropped frames:** How does irregular sampling affect motion? | Assuming fixed dt corrupts derivatives          | Actual timestamps preserve correctness               | Inject deterministic drops and jitter                   | Motion error and output age                | Reject stale outputs and maintain measured error bounds       | Planned / untested |
| **Sensor loss:** How are partial sensor failures represented?  | Missing inputs can invalidate fusion            | Explicit validity enables graceful degradation       | Inject sensor outages and delayed events                | Detection latency and recovery correctness | No fabricated estimates during invalid intervals              | Planned / untested |
| **Model failure:** How do runtime errors affect the loop?      | Crashes must not produce stale certainty        | Bounded failure handling isolates inference          | Inject timeout/error conditions in future adapter tests | Recovery time and stale-output count       | Require explicit unavailable output and bounded recovery      | Planned / untested |

## Task 003 camera experiments

All experiments below are **STATUS=PLANNED**. No device results or accuracy claims
exist. Set application-specific acceptance bounds before collecting evaluation
data, and retain failures in the denominator.

| ID          | QUESTION                                               | HYPOTHESIS                                                  | EXPERIMENT                                                                | METRIC                                                          | DECISION CRITERION                                                                | STATUS  |
| ----------- | ------------------------------------------------------ | ----------------------------------------------------------- | ------------------------------------------------------------------------- | --------------------------------------------------------------- | --------------------------------------------------------------------------------- | ------- |
| RND-CAM-001 | Are intrinsics repeatable?                             | Fixed capture modes yield stable fits                       | Repeat independent calibration sessions with held-out views               | Parameter spread, spatial residuals, holdout RMS                | Accept only modes within predeclared bearing-error budget across sessions         | PLANNED |
| RND-CAM-002 | Which distortion family fits each lens?                | Brown suffices for some lenses, not all                     | Compare ideal, Brown and alternative offline fits with domain validation  | Holdout residual distribution, inversion failures, coverage     | Choose supported model meeting held-out budget without ambiguous inverse branches | PLANNED |
| RND-CAM-003 | Are resolution/crop transforms exact?                  | Recorded actual preprocessing preserves geometry            | Replay targets through scale/crop/rotation and odd-padding pipelines      | Pixel roundtrip and calibrated bearing errors                   | Require analytic consistency and measured error below predeclared adapter budget  | PLANNED |
| RND-CAM-004 | How accurate is pixel-to-bearing?                      | Calibration improves over normalized-coordinate heuristics  | Compare rays against surveyed target bearings across image                | Angular bias, P50/P95/P99 errors by region                      | Meet predeclared angular budget including edge and failure cases                  | PLANNED |
| RND-CAM-005 | Are camera-to-device extrinsics stable?                | Measured transforms outperform centered/aligned assumptions | Repeated physical-reference rotation/translation calibration              | Angular/translation error, repeatability                        | Require held-out composition error within pose budget                             | PLANNED |
| RND-CAM-006 | When are ground intersections useful?                  | Error grows with shallow ray angle and pose uncertainty     | Survey ground targets across tilt, height, slope and distance             | Position-error distribution, unavailable fraction, conditioning | Bound operating domain before accepting nominal coordinates for downstream use    | PLANNED |
| RND-CAM-007 | How do low light and blur affect calibration?          | Corner degradation destabilizes fitted parameters           | Controlled illumination/exposure/motion sweep with held-out targets       | Rejection rate, residuals, repeatability and bearing error      | Identify degraded regimes and prevent unsupported quality labels                  | PLANNED |
| RND-CAM-008 | Does digital stabilization alter effective intrinsics? | Per-frame crop/warp invalidates one static calibration      | Compare EIS off/on sequences against static targets and supplied metadata | Time-varying ray error, missing-transform rate                  | Use only modes with sufficient geometry metadata or explicitly reject/degrade     | PLANNED |

Later performance experiments should compare caller ray reuse, precomputed ray maps,
distortion lookup grids, vectorization and native SIMD against this deterministic
reference. Include interpolation error, memory, invalidation on calibration changes,
thread safety, sustained thermal state and tail latency; do not optimize from desktop
mean timing alone.

## Task 004 temporal and IMU experiments

All entries are planned; no hardware measurements or accuracy claims exist.
Decision budgets must be specified before collecting evaluation data.

| ID             | QUESTION                                           | WHY IT MATTERS                                     | HYPOTHESIS                                                     | EXPERIMENT                                                            | METRIC                                                   | DECISION CRITERION                                                              | STATUS  |
| -------------- | -------------------------------------------------- | -------------------------------------------------- | -------------------------------------------------------------- | --------------------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------- | ------- |
| RND-IMU-001    | What is gyro noise across modes?                   | Noise affects short-term orientation.              | Stationary noise varies by mode and temperature.               | Record stationary local streams across rates and thermal states.      | Rate variance, spectral density, integration error.      | Select a noise model only after held-out residual checks.                       | PLANNED |
| RND-IMU-002    | What is accelerometer noise?                       | Second integration amplifies errors.               | Mode-dependent noise needs calibrated parameters.              | Capture controlled stationary orientations and repeated sessions.     | Per-axis variance, spectrum, repeatability.              | Accept parameters only within predeclared held-out error bounds.                | PLANNED |
| RND-IMU-003    | How does gyro bias vary with temperature?          | Constant bias correction can become stale.         | Temperature explains some bias variation.                      | Repeat stationary thermal sweeps with reference orientation.          | Bias drift versus temperature and time.                  | Use compensation only if repeatable improvements survive holdouts.              | PLANNED |
| RND-IMU-004    | How does accelerometer bias depend on orientation? | Gravity and bias can be confused.                  | Multi-orientation calibration reveals bias/scale errors.       | Use surveyed orientations and repeated stationary captures.           | Residual specific force, scale/misalignment error.       | Require held-out gravity-compensation error within a preregistered budget.      | PLANNED |
| RND-IMU-005    | What is camera/IMU timestamp offset?               | Misalignment corrupts pose at capture.             | Metadata alone may not characterize effective exposure timing. | Compare synchronized visible motion with IMU motion per capture mode. | Offset and uncertainty across sessions.                  | Permit mapping only with measured error below an application budget.            | PLANNED |
| RND-IMU-006    | Does camera/IMU clock offset drift?                | A constant mapping can fail over long runs.        | Some pipelines need bounded affine drift models.               | Repeat long-duration synchronized motion under thermal changes.       | Offset slope, residual jitter, mapping failure rate.     | Use affine mapping only if held-out timing error improves reliably.             | PLANNED |
| RND-IMU-007    | How accurate is pose interpolation?                | Sparse pose samples can hide rapid motion.         | Error depends on span and motion regime.                       | Compare subsampled poses against high-rate reference motion.          | Angular/translation error versus span and rotation.      | Choose maximum span using validated error bounds, including failures.           | PLANNED |
| RND-IMU-008    | How accurate is gravity compensation?              | Tilt error leaks gravity into linear acceleration. | Orientation error dominates some regimes.                      | Test stationary orientations and reference-controlled accelerations.  | Residual acceleration, bias and tilt sensitivity.        | Bound usable conditions before interpreting output as motion.                   | PLANNED |
| RND-IMU-009    | When are stationary candidates reliable?           | False stationary updates can corrupt fusion.       | Combined gyro/force criteria outperform one signal.            | Replay rest, vibration, constant velocity, rotation and acceleration. | False candidates, missed rest, detection delay.          | Choose thresholds on held-out cases without treating candidates as proof.       | PLANNED |
| RND-IMU-010    | What filter lag buys useful noise reduction?       | Smoothed but late motion may be misleading.        | Cutoff should depend on latency and noise evidence.            | Replay known steps and motion over irregular timing.                  | Noise reduction, phase lag, step delay and failure rate. | Choose cutoff only after a preregistered error/lag tradeoff.                    | PLANNED |
| RND-IMU-011    | What is each mode's rolling-shutter readout?       | Rows need different motion timestamps.             | Scan/readout behavior differs by mode.                         | Use controlled flashes/motion and compare reported metadata.          | First-last readout error, direction, repeatability.      | Enable row-time correction only for validated modes.                            | PLANNED |
| RND-IMU-012    | Which orientation source is reliable?              | Vendor fusion can differ across devices.           | Adapter estimates may outperform uncalibrated custom fusion.   | Compare available orientation sources against reference rotations.    | Angular error, drift, latency, reset behavior.           | Select source based on held-out accuracy/freshness and explicit degraded cases. | PLANNED |
| RND-MOTION-001 | How accurate are streaming velocity estimates?     | Finite differences amplify position noise.         | Timing-aware filtering improves some noise/lag regimes.        | Synthetic and reference trajectories with noise, gaps and outliers.   | Velocity error, temporal lag and unavailable fraction.   | Choose policies with held-out error and lag budgets.                            | PLANNED |
| RND-MOTION-002 | When is acceleration estimation usable?            | Second derivatives are especially noisy.           | Filtered acceleration is useful only in a restricted domain.   | Reference velocity profiles with timing jitter and correlated noise.  | Acceleration error, lag, outlier behavior.               | Keep acceleration unavailable outside validated conditions.                     | PLANNED |
| RND-MOTION-003 | When does CA improve on CV prediction?             | Noisy acceleration can worsen prediction.          | CA helps only when acceleration is sufficiently reliable.      | Compare CP/CV/CA on held-out short-horizon trajectories.              | Error versus horizon, uncertainty coverage and failures. | Use CA only where its measured gain exceeds added uncertainty.                  | PLANNED |

Complementary fusion and ESKF remain contingent research following these measurements.
Evaluate whether an ESKF using measured bias/noise models improves held-out pose error
and consistency over adapter orientation; record tuning, failures, compute and resets.
Do not adopt a larger estimator without an observed benefit and uncertainty validation.

### RND-FUSION-001: Error-state fusion feasibility

- QUESTION: Does an ESKF improve on validated adapter orientation and bounded gyro propagation?
- WHY IT MATTERS: Larger estimators add tuning, observability and reset risks.
- HYPOTHESIS: Measured bias/noise models plus external corrections can improve consistency.
- EXPERIMENT: After IMU characterization, compare an isolated offline prototype against the V1 baseline on held-out trajectories with gaps and resets.
- METRIC: Pose error, uncertainty coverage, drift, failure/recovery rate and compute cost.
- DECISION CRITERION: Adopt only after predeclared accuracy/consistency gains justify complexity and failure behavior is validated.
- STATUS: PLANNED; no ESKF is implemented in Task 004.

## Desktop perception laboratory experiments

All entries below are PLANNED; unit-test fixtures are not hardware experiments.

### RND-LAB-001: video decoder timestamp fidelity

- QUESTION: Can decoded PTS reproduce the encoder timeline?
- WHY IT MATTERS: Fusion needs correct observation time.
- HYPOTHESIS: Rational PTS preserves authored timing within one nanosecond quantization.
- EXPERIMENT: Encode CFR and VFR fixtures with known PTS, decode multiple containers/codecs.
- METRIC: PTS error, missing/duplicate rate.
- DECISION CRITERION: Require exact rational-floor agreement for supported fixtures; document container quantization.
- STATUS: PLANNED

### RND-LAB-002: realtime drop policy comparison

- QUESTION: Which policy preserves useful freshness?
- WHY IT MATTERS: Completeness competes with latency.
- HYPOTHESIS: Latest-frame minimizes age while drop-oldest preserves more continuity.
- EXPERIMENT: Replay identical workloads with simulated and measured consumer delays.
- METRIC: Drop fraction, result age P50/P90/P95/P99.
- DECISION CRITERION: Choose per workload only after a specified freshness/continuity target.
- STATUS: PLANNED

### RND-LAB-003: queue capacity versus latency

- QUESTION: How much capacity helps without stale backlog?
- WHY IT MATTERS: Large queues hide overload.
- HYPOTHESIS: Small bounded queues limit age under realistic bursts.
- EXPERIMENT: Sweep capacities and fixed consumer delays on identical clips.
- METRIC: Peak depth, output age, drops, throughput.
- DECISION CRITERION: Reject configurations exceeding the declared freshness limit.
- STATUS: PLANNED

### RND-LAB-004: frame-copy overhead

- QUESTION: Where do full-frame copies dominate?
- WHY IT MATTERS: HD arrays consume memory bandwidth.
- HYPOTHESIS: Identity and crop views avoid most avoidable copies.
- EXPERIMENT: Profile identity, crop, resize and optional renderer separately.
- METRIC: Allocated bytes/frame, latency distributions.
- DECISION CRITERION: Retain views unless measured ownership or lifetime problems justify copying.
- STATUS: PLANNED

### RND-LAB-005: pixel-format conversion cost

- QUESTION: Which explicit conversion is suitable for future inputs?
- WHY IT MATTERS: Models require specific formats.
- HYPOTHESIS: A single decoder-to-required-format conversion beats chained conversions.
- EXPERIMENT: Measure RGB/BGR/GRAY/RGBA paths at representative resolutions.
- METRIC: Conversion ns and allocations.
- DECISION CRITERION: Select only a measured path matching model semantics and accuracy.
- STATUS: PLANNED

### RND-LAB-006: preprocessing latency

- QUESTION: How expensive are geometry-preserving transforms?
- WHY IT MATTERS: Preprocessing consumes the same latency budget as inference.
- HYPOTHESIS: Cached geometry and bounded array operations are sufficient.
- EXPERIMENT: Benchmark resize/crop/integer-letterbox with roundtrip fixtures.
- METRIC: Latency distributions, coordinate error.
- DECISION CRITERION: Require exact declared mapping and a predeclared hardware budget.
- STATUS: PLANNED

### RND-LAB-007: desktop/mobile numerical parity

- QUESTION: Do shared core results agree across runtimes?
- WHY IT MATTERS: Desktop evidence must transfer to device implementations.
- HYPOTHESIS: The same core JAR conventions prevent convention drift.
- EXPERIMENT: Run identical calibration/transform/ray vectors on desktop and future Android.
- METRIC: Absolute/relative error and rejected-domain agreement.
- DECISION CRITERION: Require agreed tolerances and identical availability semantics before parity claims.
- STATUS: PLANNED

### RND-LAB-008: replay determinism

- QUESTION: Which outputs are reproducible across runs?
- WHY IT MATTERS: Regression comparisons need stable semantics.
- HYPOTHESIS: Offline identity, scheduling and no-op results are repeatable.
- EXPERIMENT: Replay same source/config multiple times and compare excluding measured timing and UUID.
- METRIC: Semantic mismatch count.
- DECISION CRITERION: Zero mismatches for deterministic components on supported inputs.
- STATUS: PLANNED

### RND-LAB-009: variable-frame-rate handling

- QUESTION: Do gaps and changing cadence retain observation identity?
- WHY IT MATTERS: Average FPS hides timing variation.
- HYPOTHESIS: Source-time scheduling handles VFR without index assumptions.
- EXPERIMENT: Use irregular authored PTS, forward gaps and malformed sequences.
- METRIC: Accepted timestamps, rejection reasons, scheduling slots.
- DECISION CRITERION: Exact expected times and explicit rejection of invalid epochs.
- STATUS: PLANNED

### RND-LAB-010: long-session memory stability

- QUESTION: Does retained memory plateau?
- WHY IT MATTERS: Unbounded retention breaks long experiments.
- HYPOTHESIS: Bounded queues and recent metrics keep application state bounded.
- EXPERIMENT: Run long synthetic and real-video sessions with allocation/RSS profiling.
- METRIC: Live references, RSS trend, queue depth.
- DECISION CRITERION: No monotonic retained-frame growth after warmup; investigate native allocator behavior separately.
- STATUS: PLANNED

### RND-LAB-011: decoder error recovery

- QUESTION: Which corruption permits defensible continuation?
- WHY IT MATTERS: Silent decoder damage can contaminate evaluation.
- HYPOTHESIS: Packet failures can be accounted without fabricating missing frames.
- EXPERIMENT: Inject truncation and corruption into disposable generated fixtures.
- METRIC: Recoverable/fatal classification, valid frames after error, cleanup.
- DECISION CRITERION: No swallowed fatal error; classify unsupported recovery explicitly.
- STATUS: PLANNED

### RND-LAB-012: scheduler accuracy under variable source FPS

- QUESTION: Does fixed scheduling accumulate phase drift?
- WHY IT MATTERS: Mixed-rate components must remain aligned to source time.
- HYPOTHESIS: Anchored integer intervals skip missed slots without drift.
- EXPERIMENT: Sweep VFR timelines and component intervals against an analytical slot oracle.
- METRIC: Eligibility error and phase drift.
- DECISION CRITERION: Zero drift relative to anchored slots, with at most one call per due frame.
- STATUS: PLANNED
