"""Latest-only asynchronous semantics; the owner validates live entity association."""

from dataclasses import dataclass
from threading import Event, get_ident
from typing import Literal, Protocol

from .clocks import processing_ns
from .latest_worker import LatestWorker
from .metrics import Distribution
from .perceived_entity import PerceivedEntityObservation
from .preprocessing import PreparedImage
from .tracking_types import TrackId
from .world_types import WorldEntityId, WorldState

SemanticTrigger = Literal[
    "NEW_TRACK", "UNKNOWN_TRACK", "UNSTABLE_SEMANTICS", "PERIODIC_REFRESH", "HIGH_RELEVANCE_TRACK"
]


@dataclass(frozen=True)
class SemanticEnrichmentRequest:
    entity_id: WorldEntityId
    track_id: TrackId
    observation: PerceivedEntityObservation
    image: PreparedImage
    trigger: SemanticTrigger


class SemanticEnricher(Protocol):
    def enrich(self, request: SemanticEnrichmentRequest) -> PerceivedEntityObservation | None: ...


@dataclass(frozen=True)
class AcceptedSemanticEnrichment:
    entity_id: WorldEntityId
    track_id: TrackId
    observation: PerceivedEntityObservation
    queue_wait_ns: int
    compute_ns: int
    result_age_ns: int
    source_age_ns: int


class EntitySemanticWorker:
    def __init__(self, provider: SemanticEnricher, max_age_ns: int = 2_000_000_000) -> None:
        if type(max_age_ns) is not int or not 0 < max_age_ns <= 10_000_000_000:
            raise ValueError("Invalid semantic freshness bound")
        self.max_age_ns = max_age_ns
        self._owner = get_ident()
        self.rejected = 0
        self.result_age = Distribution(2048)
        self._provider_failed = Event()

        def execute(request: SemanticEnrichmentRequest) -> PerceivedEntityObservation | None:
            if self._provider_failed.is_set():
                return None
            try:
                output = provider.enrich(request)
            except Exception:
                # Optional naming must not terminate physical reasoning. Quarantine
                # this provider for the session; never expose arbitrary error text.
                self._provider_failed.set()
                return None
            if output is not None and (
                output.source_frame != request.observation.source_frame
                or output.bbox != request.observation.bbox
                or output.orientation_transform_sha256
                != request.observation.orientation_transform_sha256
            ):
                raise ValueError("Semantic provider changed source association/geometry")
            return output

        self.worker = LatestWorker(execute, "vision-entity-semantics")

    def _check_owner(self) -> None:
        if get_ident() != self._owner:
            raise ValueError("Semantic coordinator requires single-owner access")

    @property
    def provider_failed(self) -> bool:
        return self._provider_failed.is_set()

    def submit(self, request: SemanticEnrichmentRequest) -> None:
        self._check_owner()
        if request.entity_id.session_id != request.track_id.session_id:
            raise ValueError("Semantic request session mismatch")
        if request.image.mapping.fingerprint != request.observation.orientation_transform_sha256:
            raise ValueError("Semantic image transform mismatch")
        if request.image.pixels.flags.writeable:
            raise ValueError("Semantic worker requires immutable image ownership")
        if self.provider_failed:
            return
        self.worker.submit(request)

    def poll(self, state: WorldState) -> AcceptedSemanticEnrichment | None:
        self._check_owner()
        completion = self.worker.poll()
        if self.provider_failed or completion is None or completion.output is None:
            return None
        request, output = completion.input, completion.output
        elapsed = processing_ns() - completion.submitted_ns
        self.result_age.add(elapsed)
        entity = next((e for e in state.entities if e.entity_id == request.entity_id), None)
        identity = output.source_frame
        age = state.state_timestamp - identity.observation_ns
        if (
            state.session_id != request.entity_id.session_id
            or entity is None
            or entity.source_track_id != request.track_id
            or entity.lifecycle.value == "LOST"
            or entity.track_evidence.identity is None
            or entity.track_evidence.identity.source_id != identity.source_id
            or entity.track_evidence.identity.timing != identity.timing
            or entity.latest_observed_ns < identity.observation_ns
            or not 0 <= age < self.max_age_ns
            or not 0 <= elapsed < self.max_age_ns
        ):
            self.rejected += 1
            return None
        return AcceptedSemanticEnrichment(
            request.entity_id,
            request.track_id,
            output,
            completion.started_ns - completion.submitted_ns,
            completion.completed_ns - completion.started_ns,
            elapsed,
            age,
        )

    def close(self) -> None:
        self._check_owner()
        self.worker.close()

    def timing(self) -> dict[str, object]:
        self._check_owner()
        return {
            **self.worker.timing(),
            "result_age": self.result_age.summary(),
            "rejected": self.rejected,
            "provider_failed": self.provider_failed,
            "capability": "UNAVAILABLE" if self.provider_failed else "AVAILABLE",
        }
