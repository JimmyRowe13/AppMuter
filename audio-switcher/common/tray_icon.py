import threading

import pystray
from PIL import Image, ImageDraw


def create_tray_icon(muted: bool = False) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if muted:
        _draw_speaker(draw, fill=(80, 80, 80))
        draw.ellipse([6, 22, 58, 42], fill=(244, 67, 54))
        draw.line([(24, 20), (40, 44)], fill=(255, 255, 255), width=4)
        draw.line([(40, 20), (24, 44)], fill=(255, 255, 255), width=4)
    else:
        _draw_speaker(draw, fill=(79, 195, 247))
    return img


def _draw_speaker(draw, fill=(255, 255, 255)):
    # Speaker body
    draw.rectangle([10, 22, 24, 42], fill=fill)
    # Speaker cone (triangle)
    draw.polygon([(24, 20), (24, 44), (42, 50), (42, 14)], fill=fill)
    # Sound waves
    for i, offset in enumerate([0, 5, 10]):
        alpha = int(255 * (1 - i * 0.3))
        color = (*fill, alpha)
        draw.arc(
            [28 + offset, 14 + offset, 56 - offset, 50 - offset],
            start=300, end=60, fill=color, width=3,
        )


def run_tray(menu: pystray.Menu, tooltip: str, on_activate=None):
    exit_event = threading.Event()
    icon_img = create_tray_icon()

    icon = pystray.Icon("app_muter", icon_img, tooltip, menu)
    icon._on_activate = on_activate

    def on_exit(icon_instance):
        icon_instance.stop()
        exit_event.set()

    icon.run_detached()

    while not exit_event.is_set():
        exit_event.wait(0.5)

    return icon
