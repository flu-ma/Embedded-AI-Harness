"""One part of a multipart/form-data body, split without touching its data.

A raw part — the bytes between two `--boundary` lines — is
`\\r\\n<headers>\\r\\n\\r\\n<content>\\r\\n`. Only that framing may be removed:
`bytes.strip()` also eats any whitespace bytes (0x09–0x0d, 0x20) the content
itself ends with, which silently truncated firmware images whose last bytes
happened to be, e.g., `0d 0c` (FR-020 flash, FR-021 firmware upload).
"""


def split_part(raw: bytes) -> tuple[str, bytes] | None:
    """(header text, content) of a raw part, or None for the preamble, the
    closing `--` and anything without a header block."""
    part = raw.lstrip(b"\r\n")                 # headers start with a letter: safe
    if not part or part.startswith(b"--"):
        return None
    for sep in (b"\r\n\r\n", b"\n\n"):
        if sep in part:
            head, content = part.split(sep, 1)
            break
    else:
        return None
    if content.endswith(b"\r\n"):              # the framing CRLF, exactly once
        content = content[:-2]
    elif content.endswith(b"\n"):
        content = content[:-1]
    return head.decode("utf-8", errors="replace"), content
