"""A small fictional feed payload for the feed connector's tests (a trading desk with two books on one strategy),
and a feed server on 127.0.0.1 in a thread, so no test ever needs the network.

Every name and number here is made up.
"""

from __future__ import annotations

import json
import socket
import struct
import sys
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

Reply = Callable[[BaseHTTPRequestHandler], None]

MADE = "2026-09-25T21:05:00+00:00"  # three minutes before the tests' NOW
CAP = 5.0  # seconds: the longest a slow reply keeps going, so a kestrel that never gives up still gets an end
CHUNKED = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n"


def desk(**changes) -> dict:
    """The payload as JSON-ready data; keyword arguments replace its top-level fields."""
    payload = {
        "contract_version": "1",
        "generated_at": MADE,
        "sources": [{"id": "desk-broker", "label": "Broker link", "kind": "api", "status": "ok"}],
        "books": [
            {"id": "swing-real", "name": "Swing", "money": "real", "strategy_id": "swing", "status": "running",
             "started": "2026-03-02", "value": 2150.0, "slots_total": 4},
            {"id": "swing-paper", "name": "Swing (paper)", "money": "paper", "strategy_id": "swing",
             "status": "running", "started": "2026-01-05", "value": 10480.0, "slots_total": 6},
        ],
        "book_history": [
            {"id": "swing-real", "points": [{"date": "2026-09-24", "value": 2131.4},
                                            {"date": "2026-09-25", "value": 2150.0}]},
        ],
        "positions": [
            {"book_id": "swing-real", "symbol": "KO", "quantity": 5, "entry_price": 61.2, "last_price": 62.05,
             "stop_price": 56.3, "opened": "2026-09-22"},
        ],
        "trades": [
            {"book_id": "swing-real", "symbol": "PG", "opened": "2026-09-08", "closed": "2026-09-11",
             "entry_price": 158.4, "exit_price": 162.1, "quantity": 3, "pnl": 11.1, "return_pct": 2.34,
             "exit_reason": "closed above its 5-day average"},
            {"book_id": "swing-paper", "symbol": "JNJ", "opened": "2026-09-14", "closed": "2026-09-18",
             "entry_price": 171.0, "exit_price": 168.2, "quantity": 10, "pnl": -28.0, "return_pct": -1.64,
             "exit_reason": "time stop"},
        ],
        "strategies": [{"id": "swing", "name": "Swing pullbacks",
                        "summary": "Buy a dip in an uptrend; sell the bounce."}],
        "runs": [{"time": "2026-09-25T19:56:00+00:00", "label": "Evening run", "book_id": "swing-real",
                  "status": "done"}],
        "alerts": [{"level": "warning", "title": "KO is near its stop", "detail": "8.2% of room left",
                    "link": "/strategies/swing"}],
        "benchmark": {"symbol": "SPY", "label": "S&P 500", "points": [{"date": "2026-09-24", "value": 655.1},
                                                                    {"date": "2026-09-25", "value": 657.3}]},
    }
    payload.update(changes)
    return payload


def feed_file(folder: Path, payload: dict | None = None, name: str = "feed.json") -> Path:
    """The payload saved as a feed file (the desk's payload when none is given)."""
    path = folder / name
    path.write_text(json.dumps(desk() if payload is None else payload), encoding="utf-8")
    return path


class FeedServer:
    """A feed answered from a thread: `reply(handler)` writes each answer; `requests` keeps each request's method,
    path and headers (names in lower case)."""

    def __init__(self, reply: Reply) -> None:
        self.requests: list[dict[str, str]] = []
        feed = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                feed.requests.append({"method": self.command, "path": self.path,
                                      **{name.lower(): value for name, value in self.headers.items()}})
                try:
                    reply(self)
                except ConnectionError:
                    pass  # kestrel hung up first, as it should on a slow or huge answer

            def log_message(self, *args) -> None:
                pass  # keep the test output quiet

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.stop = threading.Event()  # set when the test ends, so a reply that waits returns
        self.url = f"http://127.0.0.1:{self.httpd.server_port}"
        # a short poll, so closing the server at the end of a test doesn't wait half a second
        self.thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.httpd.stop.set()
        self.httpd.shutdown()
        self.httpd.server_close()


def answer(body: bytes | dict | list, status: int = 200, headers: dict[str, str] | None = None,
           length: bool = True) -> Reply:
    """One answer: data goes as JSON; `length=False` leaves out Content-Length, so the body ends when the connection
    closes."""
    data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")

    def reply(handler: BaseHTTPRequestHandler) -> None:
        handler.send_response(status)
        for name, value in (headers or {"Content-Type": "application/json"}).items():
            handler.send_header(name, value)
        if length:
            handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)

    return reply


def hang(handler: BaseHTTPRequestHandler) -> None:
    """Never answer (until the test ends)."""
    handler.server.stop.wait(10)


def trickle(handler: BaseHTTPRequestHandler) -> None:
    """Answer at once, then send the body a byte every 50 ms, forever: each read on the socket gets something."""
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    handler.end_headers()
    handler.wfile.write(f'{{"contract_version": "1", "generated_at": "{MADE}", "note": "'.encode("utf-8"))
    while not handler.server.stop.wait(0.05):
        handler.wfile.write(b"z")


def hang_up(handler: BaseHTTPRequestHandler) -> None:
    """Close the connection without a word."""
    handler.close_connection = True


def header_trickle(handler: BaseHTTPRequestHandler) -> None:
    """A status line and one full header, then a header byte every 20 ms, forever, without ever finishing the
    headers (the blank line that ends them never comes)."""
    handler.wfile.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n")
    while not handler.server.stop.wait(0.02):
        handler.wfile.write(b"X")


def _drip(handler: BaseHTTPRequestHandler, data: bytes, seconds: float = CAP) -> None:
    """`data` a byte every 50 ms, round and round, for `seconds` (or until the test ends)."""
    until, i = time.monotonic() + seconds, 0
    while time.monotonic() < until and not handler.server.stop.wait(0.05):
        handler.wfile.write(data[i % len(data):i % len(data) + 1])
        i += 1


def chunk_size_trickle(handler: BaseHTTPRequestHandler) -> None:
    """The headers of a chunked answer, then a chunk-size line a byte every 50 ms that never ends."""
    handler.wfile.write(CHUNKED + b"1")
    _drip(handler, b"0")


def trailer_trickle(handler: BaseHTTPRequestHandler) -> None:
    """A whole chunked body (the desk's payload) and the last chunk, then trailer lines a byte every 50 ms: the blank
    line that ends them never comes."""
    body = json.dumps(desk()).encode("utf-8")
    handler.wfile.write(CHUNKED + f"{len(body):x}\r\n".encode("ascii") + body + b"\r\n0\r\n")
    _drip(handler, b"X-Trailer: 1\r\n")


def slow_head_then_body(handler: BaseHTTPRequestHandler) -> None:
    """Headers that take 0.7 s, a body that takes 0.9 s more, then silence: each part fits a 1 s timeout on its own;
    together they don't."""
    handler.wfile.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 1000\r\nX-Pad: ")
    _drip(handler, b"a", 0.7)
    handler.wfile.write(b"\r\n\r\n")
    _drip(handler, b"z", 0.9)
    handler.server.stop.wait(CAP)


def chunked_cut_off(handler: BaseHTTPRequestHandler) -> None:
    """A chunk that promises 16 bytes, five of them, then the connection closes."""
    handler.wfile.write(CHUNKED + b'10\r\n{"con')


def reset_midway(handler: BaseHTTPRequestHandler) -> None:
    """Part of a body, then the connection is reset (a TCP RST: SO_LINGER with no wait, then close)."""
    handler.wfile.write(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 1000\r\n\r\n{"con')
    handler.server.stop.wait(0.3)  # long enough for kestrel to be waiting on the rest of the body
    linger = struct.pack("HH", 1, 0) if sys.platform == "win32" else struct.pack("ii", 1, 0)
    handler.connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)
    handler.connection.close()


class RawServer:
    """A server on 127.0.0.1 that hands each connection's socket to `serve(conn, stop)`: for answers an HTTP server
    can't give, such as a TLS handshake that never finishes."""

    def __init__(self, serve: Callable[[socket.socket, threading.Event], None]) -> None:
        self.listener = socket.create_server(("127.0.0.1", 0))
        self.listener.settimeout(0.02)
        self.stop = threading.Event()
        self.port = self.listener.getsockname()[1]
        self.thread = threading.Thread(target=self._run, args=(serve,), daemon=True)
        self.thread.start()

    def _run(self, serve: Callable[[socket.socket, threading.Event], None]) -> None:
        while not self.stop.is_set():
            try:
                conn, _ = self.listener.accept()
            except OSError:  # the accept timed out: look at stop again
                continue
            with conn:
                try:
                    serve(conn, self.stop)
                except OSError:
                    pass  # kestrel hung up first

    def close(self) -> None:
        self.stop.set()
        self.thread.join(CAP + 1)
        self.listener.close()


def tls_trickle(conn: socket.socket, stop: threading.Event) -> None:
    """Read the client's hello, then start a 16 KB handshake record and send it a byte every 50 ms."""
    conn.settimeout(CAP)
    conn.recv(4096)
    conn.sendall(b"\x16\x03\x03\x40\x00")  # a handshake record in TLS 1.2 framing, 16,384 bytes long
    until = time.monotonic() + CAP
    while time.monotonic() < until and not stop.wait(0.05):
        conn.sendall(b"\x00")
