"""Single-use physical QR bootstrap and scoped, expiring bearer grants.

State is memory-only: restarting the gateway revokes all grants and pairing codes.
The QR fingerprint must be obtained from the trusted operator screen, not the LAN.
"""

import hashlib
import secrets
import threading
from dataclasses import dataclass
from time import monotonic


@dataclass
class Grant:
    expires: float
    session_id: str | None = None


class PairingAuthority:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.code_hash: str | None = None
        self.code_expires = 0.0
        self.grants: dict[str, Grant] = {}
        self.device_hash: str | None = None
        self.device_expires = 0.0

    def issue(self, now: float | None = None) -> str:
        now = monotonic() if now is None else now
        code = secrets.token_urlsafe(32)
        with self.lock:
            self.code_hash = self.digest(code)
            self.code_expires = now + 120
        return code

    @staticmethod
    def digest(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    def exchange(self, code: str, now: float | None = None) -> str:
        now = monotonic() if now is None else now
        with self.lock:
            if (
                self.code_hash is None
                or now >= self.code_expires
                or not secrets.compare_digest(self.digest(code), self.code_hash)
            ):
                raise ValueError("PAIRING_EXPIRED_OR_INVALID")
            self.code_hash = None
            # One paired phone at a time. Re-pairing revokes the previous grant.
            self.grants.clear()
            token = secrets.token_urlsafe(32)
            self.device_hash = self.digest(token)
            self.device_expires = now + 30 * 86400
            return token

    def mint(self, device_key: str, now: float | None = None) -> str:
        now = monotonic() if now is None else now
        with self.lock:
            if (
                not self.device_hash
                or now >= self.device_expires
                or not secrets.compare_digest(self.digest(device_key), self.device_hash)
            ):
                raise ValueError("PAIR_AGAIN")
            self.grants.clear()
            token = secrets.token_urlsafe(32)
            self.grants[self.digest(token)] = Grant(now + 3600)
            return token

    def authorize(self, token: str, session_id: str | None, now: float | None = None) -> bool:
        now = monotonic() if now is None else now
        with self.lock:
            key = self.digest(token)
            grant = self.grants.get(key)
            if not grant or now >= grant.expires:
                self.grants.pop(key, None)
                return False
            return grant.session_id is None or grant.session_id == session_id

    def bind(self, token: str, session_id: str) -> None:
        with self.lock:
            grant = self.grants.get(self.digest(token))
            if not grant or grant.session_id is not None:
                raise ValueError("GRANT_ALREADY_BOUND")
            grant.session_id = session_id

    def release_session(self, token: str) -> None:
        # A finished/disconnected session cannot reuse its credential.
        with self.lock:
            self.grants.pop(self.digest(token), None)

    def revoke(self) -> None:
        with self.lock:
            self.grants.clear()
            self.code_hash = None
            self.device_hash = None
