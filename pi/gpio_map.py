"""Map the API's Pi BCM pin numbers onto the host board's gpiochip lines.

The HTTP API (FR-018) and testbench.json speak Raspberry Pi BCM numbers, and the
wiring is described by 40-pin header position (BCM 17 = physical pin 11 = EN,
BCM 18 = physical pin 12 = BOOT). On a Raspberry Pi the BCM number *is* the
line offset on /dev/gpiochip0. Other boards put different SoC pins on the same
header positions, so the offset must be looked up — using the BCM number as an
offset there drives an unrelated SoC pin (on an Orange Pi Zero 4 line 18 is
PA18 and the request fails with errno 517).

Each board table maps BCM -> (gpiochip path, line offset) for the header pin
where a Raspberry Pi has that BCM GPIO. Header pins the board lacks, or whose
pin is muxed to another function, are left out and so are not allowed.
"""
import pathlib

RPI = "raspberrypi"

# Orange Pi Zero 4 (Allwinner sun60iw2, 36-pin header). From `gpio readall`
# (wiringOP): physical pin -> SoC pin -> Linux number. gpiochip0 holds banks
# PA..PK (offset = Linux number); gpiochip1 holds PL (base 352).
#   BCM17 p11 PB0  32     BCM18 p12 PD1  97     BCM27 p13 PB1  33
#   BCM22 p15 PE11 139    BCM23 p16 PL2  354    BCM25 p22 PD2  98
# Left out: BCM24 p18 PL3 (driven as an output by the system at boot),
# BCM19 p35 PL6 (muxed ALT5); BCM16/20/21/26 sit on pins 36–40 (36 is NC,
# 37–40 do not exist). BCM 5/6/12/13 are on pins 29/31/32/33 — on this board
# those are PB6/PB8/PD13/PD16 and are reserved for siggen hardware on a Pi, so
# they stay out until a board needs them.
ORANGEPI_ZERO4 = {
    17: ("/dev/gpiochip0", 32),
    18: ("/dev/gpiochip0", 97),
    27: ("/dev/gpiochip0", 33),
    22: ("/dev/gpiochip0", 139),
    23: ("/dev/gpiochip1", 2),
    25: ("/dev/gpiochip0", 98),
}

BOARDS = {
    "orangepizero4": ORANGEPI_ZERO4,
}

# Raspberry Pi: BCM number == offset on gpiochip0.
RPI_ALLOWED = frozenset({16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27})


def detect_board(release_file="/etc/orangepi-release"):
    """Return the board key: an Orange Pi BOARD= value, else RPI."""
    try:
        for line in pathlib.Path(release_file).read_text().splitlines():
            if line.startswith("BOARD="):
                return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return RPI


class GpioMap:
    def __init__(self, board):
        self.board = board
        self.table = BOARDS.get(board)
        self.supported = board == RPI or self.table is not None

    @property
    def allowed(self):
        if self.board == RPI:
            return RPI_ALLOWED
        return frozenset(self.table or ())

    def resolve(self, bcm):
        """BCM pin -> (chip path, line offset). KeyError if not on this board."""
        if bcm not in self.allowed:
            raise KeyError(f"pin {bcm} not available on board {self.board}")
        if self.board == RPI:
            return ("/dev/gpiochip0", bcm)
        return self.table[bcm]
