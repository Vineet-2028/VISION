"""Small English template table; evidence selection belongs upstream."""

from time import perf_counter_ns

from .alert_config import AlertConfig
from .alert_types import AlertIntent, AlertPresentation
from .attention_types import AttentionAction
from .contracts import ComponentProvenance
from .metrics import Distribution

CATEGORIES = {
    "PERSON": "Person",
    "BICYCLE": "Bicycle",
    "MOTORCYCLE": "Motorcycle",
    "VEHICLE": "Vehicle",
    "OBSTACLE": "Obstacle",
    "UNKNOWN": "Object",
}
DIRECTIONS = {"LEFT": "left", "RIGHT": "right", "AHEAD": "ahead", "UNKNOWN": ""}


def bounded_concept_text(label: str) -> str | None:
    """Bound display text, without expanding a fixed class vocabulary."""
    if (
        not label
        or len(label) > 48
        or len(label.split()) > 4
        or not all(c.isalnum() or c in " '-" for c in label)
        or not any(c.isalpha() for c in label)
    ):
        return None
    return label[0].upper() + label[1:]


class EnglishV1AlertRenderer:
    def __init__(self, config: AlertConfig | None = None) -> None:
        self.config = config or AlertConfig()
        self.timings = {name: Distribution(2048) for name in ("template", "presentation")}

    def render(self, intent: AlertIntent, now_ns: int) -> AlertPresentation:
        started = perf_counter_ns()
        if now_ns < intent.state_timestamp or now_ns >= intent.valid_until_ns:
            raise ValueError("Alert outside its presentation interval")
        if intent.decision_type == AttentionAction.SILENT:
            raise ValueError("Silence cannot render")
        noun, direction = CATEGORIES[intent.category], DIRECTIONS[intent.direction]
        semantic_level = "GENERIC"
        if intent.concept_text is not None:
            bounded = bounded_concept_text(intent.concept_text)
            if bounded is not None:
                noun = bounded
                semantic_level = intent.semantic_level
        if intent.interaction == "CROSSING":
            suffix = "crossing" + (
                " ahead" if direction == "ahead" else f" from {direction}" if direction else ""
            )
        elif intent.interaction == "APPROACHING":
            suffix = "approaching" + (f" {direction}" if direction else "")
        elif intent.interaction in {"IN_CORRIDOR", "STATIC_OBSTACLE", "GENERIC"}:
            # Corridor membership alone does not establish the user's bearing.
            suffix = direction
        else:
            raise ValueError("Unsupported interaction")
        text = f"{noun} {suffix}".strip() + "."
        if intent.concept_text is not None and (
            len(text.split()) > self.config.max_words or len(text) > self.config.max_characters
        ):
            text = f"{CATEGORIES[intent.category]} {suffix}".strip() + "."
            semantic_level = "GENERIC"
        words = len(text.split())
        if words > self.config.max_words or len(text) > self.config.max_characters:
            raise ValueError("Phrase exceeds configured bound")
        age = (
            None if intent.source_observation_ns is None else now_ns - intent.source_observation_ns
        )
        self.timings["template"].add(perf_counter_ns() - started)
        started = perf_counter_ns()
        result = AlertPresentation(
            intent.alert_id,
            text,
            text,
            intent.urgency,
            "EMPHASIS"
            if intent.decision_type == AttentionAction.ESCALATE
            else "FULL_REPEAT"
            if intent.decision_type == AttentionAction.REPEAT
            else "NORMAL",
            ("TEXT", "OPTIONAL_SPEECH"),
            intent.source_observation_ns,
            intent.state_timestamp,
            now_ns,
            age,
            now_ns - intent.state_timestamp,
            intent.valid_until_ns,
            "PROTOTYPE_UNVALIDATED",
            "AGE_UNAVAILABLE"
            if age is None
            else "LATE_CANDIDATE"
            if age > self.config.late_after_ns
            else "ON_TIME_CANDIDATE",
            words,
            len(text),
            words * 60 / self.config.words_per_minute,
            ComponentProvenance(
                self.config.template_version,
                "alert-renderer",
                configuration_hash=intent.config_hash,
            ),
            semantic_level=semantic_level,
            lineage=intent.lineage,
        )
        self.timings["presentation"].add(perf_counter_ns() - started)
        return result
