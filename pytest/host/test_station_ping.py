"""Host tier for FR-041 station ping. Pure logic only."""
import pytest

import station_ping as sp


def test_fr041_valid_body():
    assert sp.validate({"host": "192.168.4.1", "interval_ms": 100, "duration_s": 180}) == ("192.168.4.1", 100, 180)


@pytest.mark.parametrize("body,field", [
    ({"interval_ms": 100}, "host"), ({"host": "dut.local"}, "host"),
    ({"host": "192.168.4.1", "interval_ms": 10}, "interval_ms"),
    ({"host": "192.168.4.1", "interval_ms": "100"}, "interval_ms"),
    ({"host": "192.168.4.1", "duration_s": 601}, "duration_s"),
    ({"host": "192.168.4.1", "duration_s": True}, "duration_s"),
])
def test_fr041_rejects(body, field):
    with pytest.raises(ValueError, match=field):
        sp.validate(body)


def test_fr041_count_and_command():
    assert sp.count_for(100, 180) == 1800
    cmd = sp.command("wlan0", "192.168.4.1", 100, 1800)
    assert cmd[cmd.index("-i") + 1] == "0.100" and cmd[cmd.index("-c") + 1] == "1800"
    assert cmd[cmd.index("-I") + 1] == "wlan0" and cmd[-1] == "192.168.4.1"


def test_fr041_parses_replies_only():
    out = ["PING 192.168.4.1 (192.168.4.1) from 192.168.4.2 wlan0: 56(84) bytes of data.",
           "64 bytes from 192.168.4.1: icmp_seq=1 ttl=255 time=3.12 ms",
           "64 bytes from 192.168.4.1: icmp_seq=4 ttl=255 time=2.80 ms",
           "From 192.168.4.2 icmp_seq=2 Destination Host Unreachable",
           "--- 192.168.4.1 ping statistics ---"]
    assert sp.replies(out) == {1, 4}


def test_fr041_longest_loss_run():
    s = sp.summary({1, 2, 6, 7, 8, 10}, 10, 100)
    assert s == {"sent": 10, "received": 6, "lost": 4, "longest_loss_run": 3, "longest_loss_ms": 300}
    assert sp.summary(set(range(1, 11)), 10, 100)["longest_loss_run"] == 0
    assert sp.summary(set(), 5, 100)["longest_loss_ms"] == 500   # nothing answered: the whole run
