import hashlib
from pathlib import Path

import pytest

from perception_lab.product_data import (
    Artifact,
    ConsentGrant,
    DatasetRegistry,
    LocalObjectStore,
    Review,
    dataset_manifest,
    evaluate_optional_ranking,
    owner_lock,
)


def example(number: int, participant: str, route: str) -> Artifact:
    return Artifact(
        artifact_id=hashlib.sha256(str(number).encode()).hexdigest(),
        participant=participant,
        route=route,
        session=f"s{number}",
        scenario="CROSSING",
        license_or_consent_reference="local-test-consent",
        redaction_reviewed=True,
        kind="SILENCE",
    )


def review(artifact: Artifact) -> Review:
    return Review(
        artifact_id=artifact.artifact_id,
        reviewer="independent-reviewer",
        independent=True,
        relevance="RELEVANT",
        timing="MISSED",
        motion="MOVING",
        interruption="MUST_NOTIFY",
    )


def grant(participant: str) -> ConsentGrant:
    return ConsentGrant(
        participant=participant, purpose="MODEL_RESEARCH", granted=True, expires_at=100
    )


def test_no_training_without_independent_review_and_separate_consent() -> None:
    artifact = example(1, "p1", "r1")
    for grants, reviews in [
        ([], [review(artifact)]),
        ([grant("p1")], []),
        ([grant("p1").model_copy(update={"purpose": "LOCAL_REVIEW"})], [review(artifact)]),
    ]:
        with pytest.raises(ValueError):
            dataset_manifest([artifact], reviews, grants, 1)
    with pytest.raises(ValueError):
        dataset_manifest([artifact], [review(artifact)], [grant("p1")], 100)
    with pytest.raises(ValueError):
        dataset_manifest(
            [artifact.model_copy(update={"deleted": True})], [review(artifact)], [grant("p1")], 1
        )


def test_transitive_route_and_participant_links_cannot_leak_between_splits() -> None:
    artifacts = [example(1, "p1", "r1"), example(2, "p2", "r1"), example(3, "p2", "r2")]
    result = dataset_manifest(
        artifacts, [review(a) for a in artifacts], [grant("p1"), grant("p2")], 1
    )
    rows = result["rows"]
    assert isinstance(rows, list)
    assert len({row["split"] for row in rows}) == 1
    assert len({row["group"] for row in rows}) == 1
    assert result["training_authorized"] is False


def test_disagreement_and_self_review_are_not_truth() -> None:
    a = example(1, "p1", "r1")
    for labels in [
        [review(a).model_copy(update={"reviewer": "p1"})],
        [review(a), review(a).model_copy(update={"reviewer": "second", "relevance": "IRRELEVANT"})],
    ]:
        with pytest.raises(ValueError):
            dataset_manifest([a], labels, [grant("p1")], 1)


def test_local_store_tenant_isolation_integrity_dedup_and_offline_delete(tmp_path: Path) -> None:
    store = LocalObjectStore(tmp_path)
    digest = store.put("alice", b"consented fixture")
    assert store.put("alice", b"consented fixture") == digest
    with pytest.raises(FileNotFoundError):
        store.get("bob", digest)
    with pytest.raises(ValueError):
        store.get("../alice", digest)
    with owner_lock(tmp_path / "alice"):
        with pytest.raises(OSError):
            store.put("alice", b"concurrent")
    (tmp_path / "alice" / digest).write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        store.get("alice", digest)
    store.delete("alice", digest)
    store.delete("alice", digest)
    assert not (tmp_path / "alice" / digest).exists()


def test_shadow_scoring_never_promotes_or_hides_mandatory_violations() -> None:
    result = evaluate_optional_ranking(
        ["MUST_NOTIFY", "UNAVAILABLE", "OPTIONAL", "UNKNOWN"], [False, False, True, None]
    )
    assert result["forbidden_suppressions"] == 2
    assert result["unknown_labels"] == 1
    assert result["abstentions"] == 1
    assert result["promotion_allowed"] is False


def test_withdrawal_invalidates_versions_and_retry_survives_reopen(tmp_path: Path) -> None:
    class InterruptedStore(LocalObjectStore):
        def delete(self, owner: str, digest: str) -> None:
            raise OSError("interrupted storage job")

    store = LocalObjectStore(tmp_path / "objects")
    digest = store.put("p1", b"consented sample")
    artifact = example(1, "p1", "r1").model_copy(update={"artifact_id": digest})
    registry = DatasetRegistry(tmp_path / "registry.sqlite", InterruptedStore(tmp_path / "objects"))
    version = registry.publish([artifact], [review(artifact)], [grant("p1")], 1)
    assert registry.manifest(version, now=1)["version_sha256"] == version
    with pytest.raises(ValueError):
        registry.manifest(version, now=100)
    registry.withdraw("p1")
    assert (
        registry.db.execute("SELECT status FROM versions WHERE version=?", (version,)).fetchone()[0]
        == "INVALIDATED_CONSENT_WITHDRAWN"
    )
    registry.close()
    registry = DatasetRegistry(tmp_path / "registry.sqlite", store)
    registry.reconcile_deletions()
    assert not store.path("p1", digest).exists()
    with pytest.raises(ValueError):
        registry.publish([artifact], [review(artifact)], [grant("p1")], 1)
    with pytest.raises(ValueError):
        registry.manifest(version)
    registry.close()


def test_ambiguous_consent_fails_closed_and_review_order_is_canonical() -> None:
    a = example(1, "p1", "r1")
    labels = [review(a), review(a).model_copy(update={"reviewer": "second"})]
    first = dataset_manifest([a], labels, [grant("p1")], 1)
    assert first == dataset_manifest([a], list(reversed(labels)), [grant("p1")], 1)
    with pytest.raises(ValueError):
        dataset_manifest(
            [a], labels, [grant("p1"), grant("p1").model_copy(update={"revoked_at": 1})], 2
        )
