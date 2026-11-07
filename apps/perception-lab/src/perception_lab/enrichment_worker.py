"""Optional inference and surface extraction, isolated from the reasoning owner."""

from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter_ns

from .components import DepthOutput, OpticalFlowOutput, SegmentationOutput
from .contracts import FrameIdentity, LabError
from .latest_worker import LatestWorker
from .metrics import Distribution
from .preprocessing import PreparedImage
from .surfaces import SurfaceEvidenceExtractor, SurfaceEvidenceFrame

Enrichment = DepthOutput | OpticalFlowOutput | SegmentationOutput
Job = tuple[PreparedImage, FrameIdentity] | tuple[PreparedImage, FrameIdentity, int]


@dataclass(frozen=True)
class EnrichmentResult:
    observation: Enrichment | None
    surface: SurfaceEvidenceFrame | None = None


class EnrichmentWorker(LatestWorker[Job, EnrichmentResult]):
    def __init__(
        self,
        call: Callable[[PreparedImage, FrameIdentity], Enrichment | None],
        name: str,
    ) -> None:
        extractor = SurfaceEvidenceExtractor()
        self._input_age = Distribution(2048)
        self._output_age = Distribution(2048)

        def execute(job: Job) -> EnrichmentResult:
            image, identity = job[0], job[1]
            due = job[2] if len(job) == 3 else None
            if due is not None:
                with self._condition:
                    self._input_age.add(max(0, perf_counter_ns() - due))
            output = call(image, identity)
            valid = {
                "depth": isinstance(output, DepthOutput),
                "optical_flow": isinstance(output, OpticalFlowOutput),
                "segmentation": isinstance(output, SegmentationOutput),
            }[name]
            if output is not None and (not valid or output.identity != identity):
                raise LabError("ASYNC_COMPONENT_IDENTITY_OR_TYPE_MISMATCH")
            surface = extractor.extract(output) if isinstance(output, SegmentationOutput) else None
            if due is not None:
                with self._condition:
                    self._output_age.add(max(0, perf_counter_ns() - due))
            return EnrichmentResult(output, surface)

        super().__init__(execute, "sentinel-" + name)

    def timing(self) -> dict[str, object]:
        with self._condition:
            return {
                **super().timing(),
                "input_age": self._input_age.summary(),
                "output_age": self._output_age.summary(),
            }
