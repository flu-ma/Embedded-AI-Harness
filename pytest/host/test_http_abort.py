"""FR-043: request head and cut checks for the cut-off upload."""
import pytest

import http_abort


def test_head_announces_full_body():
    host, port, head = http_abort.request_head("post", "http://192.168.4.6/api/ota/upload?x=1",
                                               {"Authorization": "Basic YQ==", "Content-Length": "1"}, 1000)
    assert (host, port) == ("192.168.4.6", 80)
    text = head.decode()
    assert text.startswith("POST /api/ota/upload?x=1 HTTP/1.1\r\n")
    assert "Content-Length: 1000\r\n" in text and "Content-Length: 1\r\n" not in text
    assert "Authorization: Basic YQ==\r\n" in text and text.endswith("\r\n\r\n")


def test_port_and_rejections():
    assert http_abort.request_head("PUT", "http://10.0.0.1:8080", None, 1)[:2] == ("10.0.0.1", 8080)
    with pytest.raises(ValueError):
        http_abort.request_head("POST", "https://x/", None, 1)
    with pytest.raises(ValueError):
        http_abort.request_head("POST", "http://x/", {"X": "a\r\nB: c"}, 1)


@pytest.mark.parametrize("cut,ok", [(0, True), (500, True), (999, True), (1000, False), (-1, False)])
def test_cut_bounds(cut, ok):
    if ok:
        http_abort.check_cut(1000, cut)
    else:
        with pytest.raises(ValueError):
            http_abort.check_cut(1000, cut)
