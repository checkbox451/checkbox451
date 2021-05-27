from escpos.printer import File


def test_escpos(tmp_path):
    dst_file = tmp_path / "output.bin"
    printer = File(str(dst_file))
    printer.text("абв")

    assert dst_file.read_bytes() == b"\x1bt\x11\xa0\xa1\xa2"
