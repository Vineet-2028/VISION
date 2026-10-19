"""Process-wide Python network denial for explicitly local model workers.

This is not an OS sandbox: native code can bypass Python audit hooks. Use trusted
weights and an OS network policy for hostile-code isolation. Install before vendor imports.
"""

import sys

_installed = False


def enforce_offline() -> None:
    global _installed
    if _installed:
        return

    def deny_network(event: str, args: tuple[object, ...]) -> None:
        if event in {
            "socket.connect",
            "socket.getaddrinfo",
            "socket.gethostbyname",
            "socket.gethostbyaddr",
            "socket.sendto",
            "socket.sendmsg",
            "urllib.Request",
        }:
            raise OSError("NETWORK_DISABLED_FOR_LOCAL_MODEL_WORKER")

    sys.addaudithook(deny_network)
    _installed = True
