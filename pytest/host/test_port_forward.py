"""FR-044: request validation and a loopback relay round trip."""
import socket
import threading
import time

import pytest

import port_forward as pf


def test_validate_defaults_and_fields():
    assert pf.validate({"target_ip": "192.168.4.6"}) == ("192.168.4.6", 80, 8100)
    assert pf.validate({"target_ip": "192.168.4.6", "target_port": 8080, "listen_port": 8199})[1:] == (8080, 8199)


@pytest.mark.parametrize("body,field", [
    ({"target_ip": "x"}, "target_ip"), ({"target_ip": "8.8.8.8"}, "target_ip"),
    ({"target_ip": "192.168.4.6", "target_port": 0}, "target_port"),
    ({"target_ip": "192.168.4.6", "listen_port": 8080}, "listen_port"),
    ({"target_ip": "192.168.4.6", "listen_port": "a"}, "listen_port"),
])
def test_validate_rejects(body, field):
    with pytest.raises(ValueError, match=field):
        pf.validate(body)


def test_relay_round_trip():
    echo = socket.create_server(("127.0.0.1", 0))
    eport = echo.getsockname()[1]

    def serve():
        c, _ = echo.accept()
        data = c.recv(1024)
        c.sendall(b"echo:" + data)
        c.close()
    threading.Thread(target=serve, daemon=True).start()
    fw = pf.Forwards()
    st = fw.start("127.0.0.1", eport, 8187)
    assert st["listen_port"] == 8187
    with socket.create_connection(("127.0.0.1", 8187), timeout=5) as s:
        s.sendall(b"hello")
        got = b""
        while not got.endswith(b"hello"):
            chunk = s.recv(1024)
            if not chunk:
                break
            got += chunk
    assert got == b"echo:hello"
    assert fw.status()[0]["connections"] == 1
    assert fw.stop(8187)[0]["listen_port"] == 8187 and fw.status() == []
    echo.close()
