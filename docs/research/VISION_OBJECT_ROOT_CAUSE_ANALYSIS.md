# Physical-object root cause analysis — Alpha V1.1

2026-11-18. The user's original phone failure has no saved clip, gateway export,
or phone History. It cannot be reconstructed. No connected Android device was
listed by the repository SDK's `adb devices`. Physical testing is
**BLOCKED_NO_DEVICE**.

## Established engineering defect

`tools/import_field_case.py` previously selected only events whose publication
sequence equalled the selected capture. An asynchronous detector can publish a
result later while retaining the earlier source identity. The viewer therefore
could omit available evidence for that earlier capture.

The importer now retains up to 16 later publications whose detector session and
source sequence exactly match the capture, separately from current publication
events. It reports omissions and rejects a joined packet exceeding the viewer's
2 MB limit. It also enforces the two-second clip duration at import. The viewer
uses exact source identity for overlays, never the publication timestamp.

Regression coverage:
`tests/test_field_case_import.py`, `tests/test_field_case_ledger.py`, and
`tools/diagnostic-browser-qa.mjs`. These are synthetic correctness tests, **not**
evidence of an actual phone detection miss or improved recall.

## Causal evidence

`perception_lab/field_case_ledger.py` creates bounded JSON references for capture,
admission, orientation, detector source/post-vendor/filtering, association,
generation, semantics, world, corridor, interaction, risk, attention, intent,
gateway, phone receipt, TTS request and callbacks. References preserve original
entity/source identifiers, timestamps, reasons and provenance in the underlying
records. Each stage retains at most 16 references with an omission count.

Missing pre-NMS observations stay unavailable. A present stage or suppressed
attention decision is not proof that a physical target was detected, missed, or
incorrectly suppressed. `first_confirmed_failure_stage` remains UNKNOWN without
a justified reference-object correspondence. Ledger completeness is **PARTIAL**:
the schema is bounded, but it cannot supply missing observations or labels.

| Requested classification        | Current evidence                             |
| ------------------------------- | -------------------------------------------- |
| Detected and correctly silent   | Unmeasured on new physical cases             |
| Detected and incorrectly silent | Unmeasured                                   |
| Not detected                    | Unmeasured; absent pre-NMS data is not proof |
| Detected but misnamed           | Unmeasured                                   |
| Alert created but not heard     | No acoustic/device evidence                  |
| Unable to classify              | Original unrecorded incident                 |

New independently annotated field cases: **0**. Reviewer provenance, label
disagreements, relevant-object recall, false detections, missed important warnings,
and unnecessary interruptions: **not measured**, not zero. Required six cases
remain NOT_CAPTURED; this is different from NOT_OBSERVED after a physical test.

Retain PicoDet and the frozen comparator. No model swap, score relaxation,
teacher-generated ground truth, or new training is justified by this evidence.
Future measurement must use the same independently labeled scenes for both arms,
report numerator/denominator and uncertainty, and disclose any tuning overlap.
