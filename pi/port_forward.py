"""FR-044: forward a bench LAN port to a device on the bench's WiFi network.

Lets a browser or script on the LAN reach a DUT that only the bench can see
(192.168.4.x behind the bench SoftAP). One TCP relay per listen port, plain
byte copying in both directions; nothing is parsed.
"""

import ipaddress
import socket
import threading

LISTEN_MIN, LISTEN_MAX = 8100, 8199


def validate(body: dict) -> tuple[str, int, int]:
    """(target_ip, target_port, listen_port) from a request; ValueError naming the field."""
    try:
        ip = ipaddress.ip_address(str(body.get("target_ip", "")))
    except ValueError:
        raise ValueError("target_ip must be an IPv4 address")
    if ip.version != 4 or not ip.is_private:
        raise ValueError("target_ip must be a private IPv4 address")
    try:
        tport = int(body.get("target_port", 80))
        lport = int(body.get("listen_port", LISTEN_MIN))
    except (TypeError, ValueError):
        raise ValueError("target_port and listen_port must be integers")
    if not 1 <= tport <= 65535:
        raise ValueError("target_port must be 1–65535")
    if not LISTEN_MIN <= lport <= LISTEN_MAX:
        raise ValueError(f"listen_port must be {LISTEN_MIN}–{LISTEN_MAX}")
    return str(ip), tport, lport


def _pipe(src: socket.socket, dst: socket.socket) -> None:
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for s in (src, dst):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


class Forward:
    def __init__(self, target_ip: str, target_port: int, listen_port: int):
        self.target = (target_ip, target_port)
        self.listen_port = listen_port
        self.connections = 0
        self._srv = socket.create_server(("0.0.0.0", listen_port), reuse_port=False)
        self._srv.settimeout(1.0)
        self._stop = threading.Event()
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self) -> None:
        while not self._stop.is_set():
            try:
                client, _ = self._srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                upstream = socket.create_connection(self.target, timeout=5)
                upstream.settimeout(None)
            except OSError:
                client.close()
                continue
            self.connections += 1
            threading.Thread(target=_pipe, args=(client, upstream), daemon=True).start()
            threading.Thread(target=_pipe, args=(upstream, client), daemon=True).start()
        self._srv.close()

    def stop(self) -> None:
        self._stop.set()

    def status(self) -> dict:
        return {"listen_port": self.listen_port, "target_ip": self.target[0],
                "target_port": self.target[1], "connections": self.connections}


class Forwards:
    def __init__(self):
        self._lock = threading.Lock()
        self._by_port: dict[int, Forward] = {}

    def start(self, target_ip: str, target_port: int, listen_port: int) -> dict:
        with self._lock:
            old = self._by_port.pop(listen_port, None)
            if old:
                old.stop()
            f = Forward(target_ip, target_port, listen_port)
            self._by_port[listen_port] = f
            return f.status()

    def stop(self, listen_port: int | None = None) -> list[dict]:
        with self._lock:
            ports = [listen_port] if listen_port is not None else list(self._by_port)
            out = []
            for p in ports:
                f = self._by_port.pop(p, None)
                if f:
                    f.stop()
                    out.append(f.status())
            return out

    def status(self) -> list[dict]:
        with self._lock:
            return [f.status() for f in self._by_port.values()]


forwards = Forwards()
