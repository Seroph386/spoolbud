"""QR code generation."""

from __future__ import annotations

import io

import segno


def render_qr_svg(value: str) -> bytes:
    qr = segno.make(value)
    buffer = io.BytesIO()
    qr.save(buffer, kind="svg", scale=7, border=2)
    return buffer.getvalue()
