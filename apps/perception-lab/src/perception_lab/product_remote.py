"""Opt-in S3-compatible research adapter. No client creation, discovery or auto-upload.

The caller supplies a narrowly scoped, SigV4-configured SDK client after separate
authorization. This adapter is deliberately not wired into the phone or Guardian.
"""

import hashlib
import re
from typing import Protocol
from urllib.parse import urlsplit


class SDKConfig(Protocol):
    @property
    def signature_version(self) -> str: ...


class ClientMeta(Protocol):
    @property
    def endpoint_url(self) -> str: ...

    @property
    def config(self) -> SDKConfig: ...


class S3Client(Protocol):
    @property
    def meta(self) -> ClientMeta: ...

    def put_object(self, **kwargs: object) -> object: ...
    def delete_object(self, **kwargs: object) -> object: ...
    def generate_presigned_url(
        self, ClientMethod: str, Params: dict[str, object], ExpiresIn: int, HttpMethod: str
    ) -> str: ...


class PrivateS3Export:
    """Explicit export of bounded metadata or consent-reviewed research objects.

    Not an HTTP authorization service. The owner must come from the future trusted
    account boundary, never from an untrusted request's owner field. No public ACLs,
    signed uploads or remote inference. Cloud integration remains an acceptance gate.
    """

    def __init__(
        self, client: S3Client, *, enabled: bool, bucket: str, owner: str, endpoint: str
    ) -> None:
        if not enabled:
            raise ValueError("Remote storage is disabled")
        address = urlsplit(endpoint)
        if (
            address.scheme != "https"
            or not address.hostname
            or address.username
            or address.password
            or address.query
            or address.fragment
        ):
            raise ValueError("Explicit HTTPS storage endpoint required")
        if client.meta.endpoint_url.rstrip("/") != endpoint.rstrip("/"):
            raise ValueError("SDK endpoint differs from the authorized destination")
        if client.meta.config.signature_version != "s3v4":
            raise ValueError("Signature Version 4 required")
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket):
            raise ValueError("Invalid private bucket")
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", owner):
            raise ValueError("Invalid owner")
        self.client, self.bucket, self.owner = client, bucket, owner
        self.destination = hashlib.sha256(f"{endpoint.rstrip('/')}\n{bucket}".encode()).hexdigest()

    def _key(self, owner: str, digest: str) -> str:
        if owner != self.owner or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise PermissionError("Object outside authorized owner scope")
        return f"private/{self.owner}/{digest}"

    def export(self, owner: str, data: bytes, *, upload_consent: bool) -> str:
        if not upload_consent:
            raise PermissionError("Separate explicit upload consent required")
        if not 0 < len(data) <= 10 * 1024**2:
            raise ValueError("Object quota")
        digest = hashlib.sha256(data).hexdigest()
        self.client.put_object(
            Bucket=self.bucket,
            Key=self._key(owner, digest),
            Body=data,
            ContentType="application/octet-stream",
            ServerSideEncryption="AES256",
            Metadata={"sha256": digest},
        )
        return digest

    def read_url(self, owner: str, digest: str, *, authorized: bool, seconds: int = 60) -> str:
        if not authorized:
            raise PermissionError("Read authorization required")
        if not 1 <= seconds <= 300:
            raise ValueError("Signed URL lifetime must be 1..300 seconds")
        return self.client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self.bucket, "Key": self._key(owner, digest)},
            ExpiresIn=seconds,
            HttpMethod="GET",
        )

    def delete(self, owner: str, digest: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=self._key(owner, digest))
