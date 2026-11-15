"""FR-043: an HTTP request whose body is cut off mid-transfer.

The request head announces the full body (Content-Length), only the first
`abort_after` bytes follow, then the connection is closed — what a DUT sees
when a client dies during an upload.
"""

import socket
import time
from urllib.parse import urlsplit


def request_head(method: str, url: str, headers: dict | None, body_len: int) -> tuple[str, int, bytes]:
    """(host, port, head bytes) for an HTTP/1.1 request announcing body_len."""
    u = urlsplit(url)
    if u.scheme != "http" or not u.hostname:
        raise ValueError("url must be http://host[:port]/path")
    path = (u.path or "/") + (f"?{u.query}" if u.query else "")
    lines = [f"{method.upper()} {path} HTTP/1.1", f"Host: {u.netloc}",
             f"Content-Length: {body_len}", "Connection: close"]
    for k, v in (headers or {}).items():
        if k.lower() in ("host", "content-length", "connection"):
            continue
        if any(c in f"{k}{v}" for c in "\r\n"):
            raise ValueError("header names and values must not contain CR or LF")
        lines.append(f"{k}: {v}")
    return u.hostname, u.port or 80, ("\r\n".join(lines) + "\r\n\r\n").encode()


def check_cut(body_len: int, abort_after: int) -> None:
    if not 0 <= abort_after < body_len:
        raise ValueError("abort_after must be ≥ 0 and less than the body length")


def send_cut(method: str, url: str, headers: dict | None, body: bytes, abort_after: int,
             pause_ms: int = 500, timeout: float = 30) -> dict:
    """Send the head and body[:abort_after], wait pause_ms, close. Returns what was sent."""
    check_cut(len(body), abort_after)
    host, port, head = request_head(method, url, headers, len(body))
    t0 = time.monotonic()
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall(head)
        sent = 0
        while sent < abort_after:
            n = s.send(body[sent:min(abort_after, sent + 4096)])
            sent += n
        time.sleep(max(0, pause_ms) / 1000)
        s.shutdown(socket.SHUT_RDWR)
    return {"sent": sent, "of": len(body), "closed_after_ms": int((time.monotonic() - t0) * 1000)}
