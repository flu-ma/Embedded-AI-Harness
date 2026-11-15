"""Options of POST /api/flash that change esptool's reset behaviour (FR-042)."""

AFTER = ("hard-reset", "no-reset")


def reset_args(after: str | None) -> list[str]:
    """esptool --before/--after for a flash request; ValueError on an unknown `after`.

    hard-reset (default) boots the new image at once. no-reset leaves the chip
    in the ROM downloader, so the first boot of the image is the next reset —
    POST /api/serial/reset — and its log is captured from the first line.
    """
    after = (after or "hard-reset").strip().lower().replace("_", "-")
    if after not in AFTER:
        raise ValueError(f"after must be one of {', '.join(AFTER)}")
    return ["--before", "default-reset", "--after", after]


def stays_in_bootloader(esptool_args: list[str]) -> bool:
    """True when the flash leaves the chip in the ROM downloader. The serial
    proxy must then stay stopped: opening the port (DTR/RTS) boots the chip,
    and that first boot's log would fall into the proxy's restart gap."""
    return any(a == "--after" and b == "no-reset" for a, b in zip(esptool_args, esptool_args[1:]))
