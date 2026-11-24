# V0.2 model license investigation

Checked 2026-10-27 against publisher sources. This is source evidence, not legal
clearance. No new candidate has been adopted into the realtime product path.

| Candidate                   | Published code terms                                                    | Weight status                                                         | Current decision                                         |
| --------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------- | -------------------------------------------------------- |
| Current PicoDet-S           | Existing pinned V0 model/BOM remains authoritative                      | Existing rescue hash retained                                         | Baseline only                                            |
| THU-MIG YOLOE               | AGPL version 3 in the upstream LICENSE                                  | Exact selected checkpoint and any separate terms still need recording | RESEARCH_ONLY; no product adoption                       |
| AILab-CVC YOLO-World        | Upstream README states GPL-v3 and offers a commercial licensing contact | Exact small checkpoint terms/hash still need recording                | RESEARCH_ONLY; no product adoption                       |
| IDEA-Research GroundingDINO | Apache-2.0 in the upstream LICENSE                                      | Exact offline teacher checkpoint/model card still needs review        | Candidate offline teacher; not yet selected              |
| Ultralytics implementations | Publisher describes AGPL/Enterprise options for code and models         | Do not assume converted weights remove upstream obligations           | Existing research dependency is not commercial clearance |

Sources:

- [YOLOE LICENSE](https://github.com/THU-MIG/yoloe/blob/main/LICENSE)
- [YOLO-World repository and licensing section](https://github.com/AILab-CVC/YOLO-World)
- [GroundingDINO LICENSE](https://github.com/IDEA-Research/GroundingDINO/blob/main/LICENSE)
- [Ultralytics licensing](https://www.ultralytics.com/license)

Each acquired artifact must have an exact source revision/release, SHA256,
precision/input format, runtime support, code license and weight-license evidence
in registry metadata. Code license alone is not assumed to license every weight
or dependency. Attribution/notice and applicable copyleft obligations need review
before redistribution or deployment. No model acquisition, embedding benchmark,
commercial license purchase or training was performed in the initial license pass.

Update 2026-10-28: three Ultralytics release `v8.4.0` assets were subsequently
acquired for research: YOLOE-26n prompt-free, YOLOE-11s prompt-free, and
YOLOv8s-Worldv2. Exact release URLs, published SHA256 digests, sizes and license
status are recorded in `configs/perception/research-models-v02.json`. Local
downloads matched those digests. This does not grant redistribution or product
clearance.

Grounding DINO Base was subsequently acquired at revision
`12bdfa3120f3e7ec7b434d90674b3396eccf88eb`; its official model card declares
Apache-2.0. The exact safetensors SHA256 and metadata git-object hashes are pinned
in `configs/perception/offline-teacher-v1.json`, and verified SHA256 values are
recorded in the local acquisition manifest. It remains a research-only teacher
candidate. Its predictions are pseudo-labels, not human truth or product approval.
See the [pinned publisher model card](https://huggingface.co/IDEA-Research/grounding-dino-base/blob/12bdfa3120f3e7ec7b434d90674b3396eccf88eb/README.md).

Upstream terms may change; pin the actual artifact and source revision. Dynamic
repository code execution and runtime downloads are forbidden. Do not load an
unverified executable checkpoint merely to obtain a convenient benchmark.
