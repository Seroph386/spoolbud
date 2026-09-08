from spoolbud.services.qr import render_qr_svg


def test_render_qr_svg_preserves_svg_output():
    content = render_qr_svg("https://spoolbud.example/bin/F-001")
    assert content.startswith(b'<?xml version="1.0" encoding="utf-8"?>')
    assert b"<svg" in content
