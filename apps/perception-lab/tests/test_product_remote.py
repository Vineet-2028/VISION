from types import SimpleNamespace

import pytest

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
