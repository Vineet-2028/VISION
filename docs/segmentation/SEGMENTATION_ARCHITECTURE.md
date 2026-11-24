# Semantic evidence architecture

IMPLEMENTED: `SemanticSegmenter` accepts mapped RGB and a source `FrameIdentity`, returning immutable `SemanticFrame`. Synthetic and explicit PIDNet/PP-LiteSeg ONNX profiles feed the same `SurfaceEvidenceExtractor`. No vendor tensor escapes the runtime adapter. No detector, tracker, depth, flow or physical calibration is required to segment an image.

The original camera image remains authoritative. Masks retain their native grid plus the Guardian affine mapping, continuous-edge pixel convention, source clock, session and observation identity. Restoration samples the containing native label cell at each original pixel center. Crop exterior becomes UNKNOWN. Resizing integer labels never uses bilinear interpolation. PIDNet exports interpolate continuous logits before classification.

`FrameResult.segmentation` can describe an older source observation in REALTIME mode. Its nested identity is authoritative, not the enclosing publication frame. Only exact identities can join detections/tracks. Consumers must check status and age. Surface masks are original-camera uint8 flags; image boundaries can later use Guardian rays when measured calibration exists. No new spatial math is implemented here.

`SemanticFrame` records supported classes, mapping version and taxonomy. Unsupported stairs/curb classes are unavailable capabilities, not evidence that stairs/curbs are absent. Model scores are not calibrated probabilities; current profiles publish no score map.

PLANNED: Task011 consumes implementation-independent detections, tracks, depth observations, camera motion, track image motion, semantics and surfaces. Task012 may intersect surfaces with camera/depth/pose geometry. Neither task is implemented here.
