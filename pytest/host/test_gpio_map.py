"""FR-018 board mapping: BCM numbers -> gpiochip lines per host board."""
import pytest

import gpio_map


def test_raspberry_pi_is_identity_on_gpiochip0():
    m = gpio_map.GpioMap(gpio_map.RPI)
    assert m.supported
    assert m.resolve(17) == ("/dev/gpiochip0", 17)
    assert m.resolve(18) == ("/dev/gpiochip0", 18)
    assert 17 in m.allowed and 18 in m.allowed


def test_orangepi_zero4_en_and_boot_on_header_pins_11_and_12():
    m = gpio_map.GpioMap("orangepizero4")
    assert m.supported
    assert m.resolve(17) == ("/dev/gpiochip0", 32)   # p11 PB0 -> EN
    assert m.resolve(18) == ("/dev/gpiochip0", 97)   # p12 PD1 -> BOOT
    assert m.resolve(23) == ("/dev/gpiochip1", 2)    # p16 PL2 (second chip)


def test_orangepi_zero4_refuses_pins_it_lacks_or_reserves():
    m = gpio_map.GpioMap("orangepizero4")
    for bcm in (16, 19, 20, 21, 24, 26):
        assert bcm not in m.allowed
        with pytest.raises(KeyError):
            m.resolve(bcm)


def test_unknown_board_has_no_pins():
    m = gpio_map.GpioMap("some-new-board")
    assert not m.supported
    assert m.allowed == frozenset()
    with pytest.raises(KeyError):
        m.resolve(18)


def test_detect_board(tmp_path):
    f = tmp_path / "orangepi-release"
    f.write_text('# x\nBOARD=orangepizero4\nBOARD_NAME="Orange Pi Zero 4"\n')
    assert gpio_map.detect_board(str(f)) == "orangepizero4"
    assert gpio_map.detect_board(str(tmp_path / "absent")) == gpio_map.RPI
