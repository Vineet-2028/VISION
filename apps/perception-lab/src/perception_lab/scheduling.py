"""Source-time fixed cadence and bounded, single-owner buffering."""

from collections import deque
from dataclasses import dataclass

from .contracts import Frame


class FixedRateScheduler:
    def __init__(self, intervals_ns: dict[str, int]) -> None:
        if not intervals_ns or any(value <= 0 for value in intervals_ns.values()):
            raise ValueError("Positive intervals required")
        self.intervals = dict(intervals_ns)
        self.next_due: dict[str, int] = {}
        self.last_ns = -1

    def eligible(self, observation_ns: int) -> tuple[str, ...]:
        if observation_ns < 0 or observation_ns <= self.last_ns:
            raise ValueError("Scheduler requires strictly increasing observation times")
        self.last_ns = observation_ns
        eligible = []
        for name, interval in self.intervals.items():
            due = self.next_due.setdefault(name, observation_ns)
            if observation_ns >= due:
                eligible.append(name)
                # Execute once; skip missed ticks, retain the original cadence anchor.
                self.next_due[name] = due + ((observation_ns - due) // interval + 1) * interval
        return tuple(eligible)


@dataclass(frozen=True)
class QueuedFrame:
    frame: Frame
    accepted_ns: int
    due_ns: int


class FrameQueue:
    def __init__(self, capacity: int, policy: str) -> None:
        if capacity < 1 or policy not in {"PROCESS_ALL", "DROP_OLDEST", "LATEST_FRAME"}:
            raise ValueError("Invalid queue configuration")
        self.capacity = 1 if policy == "LATEST_FRAME" else capacity
        self.policy = policy
        self.items: deque[QueuedFrame] = deque()
        self.peak = 0

    def offer(self, item: QueuedFrame) -> QueuedFrame | None:
        dropped = None
        if len(self.items) == self.capacity:
            if self.policy == "PROCESS_ALL":
                raise BufferError("Producer must wait for consumer capacity")
            dropped = self.items.popleft()
        self.items.append(item)
        self.peak = max(self.peak, len(self.items))
        return dropped

    def pop(self) -> QueuedFrame:
        return self.items.popleft()

    def clear(self) -> None:
        self.items.clear()
