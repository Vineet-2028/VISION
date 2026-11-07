from concurrent.futures import ThreadPoolExecutor

import pytest

from perception_lab.field_pairing import PairingAuthority


def test_pairing_is_single_use_expiring_and_rotation_revokes() -> None:
    authority = PairingAuthority()
    old = authority.issue(0)
    fresh = authority.issue(1)
    with pytest.raises(ValueError):
        authority.exchange(old, 2)
    device = authority.exchange(fresh, 2)
    token = authority.mint(device, 2)
    with pytest.raises(ValueError):
        authority.exchange(fresh, 2)
    assert authority.authorize(token, None, 3)
    authority.bind(token, "session-1")
    assert authority.authorize(token, "session-1", 3)
    assert not authority.authorize(token, "session-2", 3)
    with pytest.raises(ValueError):
        authority.bind(token, "session-2")
    assert not authority.authorize(token, "session-1", 3602)
    code = authority.issue(10)
    with pytest.raises(ValueError):
        authority.exchange(code, 130)


def test_concurrent_exchange_has_exactly_one_winner() -> None:
    authority = PairingAuthority()
    code = authority.issue(0)

    def claim(_: int) -> bool:
        try:
            authority.exchange(code, 1)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(claim, range(16))) == 1
    authority.revoke()
    assert not authority.grants
