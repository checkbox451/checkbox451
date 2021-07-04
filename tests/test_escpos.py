from escpos.constants import CODEPAGE_CHANGE
from escpos.printer import Dummy


def test_escpos():
    printer = Dummy(profile="POS-5890")
    printer.text("абвїґ")

    expected = (
        CODEPAGE_CHANGE
        + bytes([59])  # CP866
        + "абвї".encode("cp866")
        + CODEPAGE_CHANGE
        + bytes([73])  # CP1251
        + "ґ".encode("cp1251")
    )
    assert printer.output == expected
