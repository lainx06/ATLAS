"""Network guard for fixture-mode runs (T-06 slice 2).

A fixture run has no reason to use a network. Inside `deny_network()`, Python-level networking in
**this process** raises `NetworkDenied` before anything reaches the operating system:

- connecting: `socket.socket.connect`, `connect_ex` and `socket.create_connection`;
- sending: `socket.socket.send`, `sendall`, `sendto`, `sendmsg` (where it exists) and
  `sendfile`. These are patched on the class, so they also apply to sockets created before the
  guard (for example a connected socket or a UDP socket);
- name and address resolution: `getaddrinfo`, `gethostbyname`, `gethostbyname_ex`,
  `gethostbyaddr` and `getnameinfo`.

Every patch is restored when the context ends, after success or an exception.

**Scope.** This is an in-process safeguard for fixture tests, not a security sandbox. It does not
govern other processes (the Docker CLI that the isolated runner starts talks to the local
daemon on its own), raw use of the private `_socket` module, or native code that bypasses
Python's `socket` module. It is not evidence that no network traffic occurred.
"""

import socket
from contextlib import contextmanager


class NetworkDenied(OSError):
    pass


def _denied(*args, **kwargs):
    raise NetworkDenied("network access is denied in fixture mode")


SOCKET_METHODS = (
    "connect",
    "connect_ex",
    "send",
    "sendall",
    "sendto",
    "sendmsg",
    "sendfile",
)
MODULE_FUNCTIONS = (
    "create_connection",
    "getaddrinfo",
    "gethostbyname",
    "gethostbyname_ex",
    "gethostbyaddr",
    "getnameinfo",
)


@contextmanager
def deny_network():
    saved_methods = {
        name: socket.socket.__dict__.get(name, _MISSING)
        for name in SOCKET_METHODS
        if hasattr(socket.socket, name)
    }
    saved_functions = {name: getattr(socket, name) for name in MODULE_FUNCTIONS}
    try:
        for name in saved_methods:
            setattr(socket.socket, name, _denied)
        for name in saved_functions:
            setattr(socket, name, _denied)
        yield
    finally:
        for name, original in saved_methods.items():
            if original is _MISSING:
                delattr(socket.socket, name)  # inherited from the C base class again
            else:
                setattr(socket.socket, name, original)
        for name, original in saved_functions.items():
            setattr(socket, name, original)


_MISSING = object()
