"""Network denial for fixture-mode runs (T-06 slice 2).

A fixture run must not reach any network: no model, no name lookup, no connection. Inside
`deny_network()` this process's name resolution and socket connections raise `NetworkDenied`
before anything reaches the operating system. It covers Python-level networking in this process
(the standard library, and clients built on it); it is not a sandbox and does not govern other
processes (the Docker CLI the isolated runner starts talks to the local daemon on its own).
"""

import socket
from contextlib import contextmanager


class NetworkDenied(OSError):
    pass


def _denied(*args, **kwargs):
    raise NetworkDenied("network access is denied in fixture mode")


@contextmanager
def deny_network():
    saved = {
        "connect": socket.socket.connect,
        "connect_ex": socket.socket.connect_ex,
        "getaddrinfo": socket.getaddrinfo,
        "create_connection": socket.create_connection,
    }
    socket.socket.connect = _denied
    socket.socket.connect_ex = _denied
    socket.getaddrinfo = _denied
    socket.create_connection = _denied
    try:
        yield
    finally:
        socket.socket.connect = saved["connect"]
        socket.socket.connect_ex = saved["connect_ex"]
        socket.getaddrinfo = saved["getaddrinfo"]
        socket.create_connection = saved["create_connection"]
