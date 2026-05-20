import threading

import pystray
from PIL import Image, ImageDraw


def create_tray_icon(muted: bool = False) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    color = "white"
    if muted:
        draw.ellipse([2, 2, 18, 18], fill="#f44336")
        color = "#cccccc"

    draw.rectangle([8, 20, 24, 44], fill=color)
    draw.polygon([(24, 20), (24, 44), (44, 52), (44, 12)], fill=color)
    for offset in range(0, 12, 5):
        draw.arc(
            [28 + offset, 12 + offset, 56 - offset, 52 - offset],
            start=300,
            end=60,
            fill=color,
            width=3,
        )
    return img


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
