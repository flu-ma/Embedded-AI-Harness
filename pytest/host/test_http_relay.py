"""Host tier for FR-014's follow_redirects field. Pure logic only."""
import urllib.request

import pytest

import wifi_controller as wc


def test_fr014_follow_redirects_defaults_to_true():
    assert wc.parse_follow_redirects(None) is True


@pytest.mark.parametrize("v", [True, False])
def test_fr014_follow_redirects_takes_a_bool(v):
    assert wc.parse_follow_redirects(v) is v


@pytest.mark.parametrize("v", ["no", "false", 0, 1, [], {}])
def test_fr014_follow_redirects_rejects_anything_else(v):
    with pytest.raises(ValueError, match="follow_redirects"):
        wc.parse_follow_redirects(v)


def _redirect_handlers(opener):
    return [h for h in opener.handlers if isinstance(h, urllib.request.HTTPRedirectHandler)]


def test_fr014_no_follow_opener_stops_at_a_3xx():
    hs = _redirect_handlers(wc.relay_opener(False))
    assert hs, "no redirect handler installed"
    req = urllib.request.Request("http://192.168.4.1/generate_204")
    for code in (301, 302, 303, 307, 308):
        assert all(h.redirect_request(req, None, code, "", {}, "http://192.168.4.1/") is None for h in hs)


def test_fr014_default_opener_still_follows():
    hs = _redirect_handlers(wc.relay_opener(True))
    req = urllib.request.Request("http://192.168.4.1/generate_204")
    assert any(h.redirect_request(req, None, 302, "", {}, "http://192.168.4.1/") is not None for h in hs)
