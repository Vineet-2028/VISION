"""Single-owner replay engine. Source and processing clocks are never subtracted."""

import time
from collections.abc import Callable, Iterator
from dataclasses import replace
from typing import Any

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
from .depth_sampling import detection_depth, track_depth
from .ego_runtime import VisualEgoEstimator
from .flow import DenseFlowField
from .flow_runtime import FlowAdapter
from .geometry import CoreGeometry
from .metrics import Metrics
from .motion import TrackImageMotionObservation, sample_tracks
from .motion_geometry import calibration_hash, compensate
from .motion_masking import dynamic_exclusions
from .preprocessing import ImagePreprocessor
from .recording import SessionRecorder
from .scheduling import FixedRateScheduler, FrameQueue, QueuedFrame
from .sources import FrameSource
from .tracking import AssociationTracker
from .tracking_types import DetectorEvidence, MultiObjectTracker, TrackId
from .visualization import Renderer


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
    ) -> None:
        self.config, self.preprocessor, self.recorder = config, preprocessor, recorder
        self.listener, self.clock, self.sleep = listener, clock, sleep
        self.queue = FrameQueue(config.queue_capacity, config.drop_policy)
        self.metrics = Metrics(config.metrics_window)
        self.scheduler = FixedRateScheduler({str(k): v for k, v in config.intervals_ns.items()})
        self.detector = detector or NoOpDetector()
        self.depth = depth or NoOpDepthAdapter()
        self.segmentation = segmentation or NoOpSegmentationAdapter()
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

    def process(self, item: QueuedFrame) -> None:
        frame = item.frame
        self._active_frame = frame
        self._active_accounted = False
        started = self.clock()
        self.metrics.stages["queue"].add(started - item.accepted_ns)
        if self.abandon(item):
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
        for name in eligible:
            self._failure_stage = "COMPONENT_" + name.upper()
            provenance, call = calls[name]
            self.emit(Event("ComponentStarted", frame.identity, component=name))
            if self.abandon(item):
                return
            component_start = self.clock()
            status = "NO_OUTPUT"
            try:
                output = call(prepared, frame.identity)
                if output is not None:
                    expected_type: Any = {
                        "detector": DetectionOutput,
                        "depth": DepthOutput,
                        "segmentation": SegmentationOutput,
                        "optical_flow": OpticalFlowOutput,
                    }[name]
                    if not isinstance(output, expected_type):
                        raise LabError("COMPONENT_OUTPUT_TYPE_MISMATCH")
                    if output.identity != frame.identity:
                        raise LabError("COMPONENT_IDENTITY_MISMATCH")
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
                if self.config.motion.dynamic_masking
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
            if residual is not None and tracks is not None:
                track_sample_started = self.clock()
                track_motion = sample_tracks(tracks, residual)
                self.metrics.stages["motion_track_sampling"].add(
                    self.clock() - track_sample_started
                )
        result = FrameResult(
            frame.identity,
            frame.width,
            frame.height,
            frame.pixel_format,
            trace,
            tuple(executions),
            detector=published_detector
            if isinstance(published_detector, DetectionOutput)
            else None,
            depth=depth_output if isinstance(depth_output, DepthOutput) else None,
            detection_depths=detection_depth(published_detector, depth_output)
            if isinstance(published_detector, DetectionOutput)
            and isinstance(depth_output, DepthOutput)
            else (),
            track_depths=track_depth(
                tracks, depth_output if isinstance(depth_output, DepthOutput) else None
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
            track_image_motion=track_motion,
            warnings=()
            if frame.identity.timing == TimingProvenance.AUTHORITATIVE_PTS
            else ("DEGRADED_SOURCE_TIMING",),
        )
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
                self.metrics.stages["realtime_depth_result_age"].add(age)
            if result.optical_flow is not None:
                self.metrics.stages["realtime_flow_result_age"].add(age)
            if result.tracks is not None:
                self.metrics.stages["realtime_tracking_result_age"].add(age)
        self.metrics.counts["processed"] += 1
        if result.optical_flow is not None:
            self._flow_pairs_published += 1
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
            iterator = iter(source)
            pending = self.read(iterator, cancel)
            anchor = self.clock()
            observation_anchor = pending.identity.observation_ns if pending is not None else 0
            while (pending is not None or self.queue.items) and not cancel.requested:
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
                    if self.renderer is not None:
                        try:
                            self.renderer.close()
                        except BaseException as error:
                            caught = caught or error
                            reason, failure = "FATAL", "RENDERER_CLOSE_FAILED"
                    summary = self.metrics.summary(self.clock() - started, self.queue.peak)
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
