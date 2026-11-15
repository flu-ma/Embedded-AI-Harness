"""multipart_part.split_part keeps a part's content byte-exact."""
import pytest

from multipart_part import split_part

B = b"XyZ"


def body(*parts: bytes) -> bytes:
    out = b""
    for p in parts:
        out += b"--" + B + b"\r\n" + p + b"\r\n"
    return out + b"--" + B + b"--\r\n"


def parts(raw: bytes):
    return [p for p in (split_part(x) for x in raw.split(b"--" + B)) if p]


@pytest.mark.parametrize("tail", [b"\r\x0c", b"\r\n", b"\n", b" ", b"\t\x0b", b"\x00\xff"])
def test_binary_tail_kept(tail):
    data = bytes(range(256)) + tail
    got = parts(body(b'Content-Disposition: form-data; name="f"; filename="a.bin"\r\n'
                     b"Content-Type: application/octet-stream\r\n\r\n" + data))
    assert len(got) == 1 and got[0][1] == data


def test_leading_whitespace_in_content_kept():
    data = b"\r\n\x0c  firmware"
    got = parts(body(b'Content-Disposition: form-data; name="f"; filename="a"\r\n\r\n' + data))
    assert got[0][1] == data


def test_fields_and_preamble():
    got = parts(b"preamble ignored\r\n" + body(b'Content-Disposition: form-data; name="slot"\r\n\r\nSLOT1',
                                              b'Content-Disposition: form-data; name="e"\r\n\r\n'))
    assert [c for _, c in got] == [b"SLOT1", b""]
    assert 'name="slot"' in got[0][0]


def test_the_seen_image_tail():
    # firmware-v0.0.0-d22d0eb-bringup ended in its SHA-256 …1f330d0c: 0d 0c lost
    data = b"\x98\x67\x9c\x1f\x2a\xcb\x30\xc4\xca\xf0\xb0\xbd\x1f\x33\x0d\x0c"
    got = parts(body(b'Content-Disposition: form-data; name="webtemp.bin"; filename="webtemp.bin"\r\n\r\n' + data))
    assert got[0][1].endswith(b"\x0d\x0c") and len(got[0][1]) == 16
