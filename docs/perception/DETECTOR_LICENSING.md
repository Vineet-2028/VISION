# Detector licensing review

Official sources rechecked 2026-10-15. This is not legal advice and does not approve deployment.

| Candidate                 | Code / checkpoint source                                                                                                                                                                 | Terms and deployment implications                                                                                                                                                                                                                  |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| YOLO26n, YOLO26s, YOLO11n | [Ultralytics repository](https://github.com/ultralytics/ultralytics), official assets release v8.4.0                                                                                     | Ultralytics offers AGPL-3.0 and enterprise licensing. Its stated policy includes pretrained models. Closed/proprietary deployment requires legal review and potentially an enterprise agreement. Do not assume exporting ONNX removes obligations. |
| RT-DETRv2-R18             | [Official repository](https://github.com/lyuwenyu/RT-DETR), [PekingU converted checkpoint](https://huggingface.co/PekingU/rtdetr_v2_r18vd/tree/1a95089f34a94f1e9db917b053a06c00fdc1c08f) | Official code and converted model card identify Apache-2.0. Preserve license, applicable notices, attribution and modification notices when redistributing. Verify the exact checkpoint and bundled dependency terms before product distribution.  |

Primary terms: [Ultralytics licensing](https://www.ultralytics.com/license), [RT-DETR license](https://github.com/lyuwenyu/RT-DETR/blob/main/LICENSE). No enterprise license has been purchased and no candidate is marked legally approved.

Weights and media are not committed. Acquisition uses official HTTPS sources and records hashes. COCO annotations and individual images have separate terms: image metadata is retained, and only images marked Attribution or Attribution-ShareAlike are selected. Original Flickr attribution URLs are preserved. This metadata-based filter is not independent verification of ownership or permission. Review source attribution and ShareAlike obligations before redistributing media. [COCO terms](https://cocodataset.org/#termsofuse).

Runtime libraries and their transitive dependencies require an eventual SBOM/license review. Using the permissive RT-DETR architecture through another vendor's implementation can introduce different licensing terms; the adapter uses Transformers and PekingU weights, not Ultralytics RT-DETR.

## Task 006B use-status distinction

YOLO26n/YOLO26s/YOLO11n: **RESEARCH USE STATUS: REVIEW_REQUIRED**.
Research is not a blanket exemption from applicable terms. The publisher's current
licensing page also addresses private R&D. **PROPRIETARY DEPLOYMENT ACTION REQUIRED:**
document an applicable AGPL compliance route or obtain appropriate enterprise terms
and review the actual distribution. No enterprise agreement is recorded here.
The status is REVIEW_REQUIRED rather than an invented legal approval or categorical
legal prohibition. Exporting the same model does not establish a new license.

RT-DETR: official repository LICENSE and the PekingU checkpoint card identify
Apache-2.0. **RESEARCH USE STATUS: CLEAR for the stated upstream license identification;
product bundle review remains REVIEW_REQUIRED.** Preserve applicable notices and
review transitive dependencies and the exact artifact before deployment. This is
informational source identification, not legal advice or approval of the whole product.
