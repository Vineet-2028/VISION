"""Deterministic local discovery and sequence allocation; never approves annotations."""

from hashlib import sha256
from pathlib import Path

from .detector_runtime import file_hash
from .evaluation_dataset import sample_indices


def discover(root: Path) -> tuple[Path, ...]:
    if not root.is_dir():
        raise ValueError("Video directory does not exist")
    resolved = root.resolve()
    videos = tuple(
        sorted(
            p
            for p in root.rglob("*")
            if p.is_file() and p.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm", ".avi"}
        )
    )
    if any(not p.resolve().is_relative_to(resolved) for p in videos):
        raise ValueError("Video escapes input directory")
    return videos


def allocate(videos: tuple[Path, ...], seed: int = 0) -> dict[Path, tuple[str, str]]:
    """Freeze entire sequences before annotation/inference; TEST means QUALIFICATION."""
    hashes = {path: file_hash(path) for path in videos}
    if len(set(hashes.values())) != len(hashes):
        raise ValueError("Duplicate source media; do not split copies across sets")
    ordered = sorted(videos, key=lambda p: sha256(f"{seed}:{hashes[p]}".encode()).hexdigest())
    # One sequence cannot honestly establish independent calibration and qualification.
    calibration_count = max(1, len(ordered) // 2)
    return {
        path: ("sequence-" + hashes[path][:16], "CALIBRATION" if i < calibration_count else "TEST")
        for i, path in enumerate(ordered)
    }


def event_sample_indices(
    observations_ns: list[int], windows: tuple[tuple[int, int], ...] = ()
) -> tuple[int, ...]:
    """2 Hz base plus 5 Hz inside predeclared half-open event windows; deduplicated."""
    selected = set(sample_indices(observations_ns, 2.0))
    for start, end in windows:
        if start < 0 or end <= start:
            raise ValueError("Invalid event interval")
        indices = [i for i, time in enumerate(observations_ns) if start <= time < end]
        selected.update(
            indices[i] for i in sample_indices([observations_ns[i] for i in indices], 5)
        )
    return tuple(sorted(selected))
