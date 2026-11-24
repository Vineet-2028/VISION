# Third-party model and data BOM

## Task008 depth additions — 2026-10-18

Exact download revisions, URLs, sizes and SHA256 for weights, configuration,
processor and model cards are in `configs/depth-checkpoints.json`. Both downloaded
Small safetensors checkpoints are 99,173,660 bytes. No weights are committed.

| Candidate                              | Code / checkpoint source                                                                                                                                                                                             | License and lineage                                                                                                                                                                                                            | Decision                                                                                                                                          |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Depth Anything V2 Small relative       | [Official repository](https://github.com/DepthAnything/Depth-Anything-V2), [official converted checkpoint](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf)                                         | Repository and Small model explicitly Apache-2.0. Teacher/synthetic and pseudo-labeled real-image training lineage; individual training-image rights are not independently audited.                                            | Local research candidate, acquired and executed. No legal approval.                                                                               |
| Depth Anything V2 Small metric outdoor | [Metric implementation](https://github.com/DepthAnything/Depth-Anything-V2/tree/main/metric_depth), [official converted checkpoint](https://huggingface.co/depth-anything/Depth-Anything-V2-Metric-Outdoor-Small-hf) | Repository Small-model statement is permissive; converted metric card does not independently enumerate a license grant. Virtual KITTI fine-tuning is documented. Checkpoint-specific distribution/lineage review remains open. | Local metric research only; not deployment cleared.                                                                                               |
| Metric3Dv2 ViT-Small                   | [Official code and checkpoint links](https://github.com/YvanYin/Metric3D)                                                                                                                                            | BSD-2-Clause code; commercial inquiries directed to authors. Separate checkpoint grant not established in this review. Multi-dataset lineage requires artifact-level review.                                                   | Investigated, not acquired; SHA256 unavailable. Intrinsics/canonical-camera and heavier runtime integration deferred; no fabricated focal length. |
| FastDepth MobileNet baseline           | [Official repository](https://github.com/dwofk/fast-depth), [MIT license](https://github.com/dwofk/fast-depth/blob/master/LICENSE)                                                                                   | MIT code; separate historical weights grant not established. NYU indoor training context differs from outdoor walking.                                                                                                         | Investigated, not acquired; SHA256 unavailable. Legacy runtime/indoor-domain integration not selected for this bounded comparison.                |

Depth Anything Base/Large/Giant are non-commercial models according to the upstream
model statement; they are not selected as proprietary-product candidates. Existing
pinned Transformers/PyTorch/NumPy/Pillow runtimes are reused. No public depth dataset
was downloaded, and no user video was uploaded. This inventory is not legal advice
or a claim that model weights and training data have identical licenses.

Relative weight SHA256:
`3152477ce0d8d6978d76b995120de97cb5b928701fd0f817769f59e249a16b70`.
Metric outdoor weight SHA256:
`ad065c77a7421ca55159a1f0db9433397a607690f2d76bb8a6fc54b1be7a3124`.

The metric optical-axis-Z interpretation follows upstream
[point-cloud conversion](https://github.com/DepthAnything/Depth-Anything-V2/blob/main/metric_depth/depth_to_pointcloud.py).
Do not use that interpretation as evidence that Sentinel footage has accurate meters.

Engineering inventory, 2026-10-17. This is not legal approval. Weights and raw data
are not redistributed. Exact existing hashes are in `configs/detector-checkpoints.json`;
Task006C artifacts are listed below. A code repository license alone does not settle
checkpoint or training-image rights.

| Component                              | Source/version                                                                     | License identification                                        | Use and remaining review                                                                                        |
| -------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| YOLO26n/s, YOLO11n                     | Ultralytics assets v8.4.0, runtime8.4.177                                          | AGPL-3.0 / enterprise terms include models                    | RESEARCH_REFERENCE; no proprietary PRODUCT_CANDIDATE selection without an intentional compliance route          |
| RT-DETRv2-R18                          | PekingU checkpoint commit1a95089f34a94f1e9db917b053a06c00fdc1c08f                  | Apache-2.0 code/model card                                    | PRODUCT_CANDIDATE for research evaluation; product bundle/notice review remains                                 |
| YOLOX-Nano                             | Official Megvii release0.1.1rc0 ONNX download; current official demo preprocessing | Apache-2.0 repository; separate weight grant not established  | LICENSE_REVIEW_REQUIRED / WEIGHTS_LICENSE_REVIEW_REQUIRED; no known proprietary fee path required; COCO lineage |
| PicoDet-S416                           | Official PaddleDetection LCNet ONNX, release2.9 documentation                      | Apache-2.0 repository; separate weight grant not established  | LICENSE_REVIEW_REQUIRED / WEIGHTS_LICENSE_REVIEW_REQUIRED; COCO train2017 lineage; not legally cleared          |
| RTMDet-Tiny                            | Official MMDetection model zoo                                                     | Apache-2.0 repository; checkpoint-specific grant needs review | Integration assessed, no executed adapter/parity claim; native dependency compatibility unresolved              |
| Torch2.14.1 / torchvision0.29.1        | Optional pinned model environment                                                  | BSD-style upstream terms                                      | CPU research only; binary/transitive notices require release review                                             |
| Transformers4.57.6                     | Hugging Face                                                                       | Apache-2.0                                                    | Local-only RT-DETR loading                                                                                      |
| ONNX1.20.1 / ORT1.24.4                 | ONNX / Microsoft                                                                   | Apache-2.0 / MIT                                              | Static CPU FP32; GPU providers not qualified                                                                    |
| OpenCV5.0.0.93                         | opencv-python                                                                      | Apache-2.0 upstream; wheel third-party notices                | Model preprocessing only                                                                                        |
| PyAV18.1.0 / FFmpeg                    | PyAV wheel                                                                         | BSD PyAV; FFmpeg license depends on compiled components       | Video decode; inspect deployed build's codecs/notices before redistribution                                     |
| JPype1.7.1 / NumPy2.5.4 / Pillow12.3.0 | Pinned Python environment                                                          | Apache-2.0 / BSD / HPND-style upstream                        | Geometry bridge / arrays / local JPEG review export                                                             |
| COCO2017 diagnostic                    | 36 selected images,212 P0 objects                                                  | Annotation and per-image rights differ                        | Diagnostic only; source attribution retained; no raw redistribution                                             |
| SENTINEL_FIRST_PERSON_V1               | User-provided local recording; private inventory contains hash                     | USER_OWNED, LOCAL_R&D, user-declared                          | NOT_PLANNED redistribution; screen-recording origin/exposure uncertainty retained                               |
| UrbanEgo                               | DOI10.5281/zenodo.23062929 v1.0                                                    | RIGHTS_UNKNOWN_RESEARCH_SUPPLEMENT                            | No download or selection claim; optional multimodal pedestrian research only                                    |
| JRDB                                   | Optional future request                                                            | Publisher permission/restrictions apply                       | OPTIONAL_FUTURE_DATASET, not required; no request sent                                                          |
| CVAT / Label Studio                    | Optional, not installed                                                            | Edition/version terms require review                          | No mandatory service; local COCO import supported                                                               |

## Exact new artifacts

- YOLOX-Nano: [official artifact](https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_nano.onnx), 3,659,407 bytes, SHA256 `c789161ed43c8269fcd4e67c67eeeb4e80c622da2eb296a20bc6007bd18a0b7d`.
- PicoDet-S416: [official artifact](https://paddledet.bj.bcebos.com/deploy/third_engine/picodet_s_416_lcnet_postprocessed.onnx), 4,810,592 bytes, SHA256 `4b717e3f68f170fafd922c3c7978e52b6ad2ab3615d26b407e7d9aba44eb790f`.
- RTMDet-Tiny investigated [official checkpoint](https://download.openmmlab.com/mmdetection/v3.0/rtmdet/rtmdet_tiny_8xb32-300e_coco/rtmdet_tiny_8xb32-300e_coco_20220902_112414-78e30dcc.pth): not acquired; SHA256 unavailable. Do not infer an artifact hash from its filename suffix.

Primary sources: [YOLOX license](https://github.com/Megvii-BaseDetection/YOLOX/blob/main/LICENSE),
[YOLOX inference](https://github.com/Megvii-BaseDetection/YOLOX/tree/main/demo/ONNXRuntime),
[PaddleDetection license](https://github.com/PaddlePaddle/PaddleDetection/blob/release/2.9/LICENSE),
[PicoDet model zoo](https://github.com/PaddlePaddle/PaddleDetection/blob/release/2.9/configs/picodet/README_en.md),
[RTMDet model zoo](https://github.com/open-mmlab/mmdetection/tree/main/configs/rtmdet),
[RT-DETR card](https://huggingface.co/PekingU/rtdetr_v2_r18vd),
[UrbanEgo record](https://zenodo.org/records/23062929).

UrbanEgo is relevant because it combines first-person walking RGB, pose, IMU, GPS
and depth. Its retimed RGB video does not directly index metadata rows, and its YOLO
outputs are predictions, not reviewed ground truth. The public record did not expose
an explicit license in the inspected rights section. Commercial/redistribution
rights remain unknown; it is neither a dependency nor a product-selection dataset.

## Task009 classical motion

OpenCV Python wheel 5.0.0.93 (runtime reports 5.0.0) is now a direct pinned lab dependency for LK, DIS, Essential/Homography and research PnP. No learned-flow checkpoints were downloaded or added. Upstream code is Apache-2.0; deployed wheels retain third-party notices. Source: [OpenCV license](https://github.com/opencv/opencv/blob/5.x/LICENSE), [tracking API](https://docs.opencv.org/doc/doxygen/html/dc/d6b/group__video__track.html), [calibrated geometry API](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html).

Evaluation uses the existing user-owned local screen recording and hashed prototype review frames. No new external dataset, sensor stream or remote upload. Static/dynamic truth, pose truth and synchronized IMU are not established. No learned-flow weight rights are asserted.

## Task010 segmentation — local research only

Engineering inventory, 2026-10-21. Neither candidate is legally cleared for a proprietary product. Repository licenses do not automatically license weights or training data. No checkpoint redistribution is planned. No Cityscapes images were downloaded.

| Candidate  | Code / checkpoint source                                                                                                                                                                                   | Hash and lineage                                                                                                                                                                                  | Classification                                                                         |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| PIDNet-S   | [Official MIT repository](https://github.com/XuJiacong/PIDNet), its linked Google Drive Cityscapes folder; file ID `1wnMVQOmTEkSm8dB2A9TsSHG-yCgpGN0b` (`PIDNet_S_Cityscapes_val.pt`)                      | SHA256 `b51aa935bdb64a0779d776f38267fd49f7cce59413910abbbf0a74934b3d7c01`; ImageNet pretraining / Cityscapes segmentation lineage                                                                 | RESEARCH_REFERENCE; separate checkpoint grant and commercial-use rights require review |
| PP-LiteSeg | [PaddleSeg Apache-2.0 source](https://github.com/PaddlePaddle/PaddleSeg), [Rockchip export download script](https://github.com/airockchip/rknn_model_zoo/blob/main/examples/ppseg/model/download_model.sh) | ONNX SHA256 `ee29852c536d4cc13fa51d59201db310dc94140e72e96e12f07b36e37895da16`; Cityscapes 19-class export; exact upstream training checkpoint correspondence and exporter parity not established | RESEARCH_REFERENCE / LICENSE_REVIEW_REQUIRED; no inferred weight grant                 |

Cityscapes has [non-commercial dataset terms](https://www.cityscapes-dataset.com/license/). The implications for these derived checkpoints require release-specific review; do not treat local research execution as legal approval or product eligibility.

PIDNet inspected source hashes: `pidnet.py` = `1692ebc05ea4cc7096abd0b9a2e7e79543d878955af1a9d3d60e7973d6eb623d`; `model_utils.py` = `8817f6367b4c9d094b35cd606926f2937cef98469fff888e3773c1c95ca969aa`. The export tool verifies these before loading source, uses `torch.load(weights_only=True)`, requires every inference parameter, and excludes only auxiliary training heads/loss buffers. Local 512x256 ONNX SHA256 `2f0da8aec33e30c25299257a5b54243508528dda521c5c2614d6d250b4cb8205`; 768x384 SHA256 `7b4ab2d2d8c54baa0a4f6da7be153112ef5ecc6c4472993d9f7e62b2a6d246a7`. Both synthetic native/export class agreements were 1.0; this is not real-frame accuracy.

SegFormer is not installed or selected. The annotation editor is repository-owned plain HTML/JavaScript, with no external service or additional framework. Existing ONNX Runtime, PyAV, NumPy, OpenCV and optional Torch dependencies are reused. Review packets use existing user-declared local footage and retain private artifacts under ignored benchmark output.
