"""Bounded asynchronous diagnostic serialization, independent of model runtimes."""

import json
from queue import Empty, Full, Queue
from threading import Event, Thread
from time import perf_counter_ns


class AsyncTrace:
    """Bounded measurement writer. Overflow fails the run; never silently drops rows."""

    def __init__(self, stream):
        self.stream = stream
        self.queue = Queue(maxsize=16)
        self.stop = Event()
        self.error = None
        self.peak = 0
        self.rows = 0
        self.utf8_bytes = 0
        self.serialization_ns = 0
        self.write_ns = 0
        self.thread = Thread(target=self._run, name="sentinel-trace")
        self.started = False

    def submit(self, row):
        if self.stop.is_set():
            raise RuntimeError("Trace writer closed")
        if self.error is not None:
            raise RuntimeError("Trace writer failed") from self.error
        if not self.started:
            self.thread.start()
            self.started = True
        try:
            self.queue.put_nowait(row)
        except Full:
            raise RuntimeError("Trace writer capacity exhausted; measurement invalid") from None
        self.peak = max(self.peak, self.queue.qsize())

    def _run(self):
        try:
            while not self.stop.is_set() or not self.queue.empty():
                try:
                    row = self.queue.get(timeout=0.05)
                except Empty:
                    continue
                started = perf_counter_ns()
                payload = json.dumps(row, allow_nan=False, separators=(",", ":")) + "\n"
                self.serialization_ns += perf_counter_ns() - started
                size = len(payload.encode("utf-8"))
                started = perf_counter_ns()
                self.stream.write(payload)
                self.write_ns += perf_counter_ns() - started
                self.utf8_bytes += size
                self.rows += 1
            self.stream.flush()
        except BaseException as error:
            self.error = error

    def flush(self):
        # Only the writer thread touches the file while it is running.
        if self.error is not None:
            raise RuntimeError("Trace writer failed") from self.error

    def close(self):
        self.stop.set()
        if self.started:
            self.thread.join()
        self.flush()
