from __future__ import annotations

from io import BytesIO

from mss import mss
from PIL import Image


def capture_primary_screen_jpeg(quality: int = 74) -> bytes:
    with mss() as screen:
        monitor = screen.monitors[1]
        shot = screen.grab(monitor)
        image = Image.frombytes("RGB", shot.size, shot.rgb)

    out = BytesIO()
    image.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue()
