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
