"""Single-owner inference with one replaceable pending input and output.

Exceptions are sticky: a later success must never erase an unobserved failure.
The caller owns domain state; the worker owns only its provider invocation.
"""

from collections.abc import Callable
from dataclasses import dataclass
from threading import Condition, Thread
from time import perf_counter_ns

from .metrics import Distribution


@dataclass(frozen=True)
class Completion[T, R]:
    input: T
    output: R
    submitted_ns: int
    started_ns: int
    completed_ns: int


class LatestWorker[T, R]:
    def __init__(self, call: Callable[[T], R], name: str) -> None:
        self._call = call
        self._condition = Condition()
        self._pending: tuple[T, int] | None = None
        self._ready: Completion[T, R] | None = None
        self._error: BaseException | None = None
        self._error_observed = False
        self._closed = False
        self.submitted = self.replaced = self.completed = self.output_replaced = 0
        self.cancelled = 0
        self._queue_wait = Distribution(2048)
        self._compute = Distribution(2048)
        self._thread = Thread(target=self._run, name=name)
        self._started = False

    def submit(self, value: T) -> None:
        with self._condition:
            if self._closed or self._error is not None:
                raise RuntimeError("Worker closed or failed")
            self.submitted += 1
            self.replaced += self._pending is not None
            self._pending = (value, perf_counter_ns())
            if not self._started:
                self._thread.start()
                self._started = True
            self._condition.notify()

    def poll(self) -> Completion[T, R] | None:
        with self._condition:
            if self._error is not None:
                self._error_observed = True
                raise self._error
            result, self._ready = self._ready, None
            return result

    def _run(self) -> None:
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._closed or self._pending is not None)
                if self._closed:
                    return
                pending, self._pending = self._pending, None
            assert pending is not None
            value, submitted = pending
            started = perf_counter_ns()
            try:
                result = self._call(value)
            except BaseException as error:
                with self._condition:
                    self._error = error
                    self.cancelled += self._pending is not None
                    self._pending = None
                return
            completion = Completion(value, result, submitted, started, perf_counter_ns())
            with self._condition:
                self.completed += 1
                self._queue_wait.add(started - submitted)
                self._compute.add(completion.completed_ns - started)
                if not self._closed:
                    self.output_replaced += self._ready is not None
                    self._ready = completion

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self.cancelled += self._pending is not None
            self._pending = None
            self._condition.notify()
        # Never close a native provider while its inference is still running.
        if self._started:
            self._thread.join()
        with self._condition:
            self._ready = None
            if self._error is not None and not self._error_observed:
                self._error_observed = True
                raise self._error

    def summary(self) -> dict[str, int]:
        with self._condition:
            return {
                "submitted": self.submitted,
                "pending_replaced": self.replaced,
                "completed": self.completed,
                "output_replaced": self.output_replaced,
                "cancelled": self.cancelled,
                "pending_capacity": 1,
                "output_capacity": 1,
                "failures": int(self._error is not None),
            }

    def timing(self) -> dict[str, object]:
        with self._condition:
            return {"queue_wait": self._queue_wait.summary(), "compute": self._compute.summary()}
