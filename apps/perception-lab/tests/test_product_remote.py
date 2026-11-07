from pathlib import Path
from time import time
from types import SimpleNamespace

import pytest

from perception_lab.product_data import (
    Artifact,
    ConsentGrant,
    DatasetRegistry,
    LocalObjectStore,
    Review,
)
from perception_lab.product_remote import PrivateS3Export


class FakeClient:
    def __init__(self) -> None:
        self.meta = SimpleNamespace(
            endpoint_url="https://storage.invalid", config=SimpleNamespace(signature_version="s3v4")
        )
        self.calls: list[dict[str, object]] = []

    def put_object(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return {}

    def delete_object(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return {}

    def generate_presigned_url(
        self, ClientMethod: str, Params: dict[str, object], ExpiresIn: int, HttpMethod: str
    ) -> str:
        self.calls.append(dict(method=ClientMethod, params=Params, ttl=ExpiresIn, verb=HttpMethod))
        return "https://storage.invalid/test-only-not-a-real-signature"


def test_remote_requires_configuration_consent_owner_and_bounded_url() -> None:
    client = FakeClient()
    with pytest.raises(ValueError):
        PrivateS3Export(
            client,
            enabled=False,
            bucket="private-bucket",
            owner="alice",
            endpoint="https://storage.invalid",
        )
    store = PrivateS3Export(
        client,
        enabled=True,
        bucket="private-bucket",
        owner="alice",
        endpoint="https://storage.invalid",
    )
    with pytest.raises(PermissionError):
        store.export("alice", b"fixture", upload_consent=False)
    with pytest.raises(PermissionError):
        store.export("bob", b"fixture", upload_consent=True)
    assert client.calls == []
    digest = store.export("alice", b"fixture", upload_consent=True)
    assert client.calls[-1]["ServerSideEncryption"] == "AES256"
    assert "ACL" not in client.calls[-1]
    for owner, authorized, seconds in [
        ("bob", True, 60),
        ("alice", False, 60),
        ("alice", True, 301),
    ]:
        with pytest.raises((ValueError, PermissionError)):
            store.read_url(owner, digest, authorized=authorized, seconds=seconds)
    store.read_url("alice", digest, authorized=True)
    assert client.calls[-1]["ttl"] == 60
    assert client.calls[-1]["verb"] == "GET"
    store.delete("alice", digest)
    assert client.calls[-1]["Key"] == f"private/alice/{digest}"


def test_remote_intent_and_withdrawal_survive_interrupted_sdk_calls(tmp_path: Path) -> None:
    class InterruptedClient(FakeClient):
        def put_object(self, **kwargs: object) -> object:
            super().put_object(**kwargs)
            raise OSError("connection lost after request")

        def delete_object(self, **kwargs: object) -> object:
            raise OSError("offline")

    store = LocalObjectStore(tmp_path / "objects")
    digest = store.put("alice", b"reviewed test sample")
    registry = DatasetRegistry(tmp_path / "registry.sqlite", store)
    artifact = Artifact(
        artifact_id=digest,
        participant="alice",
        route="r",
        session="s",
        scenario="test",
        license_or_consent_reference="test grant",
        redaction_reviewed=True,
        kind="SILENCE",
    )
    label = Review(
        artifact_id=digest,
        reviewer="other",
        independent=True,
        relevance="RELEVANT",
        timing="MISSED",
        motion="UNKNOWN",
        interruption="MUST_NOTIFY",
    )
    now = int(time())
    grant = ConsentGrant(
        participant="alice", purpose="MODEL_RESEARCH", granted=True, expires_at=now + 86400
    )
    version = registry.publish([artifact], [label], [grant], now)

    def adapter(client: FakeClient) -> PrivateS3Export:
        return PrivateS3Export(
            client,
            enabled=True,
            bucket="private-bucket",
            owner="alice",
            endpoint="https://storage.invalid",
        )

    with pytest.raises(OSError):
        registry.export_reviewed(version, digest, adapter(InterruptedClient()), upload_consent=True)
    assert registry.db.execute("SELECT status FROM remote_copies").fetchone()[0] == "INTENT"
    recovered = FakeClient()
    registry.export_reviewed(version, digest, adapter(recovered), upload_consent=True)
    registry.export_reviewed(version, digest, adapter(recovered), upload_consent=True)
    assert len(recovered.calls) == 1
    assert registry.db.execute("SELECT status FROM remote_copies").fetchone()[0] == "ACTIVE"
    registry.withdraw("alice")
    with pytest.raises(OSError):
        registry.reconcile_remote(adapter(InterruptedClient()))
    registry.close()
    registry = DatasetRegistry(tmp_path / "registry.sqlite", store)
    assert registry.db.execute("SELECT status FROM remote_copies").fetchone()[0] == "PENDING_DELETE"
    client = FakeClient()
    registry.reconcile_remote(adapter(client))
    assert client.calls == [{"Bucket": "private-bucket", "Key": f"private/alice/{digest}"}]
    assert (
        registry.db.execute("SELECT status FROM remote_copies").fetchone()[0]
        == "DELETE_ACKNOWLEDGED"
    )
    registry.close()
