"""One high-resolution monotonic process clock, independent of media PTS."""

from time import perf_counter_ns


def processing_ns() -> int:
    # On Python 3.12 Windows, monotonic_ns may use the coarse tick-count clock.
    # perf_counter is monotonic and uses the high-resolution performance counter.
    return perf_counter_ns()
