"""Station ping (FR-041): ping a host from the bench station at a fixed
interval for a fixed time, and report how many replies were lost and the
longest run of consecutive losses — the way to show that a DUT's AP keeps
serving its clients while the DUT does something else with its radio.

Pure logic plus one background runner; the portal does the HTTP.
"""
import ipaddress
import re
import subprocess
import threading
import time

INTERVAL_MS = (20, 1000)
DURATION_S = (1, 600)
_REPLY = re.compile(r"icmp_seq=(\d+)\b.*\btime=")


def validate(body):
    """Request body → (host, interval_ms, duration_s). ValueError naming the field."""
    host = body.get("host")
    try:
        ipaddress.IPv4Address(host)
    except (ipaddress.AddressValueError, TypeError, ValueError):
        raise ValueError("host must be an IPv4 address")
    iv, du = body.get("interval_ms", 100), body.get("duration_s", 60)
    if not isinstance(iv, int) or isinstance(iv, bool) or not INTERVAL_MS[0] <= iv <= INTERVAL_MS[1]:
        raise ValueError(f"interval_ms must be an integer {INTERVAL_MS[0]}–{INTERVAL_MS[1]}")
    if not isinstance(du, int) or isinstance(du, bool) or not DURATION_S[0] <= du <= DURATION_S[1]:
        raise ValueError(f"duration_s must be an integer {DURATION_S[0]}–{DURATION_S[1]}")
    return host, iv, du


def count_for(interval_ms, duration_s):
    return max(1, duration_s * 1000 // interval_ms)


def command(iface, host, interval_ms, count):
    return ["ping", "-n", "-I", iface, "-i", f"{interval_ms / 1000:.3f}", "-c", str(count), "-W", "1", host]


def replies(lines):
    """Sequence numbers (1-based, as iputils counts) of the echo replies in ping's output."""
    return {int(m.group(1)) for m in map(_REPLY.search, lines) if m}


def summary(received, sent, interval_ms):
    """Losses among requests 1…sent, and the longest run of consecutive losses."""
    longest = run = 0
    for seq in range(1, sent + 1):
        run = 0 if seq in received else run + 1
        longest = max(longest, run)
    got = len([s for s in received if 1 <= s <= sent])
    return {"sent": sent, "received": got, "lost": sent - got,
            "longest_loss_run": longest, "longest_loss_ms": longest * interval_ms}


class Runner:
    """One ping run at a time, in the background."""

    def __init__(self):
        self._lock = threading.Lock()
        self._proc = None
        self._lines = []
        self._job = None

    def start(self, iface, host, interval_ms, duration_s):
        with self._lock:
            if self._proc and self._proc.poll() is None:
                raise RuntimeError("a station ping is already running")
            count = count_for(interval_ms, duration_s)
            self._lines = []
            self._job = {"host": host, "interval_ms": interval_ms, "count": count, "started": time.time()}
            self._proc = subprocess.Popen(command(iface, host, interval_ms, count), stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT, text=True)
            threading.Thread(target=self._read, args=(self._proc,), daemon=True).start()
            return dict(self._job)

    def _read(self, proc):
        for line in proc.stdout:
            with self._lock:
                self._lines.append(line)

    def status(self):
        with self._lock:
            if not self._job:
                return {"running": False}
            running = self._proc.poll() is None
            job, iv = self._job, self._job["interval_ms"]
            got = replies(self._lines)
            if running:      # requests so far: by time, never past the last answered one + 1 s of grace
                sent = min(job["count"], int((time.time() - job["started"]) * 1000 // iv))
                sent = max(0, min(sent, max(got, default=0) + 1000 // iv))
            else:
                sent = job["count"]
            out = {"running": running, "host": job["host"], "interval_ms": iv, **summary(got, sent, iv)}
            if not running and self._proc.returncode not in (0, 1):   # 1 = some replies missing
                out["error"] = "".join(self._lines[-3:]).strip() or f"ping exited {self._proc.returncode}"
            return out

    def stop(self):
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()


runner = Runner()
