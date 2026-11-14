"""Host tier for FR-021 paced serving. Pure logic only."""
import pytest

import throttle


def test_fr021_rate_absent_means_unpaced():
    assert throttle.parse_rate(None) is None
    assert throttle.delay(0.0, 10**6, None, 0.0) == 0.0
    assert throttle.chunk_size(None) == 8192


@pytest.mark.parametrize("v,want", [("1000", 1000), ("20000", 20000), ("10000000", 10_000_000)])
def test_fr021_rate_in_range(v, want):
    assert throttle.parse_rate(v) == want


@pytest.mark.parametrize("v", ["999", "10000001", "0", "-5", "fast", "", "1e4", "20000.5"])
def test_fr021_rate_rejected(v):
    with pytest.raises(ValueError, match="rate"):
        throttle.parse_rate(v)


@pytest.mark.parametrize("rate", [1000, 20000, 10_000_000])
def test_fr021_chunks_at_most_8k_and_several_per_second(rate):
    c = throttle.chunk_size(rate)
    assert 0 < c <= 8192
    assert c <= max(256, rate // 4)


def test_fr021_pacing_is_cumulative():
    # 1 MB at 20 kB/s takes 50 s: simulate writes with instant I/O.
    rate, size, now, sent = 20000, 10**6, 100.0, 0
    c = throttle.chunk_size(rate)
    while sent < size:
        sent += min(c, size - sent)
        now += throttle.delay(100.0, sent, rate, now)
    assert now - 100.0 == pytest.approx(size / rate)


def test_fr021_no_wait_when_behind():
    # A slow link that already took longer than the rate allows gets no extra delay.
    assert throttle.delay(0.0, 20000, 20000, 5.0) == 0.0
