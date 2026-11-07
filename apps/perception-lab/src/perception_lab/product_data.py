"""Offline consent, reviewed examples and dataset lineage. Never called by Guardian.

No network clients, training loop, automatic enrollment or policy promotion live here.
"""

import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ConsentGrant(Contract):
    participant: str = Field(min_length=1, max_length=128)
    purpose: Literal["LOCAL_REVIEW", "MODEL_RESEARCH"]
    granted: bool
    expires_at: int = Field(gt=0)
    revoked_at: int | None = None

    def permits(self, purpose: str, now: int) -> bool:
        return (
            self.granted
            and self.purpose == purpose
            and self.revoked_at is None
            and now < self.expires_at
        )


class Artifact(Contract):
    artifact_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    participant: str = Field(min_length=1, max_length=128)
    route: str = Field(min_length=1, max_length=128)
    session: str = Field(min_length=1, max_length=128)
    scenario: str = Field(min_length=1, max_length=80)
    license_or_consent_reference: str = Field(min_length=1, max_length=256)
    redaction_reviewed: bool
    kind: Literal["ALERT", "SILENCE", "MISSED_IMPORTANT_EVENT", "CAPABILITY_CHANGE"]
    pseudo_label: bool = False
    deleted: bool = False


class Review(Contract):
    artifact_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewer: str = Field(min_length=1, max_length=128)
    independent: bool
    relevance: Literal["RELEVANT", "IRRELEVANT", "UNCERTAIN", "INSUFFICIENT_CONTEXT"]
    timing: Literal["TIMELY", "EARLY", "LATE", "MISSED", "NOT_APPLICABLE", "UNKNOWN"]
    motion: Literal["STATIC", "MOVING", "CAMERA_MOTION", "UNKNOWN"]
    interruption: Literal["MUST_NOTIFY", "OPTIONAL", "SILENCE", "UNAVAILABLE", "UNKNOWN"]
    note: str = Field(default="", max_length=2000)


class ObjectStore(Protocol):
    def put(self, owner: str, data: bytes) -> str: ...
    def get(self, owner: str, digest: str) -> bytes: ...
    def delete(self, owner: str, digest: str) -> None: ...


class LocalObjectStore:
    """Private local content-addressed adapter. Explicit writes, 10 MiB object/100 MiB owner cap."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, owner: str, digest: str) -> Path:
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", owner) or not re.fullmatch(
            r"[a-f0-9]{64}", digest
        ):
            raise ValueError("Invalid storage identity")
        path = self.root / owner / digest
        if (
            path.parent.is_symlink()
            or path.is_symlink()
            or not path.resolve().is_relative_to(self.root)
        ):
            raise ValueError("Linked storage path")
        return path

    def put(self, owner: str, data: bytes) -> str:
        if not 0 < len(data) <= 10 * 1024**2:
            raise ValueError("Object quota")
        digest = hashlib.sha256(data).hexdigest()
        path = self.path(owner, digest)
        path.parent.mkdir(exist_ok=True)
        with owner_lock(path.parent):
            try:
                if path.exists():
                    if self.get(owner, digest) != data:
                        raise ValueError("Corrupt object")
                    return digest
                total = sum(p.stat().st_size for p in path.parent.iterdir() if p.is_file())
                if total + len(data) > 100 * 1024**2:
                    raise ValueError("Owner quota")
                with tempfile.NamedTemporaryFile(
                    dir=path.parent, prefix=".partial-", delete=False
                ) as file:
                    temporary = Path(file.name)
                    file.write(data)
                    file.flush()
                    os.fsync(file.fileno())
                os.replace(temporary, path)
                return digest
            finally:
                if "temporary" in locals():
                    temporary.unlink(missing_ok=True)

    def get(self, owner: str, digest: str) -> bytes:
        path = self.path(owner, digest)
        if path.stat().st_size > 10 * 1024**2:
            raise ValueError("Object quota")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("Content hash mismatch")
        return data

    def delete(self, owner: str, digest: str) -> None:
        path = self.path(owner, digest)
        path.parent.mkdir(exist_ok=True)
        with owner_lock(path.parent):
            path.unlink(missing_ok=True)


@contextmanager
def owner_lock(directory: Path) -> Iterator[None]:
    path = directory / ".write-lock"
    if path.is_symlink():
        raise ValueError("Linked lock")
    with path.open("a+b") as lock:
        if lock.seek(0, os.SEEK_END) == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            lock.seek(0)
            if sys.platform == "win32":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def dataset_manifest(
    artifacts: list[Artifact], reviews: list[Review], grants: list[ConsentGrant], now: int
) -> dict[str, object]:
    if not artifacts or len({a.artifact_id for a in artifacts}) != len(artifacts):
        raise ValueError("Empty or duplicate dataset")
    if len({(g.participant, g.purpose) for g in grants}) != len(grants):
        raise ValueError("Ambiguous consent history; provide the current grant only")
    allowed = {g.participant for g in grants if g.permits("MODEL_RESEARCH", now)}
    by_id = {a.artifact_id: a for a in artifacts}
    grouped: dict[str, list[Review]] = {key: [] for key in by_id}
    for review in reviews:
        if review.artifact_id not in grouped:
            raise ValueError("Orphan review")
        grouped[review.artifact_id].append(review)
    for artifact in artifacts:
        if (
            artifact.deleted
            or artifact.participant not in allowed
            or not artifact.redaction_reviewed
        ):
            raise ValueError("Consent, deletion or redaction gate")
        labels = grouped[artifact.artifact_id]
        if not labels or any(
            not r.independent or r.reviewer == artifact.participant for r in labels
        ):
            raise ValueError("Independent review required")
        if len({r.reviewer for r in labels}) != len(labels):
            raise ValueError("Duplicate reviewer")
        if len({(r.relevance, r.timing, r.motion, r.interruption) for r in labels}) != 1:
            raise ValueError("Reviewer disagreement requires reconciliation")
    # Connected components prevent leakage through ANY participant, route or session.
    parent = list(range(len(artifacts)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    identifiers: dict[tuple[str, str], int] = {}
    for index, artifact in enumerate(artifacts):
        for key in ("participant", "route", "session"):
            value = (key, str(getattr(artifact, key)))
            if value in identifiers:
                parent[find(index)] = find(identifiers[value])
            identifiers[value] = index
    components: dict[int, list[str]] = {}
    for index, artifact in enumerate(artifacts):
        components.setdefault(find(index), []).append(artifact.artifact_id)
    rows = []
    for index, artifact in enumerate(artifacts):
        group = hashlib.sha256("|".join(sorted(components[find(index)])).encode()).hexdigest()
        bucket = int(group[:8], 16) % 100
        split = "train" if bucket < 70 else "validation" if bucket < 85 else "test"
        rows.append(
            {
                "artifact": artifact.model_dump(),
                "review": [
                    r.model_dump()
                    for r in sorted(grouped[artifact.artifact_id], key=lambda r: r.reviewer)
                ],
                "split": split,
                "group": group,
            }
        )
    rows.sort(key=lambda row: str(row["artifact"]))
    payload = {
        "schema": "vision.dataset.v1",
        "rows": rows,
        "training_authorized": False,
        "scope": "OFFLINE_REVIEWED_MANIFEST_ONLY",
        "consent_checked_at": now,
        "research_grants": [
            g.model_dump()
            for g in sorted(grants, key=lambda g: (g.participant, g.purpose))
            if g.purpose == "MODEL_RESEARCH"
        ],
    }
    version = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {**payload, "version_sha256": version}


def evaluate_optional_ranking(
    truth: list[Literal["MUST_NOTIFY", "OPTIONAL", "SILENT", "UNAVAILABLE", "UNKNOWN"]],
    candidates: list[bool | None],
) -> dict[str, object]:
    if not truth or len(truth) != len(candidates):
        raise ValueError("Paired independent labels required")
    mandatory = sum(label in ("MUST_NOTIFY", "UNAVAILABLE") for label in truth)
    violations = sum(
        label in ("MUST_NOTIFY", "UNAVAILABLE") and decision is False
        for label, decision in zip(truth, candidates, strict=True)
    )
    return {
        "schema": "vision.utility-evaluation.v1",
        "mode": "SHADOW_ONLY",
        "samples": len(truth),
        "mandatory_examples": mandatory,
        "forbidden_suppressions": violations,
        "unknown_labels": truth.count("UNKNOWN"),
        "abstentions": candidates.count(None),
        "unnecessary_interruptions": sum(
            label == "SILENT" and decision is True
            for label, decision in zip(truth, candidates, strict=True)
        ),
        "optional_omissions": sum(
            label == "OPTIONAL" and decision is False
            for label, decision in zip(truth, candidates, strict=True)
        ),
        "safety_gate_passed": violations == 0,
        "promotion_allowed": False,
        "training_performed": False,
    }


class DatasetRegistry:
    """Local version registry and retryable deletion ledger; no remote replicas exist."""

    def __init__(self, path: Path, store: ObjectStore) -> None:
        self.store = store
        self.db = sqlite3.connect(path)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS versions(
                version TEXT PRIMARY KEY, manifest TEXT NOT NULL, status TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS withdrawals(participant TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS deletions(
                owner TEXT, digest TEXT, status TEXT NOT NULL, PRIMARY KEY(owner,digest));
        """)

    def close(self) -> None:
        self.db.close()

    def publish(
        self, artifacts: list[Artifact], reviews: list[Review], grants: list[ConsentGrant], now: int
    ) -> str:
        manifest = dataset_manifest(artifacts, reviews, grants, now)
        version = str(manifest["version_sha256"])
        with self.db:
            # Serialize eligibility with withdrawal across registry connections/processes.
            self.db.execute("BEGIN IMMEDIATE")
            withdrawn = {row[0] for row in self.db.execute("SELECT participant FROM withdrawals")}
            if any(a.participant in withdrawn for a in artifacts):
                raise ValueError("Withdrawn contribution cannot be re-enrolled implicitly")
            self.db.execute(
                "INSERT OR IGNORE INTO versions VALUES (?,?,?)",
                (version, json.dumps(manifest, sort_keys=True), "REVIEWED_NOT_TRAINED"),
            )
        return version

    def manifest(self, version: str, now: int | None = None) -> dict[str, object]:
        row = self.db.execute(
            "SELECT manifest,status FROM versions WHERE version=?", (version,)
        ).fetchone()
        if row is None or row[1] != "REVIEWED_NOT_TRAINED":
            raise ValueError("Dataset version unavailable or withdrawn")
        result: dict[str, object] = json.loads(row[0])
        grants = result.get("research_grants")
        if not isinstance(grants, list) or not grants:
            raise ValueError("Dataset has no current consent evidence")
        current = int(time.time()) if now is None else now
        if any(
            not ConsentGrant.model_validate(g).permits("MODEL_RESEARCH", current) for g in grants
        ):
            raise ValueError("Dataset consent has expired or been revoked")
        return result

    def withdraw(self, participant: str) -> None:
        # Commit tombstones before deleting bytes so interruption never restores eligibility.
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO withdrawals VALUES (?)", (participant,))
            for version, payload in self.db.execute(
                "SELECT version,manifest FROM versions"
            ).fetchall():
                manifest = json.loads(payload)
                matching = [
                    r["artifact"]
                    for r in manifest["rows"]
                    if r["artifact"]["participant"] == participant
                ]
                if matching:
                    self.db.execute(
                        "UPDATE versions SET status='INVALIDATED_CONSENT_WITHDRAWN' "
                        "WHERE version=?",
                        (version,),
                    )
                    for artifact in matching:
                        self.db.execute(
                            "INSERT OR IGNORE INTO deletions VALUES (?,?, 'PENDING')",
                            (participant, artifact["artifact_id"]),
                        )
        self.reconcile_deletions()

    def reconcile_deletions(self) -> None:
        for owner, digest in self.db.execute(
            "SELECT owner,digest FROM deletions WHERE status='PENDING'"
        ).fetchall():
            try:
                self.store.delete(owner, digest)
            except OSError:
                continue
            with self.db:
                self.db.execute(
                    "UPDATE deletions SET status='LOCAL_ACTIVE_COPY_DELETED' "
                    "WHERE owner=? AND digest=?",
                    (owner, digest),
                )


def hard_cases(artifacts: list[Artifact], reviews: list[Review]) -> list[str]:
    """Review queue only, including missed events and silence. No automatic truth labels."""
    uncertain = {
        r.artifact_id
        for r in reviews
        if r.relevance in ("UNCERTAIN", "INSUFFICIENT_CONTEXT")
        or r.motion == "UNKNOWN"
        or r.timing in ("LATE", "MISSED", "UNKNOWN")
    }
    return [
        a.artifact_id
        for a in artifacts
        if not a.deleted
        and (a.kind in ("MISSED_IMPORTANT_EVENT", "SILENCE") or a.artifact_id in uncertain)
    ]
