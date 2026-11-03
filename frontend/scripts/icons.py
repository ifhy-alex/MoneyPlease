"""Genera los íconos PNG de la app instalable (public/icon-*.png) con el mismo dibujo que public/favicon.svg.

Uso: uv run --project ../backend python scripts/icons.py   (desde frontend/; requiere Pillow)
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

PUBLIC = Path(__file__).resolve().parent.parent / "public"
BG, SILVER, WHITE, GLOW = (4, 6, 15), (203, 213, 225), (241, 245, 249), (37, 71, 184)
LINKS = [((28, 66), (44, 40)), ((44, 40), (60, 52)), ((60, 52), (74, 30)), ((60, 52), (70, 74))]
STARS = [((28, 66), 4), ((44, 40), 4.6), ((74, 30), 4), ((70, 74), 3.6)]
CENTER, CENTER_R = (60, 52), 8


def draw(size: int, rounded: bool) -> Image.Image:
    s = size * 4  # se dibuja a 4x y se reduce: bordes suaves
    k = s / 100
    img = Image.new("RGB", (s, s), BG)
    glow = Image.new("RGB", (s, s), BG)
    ImageDraw.Draw(glow).ellipse([(60 - 34) * k, (52 - 34) * k, (60 + 34) * k, (52 + 34) * k], fill=GLOW)
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(14 * k)), 0.55)
    d = ImageDraw.Draw(img, "RGBA")
    for (a, b) in LINKS:
        d.line([(a[0] * k, a[1] * k), (b[0] * k, b[1] * k)], fill=SILVER + (150,), width=round(2.2 * k))
    for (x, y), r in STARS:
        d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k], fill=SILVER)
    x, y = CENTER
    d.ellipse([(x - CENTER_R) * k, (y - CENTER_R) * k, (x + CENTER_R) * k, (y + CENTER_R) * k], fill=WHITE)
    img = img.resize((size, size), Image.LANCZOS)
    if rounded:  # el ícono "any" lleva esquinas redondeadas; el "maskable" va cuadrado (el sistema lo recorta)
        mask = Image.new("L", (size * 4, size * 4), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, size * 4, size * 4], radius=22 * size * 4 / 100, fill=255)
        out = Image.new("RGBA", (size, size))
        out.paste(img, mask=mask.resize((size, size), Image.LANCZOS))
        return out
    return img


if __name__ == "__main__":
    draw(192, True).save(PUBLIC / "icon-192.png")
    draw(512, True).save(PUBLIC / "icon-512.png")
    draw(512, False).save(PUBLIC / "icon-maskable-512.png")
    draw(180, False).save(PUBLIC / "apple-touch-icon.png")  # iOS redondea solo y no admite transparencia
    print("íconos generados en", PUBLIC)
