"""Paced file serving for the OTA firmware repository (FR-021 `rate`).

A firmware download normally finishes in seconds; a test that needs an OTA
to stay in progress (a DUT's behaviour during a transfer, a second request
while one runs) asks for it to be served at a fixed byte rate instead.
Pure logic: the portal does the I/O.
"""

RATE_MIN = 1000            # bytes/s; slower would trip a typical client's read timeout
RATE_MAX = 10_000_000


def parse_rate(value):
    """`rate` query value → bytes/s, or None when absent. ValueError otherwise."""
    if value is None:
        return None
    try:
        rate = int(value, 10)
    except (TypeError, ValueError):
        raise ValueError(f"rate must be an integer {RATE_MIN}–{RATE_MAX} (bytes/s)")
    if not RATE_MIN <= rate <= RATE_MAX:
        raise ValueError(f"rate must be an integer {RATE_MIN}–{RATE_MAX} (bytes/s)")
    return rate


def chunk_size(rate):
    """Bytes per write: about four writes a second, never above 8 KiB."""
    if rate is None:
        return 8192
    return max(256, min(8192, rate // 4))


def delay(start, sent, rate, now):
    """Seconds to wait before the next write so `sent` bytes take sent/rate s."""
    if rate is None:
        return 0.0
    return max(0.0, start + sent / rate - now)
