"""Single-owner replay engine. Source and processing clocks are never subtracted."""

import time
from collections.abc import Callable, Iterator
from dataclasses import replace
from typing import Any

from .alerts import AlertEngine
from .attention import NoveltyEscalationAttentionPolicy
from .attention_types import AttentionEngine
from .camera_view_quality import CameraViewQuality, CameraViewQualityEstimator, ViewQualityConfig
from .clocks import processing_ns
from .components import (
    DepthAdapter,
    DepthOutput,
    DetectionOutput,
    DetectorAdapter,
    NoOpDepthAdapter,
    NoOpDetector,
    NoOpOpticalFlowAdapter,
    NoOpSegmentationAdapter,
    OpticalFlowAdapter,
    OpticalFlowOutput,
    SegmentationAdapter,
    SegmentationOutput,
)
from .config import LabConfig
from .contracts import (
    Cancellation,
    ComponentExecution,
    DropReason,
    Event,
    FailureSeverity,
    Frame,
    FrameIdentity,
    FrameResult,
    FrameTimingTrace,
    LabError,
    Listener,
    SourceIssue,
    TimingProvenance,
)
from .corridor import HybridCorridorAnalyzer
from .corridor_types import CorridorAnalyzer
from .depth_sampling import detection_depth, track_depth
from .ego_runtime import VisualEgoEstimator
from .enrichment_worker import EnrichmentWorker
from .entity_attention import attach_entity_semantics
from .entity_enrichment import (
    EntitySemanticWorker,
    SemanticEnricher,
    SemanticEnrichmentRequest,
    SemanticTrigger,
)
from .event_lineage import attach_event_lineage
from .flow import DenseFlowField
from .flow_runtime import FlowAdapter
from .geometry import CoreGeometry
from .interaction import TrajectoryCorridorInteractionAnalyzer
from .interaction_types import InteractionAnalyzer
from .latest_source import LatestSource
from .metrics import Distribution, Metrics
from .motion import TrackImageMotionObservation, sample_tracks
from .motion_geometry import calibration_hash, compensate
from .motion_masking import dynamic_exclusions
from .preprocessing import ImagePreprocessor
from .recording import SessionRecorder
from .risk import RuleBasedRiskEngine
from .risk_types import RiskEngine
from .scheduling import FixedRateScheduler, FrameQueue, QueuedFrame
from .semantic_worker import SemanticWorker
from .semantics import ObservationStatus
from .sources import FrameSource
from .surfaces import SurfaceEvidenceExtractor
from .tracking import AssociationTracker
from .tracking_types import DetectorEvidence, MultiObjectTracker, TrackId
from .trajectory import AdaptiveKinematicPredictor
from .trajectory_types import TrajectoryPredictor
from .user_heading import UserMotionHeadingEstimator
from .visualization import Renderer
from .world_model import PrototypeWorldModel
from .world_types import EvidenceStatus, WorldEntityId, WorldModel, WorldSceneQuality


class Pipeline:
    def __init__(
        self,
        config: LabConfig,
        preprocessor: ImagePreprocessor,
        recorder: SessionRecorder,
        listener: Listener | None = None,
        clock: Callable[[], int] = processing_ns,
        sleep: Callable[[float], None] = time.sleep,
        detector: DetectorAdapter | None = None,
        depth: DepthAdapter | None = None,
        segmentation: SegmentationAdapter | None = None,
        flow: OpticalFlowAdapter | None = None,
        renderer: Renderer | None = None,
        tracker: MultiObjectTracker | None = None,
        motion_geometry: "CoreGeometry | None" = None,
        world_model: WorldModel | None = None,
        corridor_analyzer: CorridorAnalyzer | None = None,
        trajectory_predictor: TrajectoryPredictor | None = None,
        interaction_analyzer: InteractionAnalyzer | None = None,
        risk_engine: RiskEngine | None = None,
        attention_engine: AttentionEngine | None = None,
        alert_engine: AlertEngine | None = None,
        semantic_enricher: SemanticEnricher | None = None,
    ) -> None:
        self.config, self.preprocessor, self.recorder = config, preprocessor, recorder
        self.listener, self.clock, self.sleep = listener, clock, sleep
        self.view_estimator = (
            CameraViewQualityEstimator(ViewQualityConfig()) if config.camera_view_health else None
        )
        self.view_health_timing = Distribution(2048)
        self.heading_estimator = UserMotionHeadingEstimator()
        self.queue = FrameQueue(config.queue_capacity, config.drop_policy)
        self.metrics = Metrics(config.metrics_window)
        self.scheduler = FixedRateScheduler({str(k): v for k, v in config.intervals_ns.items()})
        self.detector = detector or NoOpDetector()
        self.depth = depth or NoOpDepthAdapter()
        self.segmentation = segmentation or NoOpSegmentationAdapter()
        self.semantic_worker = (
            SemanticWorker(self.segmentation)
            if segmentation is not None and config.mode == "REALTIME" and not config.realtime_rescue
            else None
        )
        self.surface_extractor = SurfaceEvidenceExtractor()
        self.flow = flow or NoOpOpticalFlowAdapter()
        self.motion_geometry = motion_geometry
        self.ego = None
        if config.motion is not None:
            if motion_geometry is None:
                raise ValueError("Motion requires explicit calibrated geometry")
            self.flow = flow or FlowAdapter(
                config.motion, recorder.session_id, calibration_hash(motion_geometry)
            )
            if config.motion.estimator == "visual":
                self.ego = VisualEgoEstimator(motion_geometry, config.motion)
        self._last_observation = -1
        self.enrichment_workers: dict[str, EnrichmentWorker] = {}
        self.enrichment_rejections: dict[str, int] = {}
        self.enrichment_timing: dict[str, Distribution] = {}
        if config.realtime_rescue:
            for name, enabled, call in (
                ("depth", config.depth is not None, self.depth.estimate_depth),
                ("segmentation", config.segmentation is not None, self.segmentation.segment),
                ("optical_flow", config.motion is not None, self.flow.flow),
            ):
                if enabled:
                    self.enrichment_workers[name] = EnrichmentWorker(call, name)
        self._last_sequence = -1
        self._source_id: str | None = None
        self._has_run = False
        self.renderer = renderer
        self._started_ns = 0
        self._cancel = Cancellation()
        self._active_frame: Frame | None = None
        self._active_accounted = False
        self._reading_frame: Frame | None = None
        self._failure_stage = "SOURCE"
        self.tracker = tracker
        if tracker is not None and config.tracker is None:
            raise ValueError("Injected tracker requires explicit tracking configuration")
        self._tracking_dimensions: tuple[int, int] | None = None
        self._tracking_identity: FrameIdentity | None = None
        self._tracking_ids: tuple[TrackId, ...] = ()
        self._tracking_peaks = {
            "active": 0,
            "lost": 0,
            "history_entries": 0,
            "max_serial": 0,
            "gap_resets": 0,
        }
        self._motion_counts: dict[str, int] = {}
        self._flow_pairs_computed = 0
        self._flow_pairs_published = 0
        self._semantic_published = 0
        if world_model is not None and config.world_model is None:
            raise ValueError("Injected world model requires explicit configuration")
        self.world_model = world_model or (
            PrototypeWorldModel(
                config.world_model, recorder.session_id, config.source_id, motion_geometry
            )
            if config.world_model is not None
            else None
        )
        self._world_published = 0
        if corridor_analyzer is not None and config.corridor is None:
            raise ValueError("Injected corridor analyzer requires explicit configuration")
        self.corridor_analyzer = corridor_analyzer or (
            HybridCorridorAnalyzer(config.corridor, motion_geometry) if config.corridor else None
        )
        self._corridor_published = 0
        if trajectory_predictor is not None and config.trajectory is None:
            raise ValueError("Injected trajectory predictor requires explicit configuration")
        self.trajectory_predictor = trajectory_predictor or (
            AdaptiveKinematicPredictor(config.trajectory, motion_geometry)
            if config.trajectory
            else None
        )
        self._trajectory_published = 0
        if interaction_analyzer is not None and config.interaction is None:
            raise ValueError("Injected interaction analyzer requires explicit configuration")
        self.interaction_analyzer = interaction_analyzer or (
            TrajectoryCorridorInteractionAnalyzer(config.interaction, motion_geometry)
            if config.interaction
            else None
        )
        self._interaction_published = 0
        if risk_engine is not None and config.risk is None:
            raise ValueError("Injected risk engine requires explicit configuration")
        self.risk_engine = risk_engine or (
            RuleBasedRiskEngine(config.risk) if config.risk else None
        )
        self._risk_published = 0
        if attention_engine is not None and config.attention is None:
            raise ValueError("Injected attention engine requires explicit configuration")
        self.attention_engine = attention_engine or (
            NoveltyEscalationAttentionPolicy(config.attention) if config.attention else None
        )
        self._attention_published = 0
        if alert_engine is not None and config.alerts is None:
            raise ValueError("Injected alerts require explicit configuration")
        self.alert_engine = alert_engine or (AlertEngine(config.alerts) if config.alerts else None)
        if semantic_enricher is not None and self.world_model is None:
            raise ValueError("Entity enrichment requires a world model")
        self.entity_semantic_worker = (
            EntitySemanticWorker(semantic_enricher) if semantic_enricher else None
        )
        self._entity_semantic_submitted: dict[WorldEntityId, int] = {}
        self._entity_semantic_applied = 0

    def emit(self, event: Event) -> None:
        self.recorder.write_event(event)
        if self.listener is not None:
            self.listener(event)

    def drop(self, frame: Frame | SourceIssue, reason: DropReason) -> None:
        if frame is self._active_frame:
            self._active_accounted = True
        if frame is self._reading_frame:
            self._reading_frame = None
        self.metrics.counts["dropped"] += 1
        self.metrics.drops[reason.value] = self.metrics.drops.get(reason.value, 0) + 1
        self.emit(
            Event(
                "FrameDropped",
                frame.identity if isinstance(frame, Frame) else None,
                reason,
                sequence=frame.identity.sequence if isinstance(frame, Frame) else frame.sequence,
            )
        )

    def read(self, iterator: Iterator[Frame | SourceIssue], cancel: Cancellation) -> Frame | None:
        while not cancel.requested:
            item = next(iterator, None)
            if item is None:
                return None
            self.metrics.counts["source"] += 1
            if isinstance(item, SourceIssue):
                self.metrics.counts["failed"] += 1
                self.drop(item, item.reason)
                continue
            identity = item.identity
            self._reading_frame = item
            self.metrics.counts["decoded"] += 1
            self.metrics.stages["decode"].add(item.decode_completed_ns - item.decode_started_ns)
            self.metrics.stages["conversion"].add(item.conversion_ns)
            self.emit(Event("FrameDecoded", identity))
            if self._source_id is None:
                self._source_id = self.config.source_id
            if self._source_id != identity.source_id or identity.sequence <= self._last_sequence:
                raise LabError("SOURCE_IDENTITY_DISCONTINUITY")
            self._last_sequence = identity.sequence
            if (
                identity.observation_ns <= self._last_observation
                or identity.timing == TimingProvenance.UNKNOWN
            ):
                self.drop(item, DropReason.INVALID_TIMESTAMP)
                continue
            self._last_observation = identity.observation_ns
            self.metrics.observe(identity.observation_ns)
            if identity.observation_ns < self.config.start_ns:
                self.drop(item, DropReason.USER_SKIP)
                continue
            if self.config.end_ns is not None and identity.observation_ns >= self.config.end_ns:
                self.drop(item, DropReason.USER_SKIP)
                return None
            self._reading_frame = None
            return item
        return None

    def accept(self, frame: Frame, due_ns: int) -> None:
        dropped = self.queue.offer(QueuedFrame(frame, self.clock(), due_ns))
        self.metrics.counts["accepted"] += 1
        if dropped is not None:
            self.drop(dropped.frame, DropReason.QUEUE_OVERFLOW)
        self.emit(Event("FrameAccepted", frame.identity))

    def abandon(self, item: QueuedFrame) -> bool:
        if self._cancel.requested:
            self.drop(item.frame, DropReason.USER_SKIP)
            return True
        if self.config.mode == "REALTIME":
            assert self.config.max_staleness_ns is not None
            if self.clock() - item.due_ns > self.config.max_staleness_ns:
                self.drop(item.frame, DropReason.REALTIME_STALENESS)
                return True
        return False

    def _publish_unusable_view(
        self, item: QueuedFrame, view: CameraViewQuality, started: int
    ) -> None:
        """Publish unavailability, never a fresh empty scene or confident alert."""
        frame, completed = item.frame, self.clock()
        if self.abandon(item):
            return
        if self.alert_engine is not None:
            self.alert_engine.reset()
        if self.attention_engine is not None:
            self.attention_engine.reset()
        result = FrameResult(
            frame.identity,
            frame.width,
            frame.height,
            frame.pixel_format,
            FrameTimingTrace(
                frame.decode_started_ns,
                frame.decode_completed_ns,
                item.accepted_ns,
                started,
                completed,
                completed,
                completed,
                completed,
            ),
            (),
            warnings=("CAMERA_VIEW_NOT_USABLE", *view.reasons),
            camera_view_quality=view,
            camera_orientation=frame.camera_orientation,
            scene_capability="CAMERA_UNUSABLE"
            if view.status.value == "UNUSABLE"
            else "PERCEPTION_UNAVAILABLE",
        )
        if self.world_model is not None:
            state = self.world_model.consume(result)
            state = replace(
                state,
                scene_quality=WorldSceneQuality(
                    "UNAVAILABLE", ("CAMERA_VIEW_NOT_USABLE", *view.reasons)
                ),
                capabilities=tuple(
                    replace(
                        c,
                        status=EvidenceStatus.UNAVAILABLE,
                        reasons=(*c.reasons, "CAMERA_VIEW_NOT_USABLE"),
                    )
                    for c in state.capabilities
                ),
                diagnostics=(*state.diagnostics, "CAMERA_VIEW_NOT_USABLE"),
            )
            result = replace(result, world_state=state)
            self._world_published += 1
        self.recorder.write_result(result)
        if self.config.mode == "REALTIME":
            self.metrics.stages["realtime_result_age"].add(self.clock() - item.due_ns)
        self.metrics.counts["processed"] += 1
        self._active_accounted = True
        self.emit(Event("FrameCompleted", frame.identity))

    def process(self, item: QueuedFrame) -> None:
        frame = item.frame
        self._active_frame = frame
        self._active_accounted = False
        started = self.clock()
        self.metrics.stages["queue"].add(started - item.accepted_ns)
        if self.abandon(item):
            return
        view = None
        if self.view_estimator is not None:
            view_started = self.clock()
            view = self.view_estimator.estimate(frame)
            self.view_health_timing.add(self.clock() - view_started)
            if not view.permits_scene_reasoning:
                self._publish_unusable_view(item, view, started)
                return
        self._failure_stage = "PREPROCESS"
        prepared = self.preprocessor.prepare(frame)
        prepared_at = self.clock()
        self.metrics.stages["preprocess"].add(prepared_at - started)
        if self.abandon(item):
            return
        self._failure_stage = "SCHEDULER"
        eligible = self.scheduler.eligible(frame.identity.observation_ns)
        scheduled_at = self.clock()
        self.metrics.stages["scheduler"].add(scheduled_at - prepared_at)
        executions = []
        errors = []
        outputs: dict[
            str, DetectionOutput | DepthOutput | SegmentationOutput | OpticalFlowOutput
        ] = {}
        calls = {
            "detector": (self.detector.provenance, self.detector.detect),
            "depth": (self.depth.provenance, self.depth.estimate_depth),
            "segmentation": (self.segmentation.provenance, self.segmentation.segment),
            "optical_flow": (self.flow.provenance, self.flow.flow),
        }
        async_surface = None
        if self.semantic_worker is not None:
            try:
                ready = self.semantic_worker.poll()
            except LabError as error:
                if error.severity == FailureSeverity.FATAL:
                    raise
                ready = None
                errors.append("segmentation:COMPONENT_RECOVERABLE")
            if ready is not None:
                if (
                    ready.session_id != self.recorder.session_id
                    or ready.identity.source_id != frame.identity.source_id
                    or ready.identity.timing != frame.identity.timing
                    or ready.identity.observation_ns > frame.identity.observation_ns
                    or ready.identity.sequence > frame.identity.sequence
                ):
                    raise LabError("SEMANTIC_ASYNC_IDENTITY_MISMATCH")
                maximum_age = (
                    self.config.segmentation.max_age_ns
                    if self.config.segmentation
                    else 1_000_000_000
                )
                if (
                    frame.identity.observation_ns - ready.observed_identity.observation_ns
                    > maximum_age
                ):
                    ready = replace(ready, status=ObservationStatus.STALE)
                # Preserve the older observation identity. No same-frame fusion below.
                outputs["segmentation"] = ready
        # Start independent enrichment before synchronous detector work. Sharing
        # immutable prepared input does not require waiting for detector output.
        for name in eligible:
            if name in self.enrichment_workers:
                self._failure_stage = "COMPONENT_" + name.upper()
                self.enrichment_workers[name].submit((prepared, frame.identity, item.due_ns))
        for name in sorted(eligible, key=lambda value: value == "segmentation"):
            self._failure_stage = "COMPONENT_" + name.upper()
            provenance, call = calls[name]
            if name in self.enrichment_workers:
                continue
            if name == "segmentation" and self.semantic_worker is not None:
                self.semantic_worker.submit(prepared, frame.identity)
                continue
            self.emit(Event("ComponentStarted", frame.identity, component=name))
            if self.abandon(item):
                return
            component_start = self.clock()
            status = "NO_OUTPUT"
            try:
                output = call(prepared, frame.identity)
                if output is not None:
                    valid_output_type = {
                        "detector": isinstance(output, DetectionOutput),
                        "depth": isinstance(output, DepthOutput),
                        "segmentation": isinstance(output, SegmentationOutput),
                        "optical_flow": isinstance(output, OpticalFlowOutput),
                    }[name]
                    if not valid_output_type:
                        raise LabError("COMPONENT_OUTPUT_TYPE_MISMATCH")
                    if output.identity != frame.identity:
                        raise LabError("COMPONENT_IDENTITY_MISMATCH")
                    if isinstance(output, SegmentationOutput):
                        if output.session_id != self.recorder.session_id:
                            raise LabError("SEMANTIC_SESSION_MISMATCH")
                    if isinstance(output, OpticalFlowOutput):
                        if output.pair.session_id != self.recorder.session_id:
                            raise LabError("FLOW_SESSION_MISMATCH")
                        self._flow_pairs_computed += 1
                    outputs[name] = output
                    status = (
                        "SUCCESS_EMPTY"
                        if isinstance(output, DetectionOutput) and not output.detections
                        else "OUTPUT"
                    )
            except LabError as error:
                if error.severity == FailureSeverity.FATAL:
                    raise
                status = "RECOVERABLE_FAILURE"
                errors.append(name + ":COMPONENT_RECOVERABLE")
            end = self.clock()
            self.metrics.stages["component"].add(end - component_start)
            if name == "depth":
                self.metrics.stages["depth"].add(end - component_start)
            if name == "segmentation":
                self.metrics.stages["segmentation"].add(end - component_start)
            if name == "optical_flow":
                self.metrics.stages["optical_flow"].add(end - component_start)
            executions.append(
                ComponentExecution(
                    frame.identity,
                    provenance,
                    component_start,
                    end,
                    status,
                    max(0, end - component_start - self.scheduler.intervals[name]),
                )
            )
            self.emit(Event("ComponentCompleted", frame.identity, component=name))
        # Consume the newest completed enrichment after detector work, without waiting.
        for name, worker in self.enrichment_workers.items():
            self._failure_stage = "ASYNC_COMPONENT_" + name.upper()
            completion = worker.poll()
            if completion is None:
                continue
            enrichment_ready = completion.output.observation
            if enrichment_ready is None:
                continue
            identity = enrichment_ready.identity
            if (
                identity.source_id != frame.identity.source_id
                or identity.timing != frame.identity.timing
                or identity.sequence > frame.identity.sequence
                or identity.observation_ns > frame.identity.observation_ns
            ):
                raise LabError("ASYNC_COMPONENT_SOURCE_MISMATCH")
            source_due = item.due_ns + identity.observation_ns - frame.identity.observation_ns
            for stage, timestamp in (
                ("input_age", completion.started_ns),
                ("output_age", completion.completed_ns),
                ("polled_age", self.clock()),
            ):
                self.enrichment_timing.setdefault(
                    name + "_" + stage, Distribution(self.config.metrics_window)
                ).add(max(0, timestamp - source_due))
            if isinstance(enrichment_ready, SegmentationOutput):
                if enrichment_ready.session_id != self.recorder.session_id:
                    raise LabError("SEMANTIC_SESSION_MISMATCH")
                age = max(0, self.clock() - item.due_ns) + (
                    frame.identity.observation_ns
                    - enrichment_ready.observed_identity.observation_ns
                )
                assert self.config.segmentation is not None
                if age <= self.config.segmentation.max_age_ns:
                    outputs[name] = enrichment_ready
                    async_surface = completion.output.surface
                    continue
            elif max(0, self.clock() - source_due) <= (
                self.config.world_model.late_ns if self.config.world_model else 1_000_000_000
            ):
                if isinstance(enrichment_ready, OpticalFlowOutput):
                    if enrichment_ready.pair.session_id != self.recorder.session_id:
                        raise LabError("FLOW_SESSION_MISMATCH")
                    self._flow_pairs_computed += 1
                outputs[name] = enrichment_ready
                continue
            # Rejected observations never become fresh by changing their identity.
            self.enrichment_rejections[name] = self.enrichment_rejections.get(name, 0) + 1
        if self.abandon(item):
            return
        self._failure_stage = "POSTPROCESS"
        components_at = self.clock()
        completed = self.clock()
        trace = FrameTimingTrace(
            frame.decode_started_ns,
            frame.decode_completed_ns,
            item.accepted_ns,
            started,
            prepared_at,
            scheduled_at,
            components_at,
            completed,
        )
        detector_output = outputs.get("detector")
        depth_output = outputs.get("depth")
        segmentation_output = outputs.get("segmentation")
        flow_output = outputs.get("optical_flow")
        tracks = None
        if self.config.tracker is not None or self.tracker is not None:
            self._failure_stage = "TRACKING"
            dimensions = (frame.width, frame.height)
            if self._tracking_dimensions is None:
                self._tracking_dimensions = dimensions
                if self.tracker is None:
                    assert self.config.tracker is not None
                    self.tracker = AssociationTracker(
                        self.config.tracker,
                        self.recorder.session_id,
                        frame.identity.source_id,
                        *dimensions,
                        objectness_first=self.config.entity_semantics_ontology is not None,
                    )
            if dimensions != self._tracking_dimensions:
                raise LabError("TRACKING_IMAGE_IDENTITY_CHANGED")
            assert self.tracker is not None
            evidence = DetectorEvidence.NO_DETECTOR_RUN
            failure_code = None
            if "detector" in eligible:
                evidence = DetectorEvidence.UNAVAILABLE
                if isinstance(detector_output, DetectionOutput):
                    evidence = (
                        DetectorEvidence.SUCCESS
                        if detector_output.detections
                        else DetectorEvidence.SUCCESS_EMPTY
                    )
                elif any(
                    e.provenance.component_type == "detector" and e.status == "RECOVERABLE_FAILURE"
                    for e in executions
                ):
                    evidence, failure_code = DetectorEvidence.FAILURE, "INFERENCE_FAILURE"
            tracking_started = self.clock()
            previous = self._tracking_identity
            reset_ids: tuple[TrackId, ...] = ()
            gap_reset = (
                previous is not None
                and self.config.tracker is not None
                and frame.identity.source_id == previous.source_id
                and frame.identity.timing == previous.timing
                and frame.identity.sequence > previous.sequence
                and frame.identity.observation_ns - previous.observation_ns
                > self.config.tracker.max_step_ns
            )
            if gap_reset:
                reset_ids = self._tracking_ids
                self.tracker.reset(self.recorder.session_id, frame.identity.source_id, *dimensions)
                self._tracking_peaks["gap_resets"] += 1
                self.emit(Event("TrackingGapReset", frame.identity))
            tracks = self.tracker.update(
                self.recorder.session_id,
                frame.identity,
                evidence,
                detector_output if isinstance(detector_output, DetectionOutput) else None,
                failure_code,
            )
            if gap_reset:
                tracks = replace(
                    tracks,
                    removed=reset_ids + tracks.removed,
                    diagnostics=tracks.diagnostics + ("FORWARD_GAP_RESET",),
                )
            self._tracking_identity = frame.identity
            self._tracking_ids = tuple(t.track_id for t in tracks.tracks)
            self.metrics.stages["tracking"].add(self.clock() - tracking_started)
            self._tracking_peaks["active"] = max(self._tracking_peaks["active"], len(tracks.tracks))
            self._tracking_peaks["lost"] = max(
                self._tracking_peaks["lost"], sum(t.lifecycle == "LOST" for t in tracks.tracks)
            )
            self._tracking_peaks["history_entries"] = max(
                self._tracking_peaks["history_entries"], sum(len(t.history) for t in tracks.tracks)
            )
            self._tracking_peaks["max_serial"] = max(
                self._tracking_peaks["max_serial"],
                max((t.track_id.serial for t in tracks.tracks), default=0),
            )
            if self.abandon(item):
                return
        published_detector = detector_output
        if isinstance(detector_output, DetectionOutput) and self.config.tracker is not None:
            published_detector = replace(
                detector_output,
                detections=tuple(
                    d
                    for d in detector_output.detections
                    if d.confidence >= self.config.tracker.publication_threshold
                ),
            )
        sampling_started = self.clock()
        if self.config.realtime_rescue:
            # Recheck after detector/tracker compute: an observation that was valid
            # when polled may expire while the fast path is doing useful work.
            for name, optional in (
                ("depth", depth_output),
                ("optical_flow", flow_output),
                ("segmentation", segmentation_output),
            ):
                if optional is None:
                    continue
                observed = (
                    optional.observed_identity
                    if isinstance(optional, SegmentationOutput)
                    else optional.identity
                )
                age = max(0, self.clock() - item.due_ns) + (
                    frame.identity.observation_ns - observed.observation_ns
                )
                limit = (
                    self.config.segmentation.max_age_ns
                    if name == "segmentation" and self.config.segmentation is not None
                    else self.config.world_model.late_ns
                    if self.config.world_model is not None
                    else 1_000_000_000
                )
                if age > limit:
                    self.enrichment_rejections[name] = self.enrichment_rejections.get(name, 0) + 1
                    if name == "depth":
                        depth_output = None
                    elif name == "optical_flow":
                        flow_output = None
                    else:
                        segmentation_output, async_surface = None, None
        motion = None
        track_motion: tuple[TrackImageMotionObservation, ...] = ()
        if flow_output is not None and self.ego is not None:
            assert self.motion_geometry is not None and self.config.motion is not None
            assert isinstance(flow_output, OpticalFlowOutput)
            sparse = (
                flow_output.sparse(self.config.motion.max_features)
                if isinstance(flow_output, DenseFlowField)
                else flow_output
            )
            if sparse.pair.session_id != self.recorder.session_id:
                raise ValueError("Flow session mismatch")
            excluded = (
                dynamic_exclusions(
                    sparse,
                    published_detector if isinstance(published_detector, DetectionOutput) else None,
                    tracks,
                )
                if self.config.motion.dynamic_masking and sparse.identity == frame.identity
                else None
            )
            motion_started = self.clock()
            motion = self.ego.estimate(sparse, excluded)
            self.metrics.stages["ego_motion"].add(self.clock() - motion_started)
            reason = motion.quality.reason
            self._motion_counts[reason] = self._motion_counts.get(reason, 0) + 1
            compensation_started = self.clock()
            residual = compensate(self.motion_geometry, sparse, motion)
            self.metrics.stages["motion_compensation"].add(self.clock() - compensation_started)
            if residual is not None and tracks is not None and sparse.identity == frame.identity:
                track_sample_started = self.clock()
                track_motion = sample_tracks(tracks, residual)
                self.metrics.stages["motion_track_sampling"].add(
                    self.clock() - track_sample_started
                )
        surface = async_surface
        if isinstance(segmentation_output, SegmentationOutput):
            if (
                segmentation_output.mapping.camera_dimensions != prepared.mapping.camera_dimensions
                or segmentation_output.mapping.camera_image_id != prepared.mapping.camera_image_id
            ):
                raise LabError("SEMANTIC_CAMERA_IMAGE_MISMATCH")
            surface_start = self.clock()
            exact = segmentation_output.identity == frame.identity
            surface = async_surface or self.surface_extractor.extract(
                segmentation_output,
                detector_output if exact and isinstance(detector_output, DetectionOutput) else None,
                tracks if exact else None,
            )
            self.metrics.stages["surface_extraction"].add(self.clock() - surface_start)
            self.metrics.stages["semantic_observation_age"].add(
                frame.identity.observation_ns - segmentation_output.observed_identity.observation_ns
            )
        result = FrameResult(
            frame.identity,
            frame.width,
            frame.height,
            frame.pixel_format,
            trace,
            tuple(executions),
            camera_view_quality=view,
            camera_orientation=frame.camera_orientation,
            scene_capability="DEGRADED" if view is not None else "NOT_EVALUATED",
            detector=published_detector
            if isinstance(published_detector, DetectionOutput)
            else None,
            depth=depth_output if isinstance(depth_output, DepthOutput) else None,
            detection_depths=detection_depth(published_detector, depth_output)
            if isinstance(published_detector, DetectionOutput)
            and isinstance(depth_output, DepthOutput)
            and depth_output.identity == published_detector.identity
            else (),
            track_depths=track_depth(
                tracks,
                depth_output
                if isinstance(depth_output, DepthOutput)
                and depth_output.identity == tracks.identity
                else None,
            )
            if tracks is not None
            else (),
            segmentation=segmentation_output
            if isinstance(segmentation_output, SegmentationOutput)
            else None,
            optical_flow=flow_output if isinstance(flow_output, OpticalFlowOutput) else None,
            errors=tuple(errors),
            tracks=tracks,
            camera_motion=motion,
            user_motion_heading=self.heading_estimator.estimate(
                motion,
                frame.identity,
                self.motion_geometry.c.camera_frame_id if self.motion_geometry else "UNAVAILABLE",
            ),
            track_image_motion=track_motion,
            surfaces=surface,
            warnings=()
            if frame.identity.timing == TimingProvenance.AUTHORITATIVE_PTS
            else ("DEGRADED_SOURCE_TIMING",),
        )
        if self.world_model is not None:
            world_started = self.clock()
            result = replace(result, world_state=self.world_model.consume(result))
            self.metrics.stages["world_model"].add(self.clock() - world_started)
            self._world_published += 1
        if (
            self.entity_semantic_worker is not None
            and self.world_model is not None
            and result.world_state is not None
        ):
            state = result.world_state
            entity_ready = self.entity_semantic_worker.poll(state)
            if entity_ready is not None and self.world_model.ingest_entity_semantics(
                entity_ready.entity_id,
                entity_ready.track_id,
                entity_ready.observation,
                state.state_timestamp,
            ):
                self._entity_semantic_applied += 1
                state = replace(
                    self.world_model.snapshot(state.state_timestamp),
                    user_motion_heading=state.user_motion_heading,
                )
                result = replace(result, world_state=state)
            active_ids = {e.entity_id for e in state.entities}
            self._entity_semantic_submitted = {
                key: value
                for key, value in self._entity_semantic_submitted.items()
                if key in active_ids
            }
            candidates = [
                e
                for e in state.entities
                if e.entity_observation is not None
                and e.entity_observation.source_frame == frame.identity
                and e.lifecycle.value != "LOST"
                and frame.identity.observation_ns
                - self._entity_semantic_submitted.get(e.entity_id, -200_000_000)
                >= 200_000_000
            ]
            if self.entity_semantic_worker.provider_failed:
                result = replace(
                    result, warnings=(*result.warnings, "ENTITY_SEMANTIC_PROVIDER_UNAVAILABLE")
                )
            if candidates and not self.entity_semantic_worker.provider_failed:
                entity = min(
                    candidates,
                    key=lambda e: (
                        self._entity_semantic_submitted.get(e.entity_id, -1),
                        e.entity_id,
                    ),
                )
                entity_observation = entity.entity_observation
                assert entity_observation is not None
                trigger: SemanticTrigger = (
                    "NEW_TRACK"
                    if entity.entity_id not in self._entity_semantic_submitted
                    else "UNKNOWN_TRACK"
                    if entity.track_semantics is None
                    or entity.track_semantics.selected_concept is None
                    else "UNSTABLE_SEMANTICS"
                    if entity.track_semantics.quality != "STABLE"
                    else "PERIODIC_REFRESH"
                )
                self.entity_semantic_worker.submit(
                    SemanticEnrichmentRequest(
                        entity.entity_id,
                        entity.source_track_id,
                        entity_observation,
                        prepared,
                        trigger,
                    )
                )
                self._entity_semantic_submitted[entity.entity_id] = frame.identity.observation_ns
        if self.corridor_analyzer is not None and result.world_state is not None:
            corridor_started = self.clock()
            result = replace(
                result, corridor_analysis=self.corridor_analyzer.analyze(result.world_state)
            )
            self.metrics.stages["corridor"].add(self.clock() - corridor_started)
            self._corridor_published += 1
        if self.trajectory_predictor is not None and result.world_state is not None:
            trajectory_started = self.clock()
            result = replace(
                result,
                trajectory_set=self.trajectory_predictor.predict(
                    result.world_state, result.corridor_analysis
                ),
            )
            self.metrics.stages["trajectory"].add(self.clock() - trajectory_started)
            self._trajectory_published += 1
        if (
            self.interaction_analyzer is not None
            and result.world_state is not None
            and result.corridor_analysis is not None
            and result.trajectory_set is not None
        ):
            interaction_started = self.clock()
            result = replace(
                result,
                interaction_analysis=self.interaction_analyzer.analyze(
                    result.world_state, result.corridor_analysis, result.trajectory_set
                ),
            )
            self.metrics.stages["interaction"].add(self.clock() - interaction_started)
            self._interaction_published += 1
        if self.risk_engine is not None and result.world_state is not None:
            risk_started = self.clock()
            result = replace(
                result,
                risk_assessment_set=self.risk_engine.assess(
                    result.world_state,
                    result.corridor_analysis,
                    result.trajectory_set,
                    result.interaction_analysis,
                ),
            )
            self.metrics.stages["risk"].add(self.clock() - risk_started)
            self._risk_published += 1
        if self.attention_engine is not None and result.risk_assessment_set is not None:
            attention_started = self.clock()
            attention_now = result.risk_assessment_set.state_timestamp
            if self.config.mode == "REALTIME":
                # Map processing lateness onto the authoritative media timeline.
                # Old inference must not create a fresh interruption intent.
                attention_now += max(0, attention_started - item.due_ns)
            result = replace(
                result,
                attention_decision_set=self.attention_engine.decide(
                    result.risk_assessment_set,
                    audio=self.alert_engine.presenter.channel_state()
                    if self.alert_engine
                    else None,
                    now_ns=attention_now,
                ),
            )
            self.metrics.stages["attention"].add(self.clock() - attention_started)
            self._attention_published += 1
            if (
                self.config.semantic_presentation_enabled
                and result.world_state is not None
                and result.attention_decision_set is not None
            ):
                result = replace(
                    result,
                    attention_decision_set=attach_entity_semantics(
                        result.attention_decision_set, result.world_state
                    ),
                )
        if result.attention_decision_set is not None:
            result = replace(result, attention_decision_set=attach_event_lineage(result))
        if self.alert_engine is not None and result.attention_decision_set is not None:
            alert_started = self.clock()
            observation = frame.identity.observation_ns

            def alert_clock() -> int:
                return (
                    observation + max(0, self.clock() - item.due_ns)
                    if self.config.mode == "REALTIME"
                    else observation
                )

            result = replace(
                result,
                alert_output_set=self.alert_engine.process(
                    result.attention_decision_set,
                    now_ns=alert_clock(),
                    mode="REALTIME"
                    if self.config.mode == "REALTIME"
                    else "OFFLINE_REPLAY_PRESENTATION",
                    delivery_clock=alert_clock,
                ),
            )
            self.metrics.stages["alerts"].add(self.clock() - alert_started)
        completed = self.clock()
        if result.depth is not None:
            self.metrics.stages["depth_sampling"].add(completed - sampling_started)
        if self.abandon(item):
            return
        result = replace(result, timing=replace(trace, postprocess_completed_ns=completed))
        self.metrics.stages["postprocess"].add(completed - components_at)
        self.metrics.stages["result"].add(completed - frame.decode_started_ns)
        record_start = self.clock()
        self._failure_stage = "RECORD"
        self.recorder.write_result(result)
        if self.config.mode == "REALTIME":
            # due_ns maps media observation time onto this run's monotonic replay
            # anchor. Never subtract media PTS directly from a processing timestamp.
            age = self.clock() - item.due_ns
            self.metrics.stages["realtime_result_age"].add(age)
            if result.detector is not None:
                self.metrics.stages["realtime_detector_result_age"].add(age)
            if result.depth is not None:
                self.metrics.stages["realtime_depth_result_age"].add(
                    age + frame.identity.observation_ns - result.depth.identity.observation_ns
                )
            if result.optical_flow is not None:
                self.metrics.stages["realtime_flow_result_age"].add(
                    age
                    + frame.identity.observation_ns
                    - result.optical_flow.identity.observation_ns
                )
            if result.segmentation is not None:
                self.metrics.stages["realtime_semantic_result_age"].add(
                    age
                    + frame.identity.observation_ns
                    - result.segmentation.observed_identity.observation_ns
                )
            if result.tracks is not None:
                self.metrics.stages["realtime_tracking_result_age"].add(age)
        self.metrics.counts["processed"] += 1
        if result.optical_flow is not None:
            self._flow_pairs_published += 1
        if result.segmentation is not None:
            self._semantic_published += 1
        self._active_accounted = True
        self.recorder.debug_frame(frame)
        self.metrics.stages["record"].add(self.clock() - record_start)
        if errors:
            self.metrics.counts["failed"] += 1
        if self.renderer is not None:
            self._failure_stage = "RENDER"
            render_started = self.clock()
            self.renderer.render(
                frame,
                result,
                self.metrics.source_fps(),
                self.metrics.output_fps(render_started - self._started_ns),
            )
            self.metrics.stages["render"].add(self.clock() - render_started)
        self.emit(Event("FrameCompleted", frame.identity))

    def run(self, source: FrameSource, cancel: Cancellation | None = None) -> dict[str, Any]:
        if self._has_run:
            raise LabError("PIPELINE_SINGLE_USE")
        self._has_run = True
        cancel = cancel or Cancellation()
        self._cancel = cancel
        started = self.clock()
        self._started_ns = started
        reason, failure = "END_OF_STREAM", None
        iterator: Iterator[Frame | SourceIssue] | None = None
        pending: Frame | None = None
        active: QueuedFrame | None = None
        caught: BaseException | None = None
        try:
            if self.config.realtime_rescue:
                source = LatestSource(source, self.config.start_ns, self.config.end_ns)
            iterator = iter(source)
            pending = self.read(iterator, cancel)
            anchor = self.clock()
            observation_anchor = pending.identity.observation_ns if pending is not None else 0
            if isinstance(source, LatestSource) and source.anchor_ns is not None:
                anchor, observation_anchor = source.anchor_ns, source.observation_anchor
            while (pending is not None or self.queue.items) and not cancel.requested:
                if self.config.realtime_rescue and pending is not None:
                    self.accept(
                        pending, anchor + pending.identity.observation_ns - observation_anchor
                    )
                    pending = None
                    active = self.queue.pop()
                    self.process(active)
                    active = None
                    self._active_frame = None
                    self._failure_stage = "SOURCE"
                    pending = self.read(iterator, cancel)
                    continue
                if self.config.mode == "OFFLINE_REPLAY":
                    if pending is not None:
                        admitting = pending
                        pending = None
                        self.accept(admitting, self.clock())
                        del admitting
                    active = self.queue.pop()
                    self.process(active)
                    active = None
                    self._active_frame = None
                    self._failure_stage = "SOURCE"
                    pending = self.read(iterator, cancel)
                    continue
                # Bound catch-up work: a decoder slower than source time must not
                # consume the entire recording before processing any queued frame.
                admissions = 0
                previous_lateness: int | None = None
                while pending is not None and not cancel.requested and admissions < 1024:
                    due = anchor + pending.identity.observation_ns - observation_anchor
                    lateness = self.clock() - due
                    if lateness < 0:
                        break
                    if admissions % 32 == 0:
                        # Extend catch-up only while decoding is actually reducing
                        # backlog. A slower-than-source decoder still yields after
                        # 32 admissions; a fast decoder can catch a slow inference.
                        if previous_lateness is not None and lateness >= previous_lateness:
                            break
                        previous_lateness = lateness
                    admitting = pending
                    pending = None
                    self.accept(admitting, due)
                    admissions += 1
                    del admitting
                    self._failure_stage = "SOURCE"
                    pending = self.read(iterator, cancel)
                if self.queue.items and not cancel.requested:
                    active = self.queue.pop()
                    self.process(active)
                    active = None
                    self._active_frame = None
                elif pending is not None and not cancel.requested:
                    due = anchor + pending.identity.observation_ns - observation_anchor
                    self.sleep(min(max(0, due - self.clock()) / 1e9, 0.02))
            if cancel.requested:
                reason = "CANCELLED"
        except KeyboardInterrupt as error:
            reason, caught = "CANCELLED", error
        except BaseException as error:
            reason, failure, caught = "FATAL", self._failure_stage + "_FAILED", error
            self.metrics.counts["failed"] += 1
        finally:
            abandoned: list[Frame] = []
            if active is not None and not self._active_accounted:
                abandoned.append(active.frame)
            if self._reading_frame is not None:
                abandoned.append(self._reading_frame)
            if pending is not None:
                abandoned.append(pending)
            while self.queue.items:
                abandoned.append(self.queue.pop().frame)
            try:
                for abandoned_frame in abandoned:
                    try:
                        self.drop(
                            abandoned_frame,
                            DropReason.USER_SKIP
                            if reason == "CANCELLED"
                            else DropReason.PIPELINE_FAILURE,
                        )
                    except BaseException as error:
                        caught = caught or error
                        reason, failure = "FATAL", "FINALIZATION_FAILED"
            finally:
                self.queue.clear()
                self._active_frame = None
                self._reading_frame = None
                try:
                    close_iterator = getattr(iterator, "close", None)
                    if close_iterator is not None:
                        close_iterator()
                except BaseException as error:
                    caught = caught or error
                    reason, failure = "FATAL", "ITERATOR_CLOSE_FAILED"
                finally:
                    try:
                        source.close()
                    except BaseException as error:
                        caught = caught or error
                        reason, failure = "FATAL", "SOURCE_CLOSE_FAILED"
                        self.metrics.counts["failed"] += 1
                    if self.renderer is not None:
                        try:
                            self.renderer.close()
                        except BaseException as error:
                            caught = caught or error
                            reason, failure = "FATAL", "RENDERER_CLOSE_FAILED"
                    summary = self.metrics.summary(self.clock() - started, self.queue.peak)
                    if isinstance(source, LatestSource):
                        summary["acquisition"] = {
                            "decoded_in_window": source.decoded,
                            "pending_replaced": source.replaced,
                            "skipped_before_conversion": source.skipped_conversion,
                            "source_end_observed_ns": source.last_seen_ns,
                            "pending_capacity": 1,
                            "timing": source.timing(),
                        }
                    summary["enrichment_rejections"] = self.enrichment_rejections.copy()
                    summary["enrichment_delivered_timing"] = {
                        key: value.summary() for key, value in self.enrichment_timing.items()
                    }
                    for name, worker in self.enrichment_workers.items():
                        try:
                            worker.close()
                        except BaseException as error:
                            caught = caught or error
                            reason, failure = "FATAL", "ENRICHMENT_CLOSE_FAILED"
                            summary["frame_counts"]["failed"] += 1
                        summary.setdefault("enrichment_workers", {})[name] = worker.summary()
                        summary.setdefault("enrichment_compute", {})[name] = worker.timing()
                    summary["semantic_results_published"] = self._semantic_published
                    summary["view_health_timing"] = self.view_health_timing.summary()
                    if self.entity_semantic_worker is not None:
                        try:
                            self.entity_semantic_worker.close()
                        except BaseException as error:
                            caught = caught or error
                            reason, failure = "FATAL", "ENTITY_SEMANTIC_CLOSE_FAILED"
                        summary["entity_semantic_worker"] = (
                            self.entity_semantic_worker.worker.summary()
                        )
                        summary["entity_semantic_timing"] = self.entity_semantic_worker.timing()
                        summary["entity_semantic_applied"] = self._entity_semantic_applied
                        self._entity_semantic_submitted.clear()
                    summary["world_states_published"] = self._world_published
                    summary["corridor_analyses_published"] = self._corridor_published
                    summary["trajectory_sets_published"] = self._trajectory_published
                    summary["interaction_analyses_published"] = self._interaction_published
                    summary["risk_assessment_sets_published"] = self._risk_published
                    summary["attention_decision_sets_published"] = self._attention_published
                    if self.alert_engine is not None:
                        try:
                            self.alert_engine.reset()
                        except BaseException as error:
                            caught = caught or error
                            reason, failure = "FATAL", "ALERT_RESET_FAILED"
                    if self.attention_engine is not None:
                        try:
                            self.attention_engine.reset()
                        except BaseException as error:
                            caught = caught or error
                            reason, failure = "FATAL", "ATTENTION_RESET_FAILED"
                    if self.risk_engine is not None:
                        try:
                            self.risk_engine.reset()
                        except BaseException as error:
                            caught = caught or error
                            reason, failure = "FATAL", "RISK_RESET_FAILED"
                    if self.world_model is not None:
                        try:
                            self.world_model.close()
                        except BaseException as error:
                            caught = caught or error
                            reason, failure = "FATAL", "WORLD_MODEL_CLOSE_FAILED"
                    if self.config.motion is not None:
                        summary["motion_states"] = self._motion_counts.copy()
                        summary["flow_pairs_computed"] = self._flow_pairs_computed
                        summary["flow_pairs_published"] = self._flow_pairs_published
                    if self.tracker is not None:
                        summary["tracking_peaks"] = self._tracking_peaks.copy()
                        try:
                            self.tracker.close()
                        except BaseException as error:
                            caught = caught or error
                            reason, failure = "FATAL", "TRACKER_CLOSE_FAILED"
                    self._tracking_ids = ()
                    close_flow = getattr(self.flow, "close", None)
                    if self.semantic_worker is not None:
                        summary["semantic_jobs"] = self.semantic_worker.submitted
                        summary["semantic_busy_ticks"] = self.semantic_worker.skipped
                        try:
                            self.semantic_worker.close()
                        except BaseException as error:
                            caught = caught or error
                            reason, failure = "FATAL", "SEMANTIC_WORKER_CLOSE_FAILED"
                    if close_flow is not None:
                        try:
                            close_flow()
                        except BaseException as error:
                            caught = caught or error
                            reason, failure = "FATAL", "FLOW_CLOSE_FAILED"
                    self._tracking_identity = None
                    try:
                        self.emit(Event("SessionCompleted"))
                    except BaseException as error:
                        caught = caught or error
                        reason, failure = "FATAL", "LISTENER_OR_RECORDER_FAILED"
                    try:
                        self.recorder.finish(summary, reason, failure)
                    except BaseException as error:
                        caught = caught or error
                        failure = "RECORDER_FINALIZATION_FAILED"
                        self.recorder.close()
        if caught is not None:
            if isinstance(caught, KeyboardInterrupt):
                raise caught
            raise LabError(failure or "PIPELINE_FATAL") from None
        return self.recorder.manifest
