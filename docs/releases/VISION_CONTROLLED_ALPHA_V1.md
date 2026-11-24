# VISION Controlled Alpha V1 engine

The measured local engine is frozen in
`benchmark-results/v02/VISION_CONTROLLED_ALPHA_V1/manifest.json`. Its SHA-256 is
`ecd83215cc8f8e144ec9126b61415e8ca38b854a4126cfdbc6e52d55affa6254`. It pins
the runtime sources, compiled Guardian JAR, PicoDet FP32, PIDNet, ontology,
configuration, hardware evidence and qualification artifacts.

| First 600 seconds of the source       | Rescued V0 | Controlled Alpha V1 |
| ------------------------------------- | ---------: | ------------------: |
| Published updates                     |      2,641 |               6,300 |
| Publication P50                       | 264.379 ms |          125.572 ms |
| Publication P95                       | 567.211 ms |          257.657 ms |
| Publication P99                       | 716.824 ms |          307.794 ms |
| Failed frames                         |          0 |                   0 |
| Specific / group / generic deliveries | 0 / 0 / 60 |         13 / 2 / 58 |

The whole recording yielded 18,541 updates. The engine dropped zero trace rows,
issued zero text deliveries after expiry, and classified 141 updates as camera
unusable. In the separate 18,000-frame offline comparison, both engines processed
the same source identities. Candidate processing took 49.8 minutes versus 16.9
minutes for V0. On usable frames detector counts differed on one frame, while
active track counts differed on 16,267. The latter is an observable change in
tracking behavior, not a ground-truth recall measurement.

The 21 transformed-clip runs covered 1,260 frames. Correction improved the
aggregate track count relative to raw rotation in six of seven cases. One
darkened clip had fewer track observations after correction. Preserve these
limitations in any review of real camera orientation.

The release applies to the local engine. Field software, participant usefulness,
physical accuracy and public deployment have separate verification requirements.
See the [limitations](VISION_ALPHA_V1_LIMITATIONS.md).
