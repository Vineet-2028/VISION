"""One in-flight semantic job. Busy ticks are skipped, never queued behind inference."""

from concurrent.futures import Future, ThreadPoolExecutor

from .contracts import FrameIdentity
from .preprocessing import PreparedImage
from .semantics import SemanticFrame, SemanticSegmenter


class SemanticWorker:
    def __init__(self, provider: SemanticSegmenter) -> None:
        self.provider = provider
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sentinel-semantic")
        self.pending: Future[SemanticFrame | None] | None = None
        self.skipped = 0
        self.submitted = 0
        self.closed = False

    def poll(self) -> SemanticFrame | None:
        if self.pending is None or not self.pending.done():
            return None
        job, self.pending = self.pending, None
        return job.result()

    def submit(self, image: PreparedImage, identity: FrameIdentity) -> None:
        if self.closed:
            raise ValueError("Semantic worker closed")
        if self.pending is not None:
            self.skipped += 1
            return
        # PreparedImage belongs to immutable frame storage; exactly one job retains it.
        self.pending = self.executor.submit(self.provider.segment, image, identity)
        self.submitted += 1

    def close(self) -> None:
        self.closed = True
        self.executor.shutdown(wait=True, cancel_futures=True)
        self.pending = None
