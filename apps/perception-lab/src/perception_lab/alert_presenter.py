"""Nonblocking local text presenter with one slot and bounded idempotency state."""

from collections import deque
from dataclasses import replace

from .alert_types import AlertIntent, AlertOutput, AlertPresentation
from .attention_types import AttentionAction, AudioChannelState


class RecordingAlertPresenter:
    """Acceptance records text, not audible delivery. No I/O on the pipeline thread.

    A single pending slot is consumed explicitly. No backlog drain is possible.
    Timestamp watermark rejects old IDs even after bounded dedup eviction.
    reset is required on a seek/session change; callers must cancel external output.
    """

    def __init__(self, history_size: int = 128) -> None:
        if not 1 <= history_size <= 512:
            raise ValueError("Invalid history bound")
        self.history_size = history_size
        self.reset()

    def reset(self, session_id: str | None = None) -> None:
        self.session_id = session_id
        self.pending: tuple[AlertIntent, AlertPresentation] | None = None
        self.history: deque[AlertOutput] = deque(maxlen=self.history_size)
        self._ids: deque[str] = deque(maxlen=self.history_size)
        self._timestamp = -1
        self._now = -1

    def channel_state(self) -> AudioChannelState:
        # This text sink does not play speech and hence never claims audio busy.
        return AudioChannelState()

    def submit(
        self, intent: AlertIntent, presentation: AlertPresentation, now_ns: int
    ) -> AlertOutput:
        def drop(status: str, reason: str) -> AlertOutput:
            result = AlertOutput(status, reason, intent)
            self.history.append(result)
            return result

        if self.session_id is None:
            self.session_id = intent.session_id
        if intent.session_id != self.session_id:
            return drop("DROPPED_INVALID", "WRONG_SESSION_RESET_REQUIRED")
        if now_ns >= intent.valid_until_ns:
            return drop("DROPPED_EXPIRED", "EXPIRED_AT_SINK")
        if (
            intent.decision_type == AttentionAction.SILENT
            or presentation.alert_id != intent.alert_id
            or presentation.valid_until_ns != intent.valid_until_ns
            or presentation.generation_timestamp > now_ns
            or now_ns < intent.state_timestamp
            or now_ns < self._now
        ):
            return drop("DROPPED_INVALID", "INVALID_PRESENTATION_OR_CLOCK")
        if intent.alert_id in self._ids:
            return drop("DROPPED_DUPLICATE", "ALREADY_ACCEPTED")
        if intent.state_timestamp <= self._timestamp:
            return drop("DROPPED_INVALID", "OUT_OF_ORDER_OR_REPLAYED")
        self._now, self._timestamp = now_ns, intent.state_timestamp
        self._ids.append(intent.alert_id)
        superseded = self.pending[0].alert_id if self.pending else None
        if self.pending is not None:
            old, _ = self.pending
            self.history.append(AlertOutput("DROPPED_SUPERSEDED", "LATEST_SELECTED_INTENT", old))
        self.pending = (intent, presentation)
        result = AlertOutput("READY", "TEXT_SINK_ACCEPTED_NOT_AUDIO", intent, presentation, True)
        result = replace(
            result,
            delivery_timestamp=now_ns,
            source_age_at_delivery_ns=(now_ns - intent.source_observation_ns)
            if intent.source_observation_ns is not None
            else None,
            presentation_age_ns=now_ns - presentation.generation_timestamp,
            superseded_alert_id=superseded,
        )
        self.history.append(result)
        return result

    def take(self, now_ns: int) -> AlertOutput:
        """Consumer must supply current media-mapped time, including output delay."""
        if self.pending is None:
            return AlertOutput("NO_PRESENTATION", "EMPTY")
        intent, presentation = self.pending
        self.pending = None
        if now_ns < self._now:
            result = AlertOutput("DROPPED_INVALID", "BACKWARD_DELIVERY_CLOCK", intent)
        elif now_ns >= intent.valid_until_ns:
            result = AlertOutput("DROPPED_EXPIRED", "EXPIRED_BEFORE_CONSUMPTION", intent)
        else:
            result = AlertOutput("READY", "TEXT_CONSUMED_NOT_AUDIO", intent, presentation, True)
            result = replace(
                result,
                delivery_timestamp=now_ns,
                source_age_at_delivery_ns=(now_ns - intent.source_observation_ns)
                if intent.source_observation_ns is not None
                else None,
                presentation_age_ns=now_ns - presentation.generation_timestamp,
            )
        self._now = max(self._now, now_ns)
        self.history.append(result)
        return result


class NullAlertPresenter(RecordingAlertPresenter):
    def submit(
        self, intent: AlertIntent, presentation: AlertPresentation, now_ns: int
    ) -> AlertOutput:
        output = super().submit(intent, presentation, now_ns)
        self.pending = None
        if output.status == "READY":
            output = AlertOutput("NO_PRESENTATION", "NULL_SINK", intent, presentation)
            self.history[-1] = output
        return output
