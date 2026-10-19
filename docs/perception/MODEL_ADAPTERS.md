# Component adapters

## IMPLEMENTED

DetectorAdapter.detect, DepthAdapter.estimate_depth, SegmentationAdapter.segment and
OpticalFlowAdapter.flow are separate protocols. Each takes a PreparedImage and
original FrameIdentity. PreparedImage carries descriptor plus exact core geometry
mapping. Descriptor declares width/height/channels/format/dtype/layout.
ComponentProvenance contains name, type, nullable model/version/runtime/config hash.
Each execution envelope records its original identity, processing start/end and status.

NoOpDetector, NoOpDepthAdapter, NoOpSegmentationAdapter and NoOpOpticalFlowAdapter
return None. They do not create a detection, depth sample, mask or motion vector.
FrameResult keeps unavailable outputs explicit. A mismatched component identity is
fatal. A deliberately recoverable component error is recorded while other components
continue. Unexpected exceptions are fatal and their raw strings never enter artifacts.

Adapters borrow read-only arrays for the duration of a call. Asynchronous execution
is not implemented. Task006 replaces the detector placeholder with validated
DetectionBatch values and optional local model adapters; see
[detector architecture](DETECTOR_ARCHITECTURE.md). Dense component outputs remain
minimal future contracts. Wrong component output types are now rejected explicitly.

## PLANNED / RESEARCH

Trackers, accelerated/mobile ONNX providers and typed dense outputs remain future
work. Task006 adds CPU ONNX research adapters and an explicit seed. Native model
resources are owned by a dedicated worker process; in-process model hot swapping
is not supported. No production detector is approved.
Risk and attention outputs do not belong in this application contract.
