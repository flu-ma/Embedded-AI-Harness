"""FR-042: POST /api/flash `after` field → esptool reset flags."""
import pytest

import flash_opts


def test_default_is_hard_reset():
    assert flash_opts.reset_args(None) == ["--before", "default-reset", "--after", "hard-reset"]
    assert flash_opts.reset_args("") == ["--before", "default-reset", "--after", "hard-reset"]


def test_no_reset_accepted_in_both_spellings():
    for v in ("no-reset", "no_reset", "NO-RESET"):
        assert flash_opts.reset_args(v)[-2:] == ["--after", "no-reset"]


@pytest.mark.parametrize("bad", ["soft-reset", "watchdog-reset", "x", "no-reset; rm"])
def test_unknown_after_rejected(bad):
    with pytest.raises(ValueError, match="after must be one of"):
        flash_opts.reset_args(bad)
