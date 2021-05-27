from escpos.constants import CODEPAGE_CHANGE
from escpos.printer import File


def test_escpos(tmp_path):
    dst_file = tmp_path / "output.bin"
    printer = File(str(dst_file), profile="POS-5890")
    printer.text("абвїґ")

    expected = (
        CODEPAGE_CHANGE
        + bytes([59])  # CP866
        + "абвї".encode("cp866")
        + CODEPAGE_CHANGE
        + bytes([73])  # CP1251
        + "ґ".encode("cp1251")
    )
    assert dst_file.read_bytes() == expected
