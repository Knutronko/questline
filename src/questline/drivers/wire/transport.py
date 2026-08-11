"""QuestlineWire transport — real TCP NDJSON or a test double."""

from __future__ import annotations

import socket
import threading
import uuid
from typing import Any, Protocol, runtime_checkable

from questline.core.errors import InfraError, SessionLostError
from questline.drivers.port import ConnectionTarget
from questline.drivers.wire.errors import error_from_server, map_wire_error
from questline.drivers.wire.protocol import make_request, parse_response


@runtime_checkable
class WireTransport(Protocol):
    """Minimal request/response transport used by QuestlineDriver."""

    def request(self, op: str, params: dict[str, Any] | None = None) -> Any: ...

    def close(self) -> None: ...


class TcpWireTransport:
    """Real TCP + NDJSON client (one request → one response line).

    ``request`` is serialized with a lock so concurrent callers (e.g. PerfProbe
    background sampler + test thread) cannot interleave lines on the socket.
    """

    def __init__(
        self,
        sock: socket.socket,
        *,
        recv_timeout_s: float = 30.0,
    ) -> None:
        self._sock = sock
        self._sock.settimeout(recv_timeout_s)
        self._buffer = b""
        self._closed = False
        self._lock = threading.Lock()

    def request(self, op: str, params: dict[str, Any] | None = None) -> Any:
        with self._lock:
            return self._request_unlocked(op, params)

    def _request_unlocked(self, op: str, params: dict[str, Any] | None = None) -> Any:
        if self._closed:
            raise SessionLostError("wire transport closed", kind="disposed")
        req_id = uuid.uuid4().hex
        line = make_request(op, params, req_id=req_id) + "\n"
        try:
            self._sock.sendall(line.encode("utf-8"))
            raw = self._readline()
        except Exception as exc:
            self._alive_clear()
            raise map_wire_error(exc) from exc
        try:
            data = parse_response(raw)
        except Exception as exc:
            raise map_wire_error(exc) from exc
        resp_id = data.get("id")
        if resp_id is not None and str(resp_id) != req_id:
            self._alive_clear()
            raise SessionLostError(
                f"wire response id mismatch (concurrent clients on one socket?): "
                f"sent {req_id}, got {resp_id!r} for op={op!r}",
                kind="protocol",
            )
        if not data.get("ok", False):
            err = data.get("error") or {}
            code = str(err.get("code", "infra"))
            message = str(err.get("message", "wire request failed"))
            raise error_from_server(code, message)
        return data.get("result")

    def close(self) -> None:
        self._closed = True
        try:
            self._sock.close()
        except OSError:
            pass

    def _alive_clear(self) -> None:
        self._closed = True
        try:
            self._sock.close()
        except OSError:
            pass

    def _readline(self) -> str:
        while True:
            nl = self._buffer.find(b"\n")
            if nl >= 0:
                line = self._buffer[:nl]
                self._buffer = self._buffer[nl + 1 :]
                return line.decode("utf-8")
            chunk = self._sock.recv(4096)
            if not chunk:
                raise SessionLostError("wire connection closed by peer", kind="disconnect")
            self._buffer += chunk


def connect_real_transport(target: ConnectionTarget) -> WireTransport:
    """Open a TCP session to the companion Wire listener."""
    host = target.host or "127.0.0.1"
    port = int(target.port)
    timeout_raw = target.extras.get("connect_timeout", "30")
    try:
        timeout = float(timeout_raw)
    except ValueError as exc:
        raise InfraError(f"invalid connect_timeout {timeout_raw!r}") from exc

    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except Exception as exc:
        raise map_wire_error(exc) from exc

    transport = TcpWireTransport(sock, recv_timeout_s=timeout)
    # Handshake — proves the peer speaks Wire.
    try:
        hello = transport.request("hello")
    except Exception:
        transport.close()
        raise
    if not isinstance(hello, dict):
        transport.close()
        raise InfraError("wire hello result must be an object")
    return transport
