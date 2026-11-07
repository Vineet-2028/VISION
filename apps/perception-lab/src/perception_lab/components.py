"""Separate component extension points. No tensors or invented measurements yet."""

from typing import Protocol

from .contracts import ComponentProvenance, FrameIdentity
from .depth import DepthFrame
from .detection import DetectionBatch
from .flow import FlowObservation
from .preprocessing import PreparedImage
from .semantics import SemanticFrame

DetectionOutput = DetectionBatch


DepthOutput = DepthFrame


SegmentationOutput = SemanticFrame


OpticalFlowOutput = FlowObservation


class DetectorAdapter(Protocol):
    provenance: ComponentProvenance

    def detect(self, image: PreparedImage, identity: FrameIdentity) -> DetectionOutput | None: ...


class DepthAdapter(Protocol):
    provenance: ComponentProvenance

    def estimate_depth(
        self, image: PreparedImage, identity: FrameIdentity
    ) -> DepthOutput | None: ...


class SegmentationAdapter(Protocol):
    provenance: ComponentProvenance

    def segment(
        self, image: PreparedImage, identity: FrameIdentity
    ) -> SegmentationOutput | None: ...


class OpticalFlowAdapter(Protocol):
    provenance: ComponentProvenance

    def flow(self, image: PreparedImage, identity: FrameIdentity) -> OpticalFlowOutput | None: ...


class NoOpDetector:
    provenance = ComponentProvenance("NoOpDetector", "detector")

    def detect(self, image: PreparedImage, identity: FrameIdentity) -> DetectionOutput | None:
        return None


class NoOpDepthAdapter:
    provenance = ComponentProvenance("NoOpDepthAdapter", "depth")

    def estimate_depth(self, image: PreparedImage, identity: FrameIdentity) -> DepthOutput | None:
        return None


class NoOpSegmentationAdapter:
    provenance = ComponentProvenance("NoOpSegmentationAdapter", "segmentation")

    def segment(self, image: PreparedImage, identity: FrameIdentity) -> SegmentationOutput | None:
        return None


class NoOpOpticalFlowAdapter:
    provenance = ComponentProvenance("NoOpOpticalFlowAdapter", "optical_flow")

    def flow(self, image: PreparedImage, identity: FrameIdentity) -> OpticalFlowOutput | None:
        return None
