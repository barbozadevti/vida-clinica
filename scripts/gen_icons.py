"""Gera os ícones do PWA (manifest + apple-touch-icon) a partir de formas
desenhadas com Pillow — sem depender de nenhum arquivo de imagem externo,
no mesmo espírito de "sem custo de integração" das outras ondas."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "frontend" / "assets" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

ACCENT = (30, 111, 217, 255)       # #1e6fd9
ACCENT_DEEP = (24, 87, 173, 255)   # #1857ad
WHITE = (255, 255, 255, 255)


def _gradient_square(size: int, radius_ratio: float) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grad = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for y in range(size):
        t = y / (size - 1)
        r = round(ACCENT[0] + (ACCENT_DEEP[0] - ACCENT[0]) * t)
        g = round(ACCENT[1] + (ACCENT_DEEP[1] - ACCENT[1]) * t)
        b = round(ACCENT[2] + (ACCENT_DEEP[2] - ACCENT[2]) * t)
        for x in range(size):
            grad.putpixel((x, y), (r, g, b, 255))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=int(size * radius_ratio), fill=255
    )
    img.paste(grad, (0, 0), mask)
    return img


def _cross(size: int, scale: float) -> Image.Image:
    """Desenha a cruz "✚" branca, arredondada, centralizada."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    arm = size * scale          # comprimento total do braço da cruz
    thick = arm * 0.34          # espessura
    cx = cy = size / 2
    rad = thick * 0.35
    d.rounded_rectangle([cx - thick / 2, cy - arm / 2, cx + thick / 2, cy + arm / 2],
                        radius=rad, fill=WHITE)
    d.rounded_rectangle([cx - arm / 2, cy - thick / 2, cx + arm / 2, cy + thick / 2],
                        radius=rad, fill=WHITE)
    return img


def make_icon(size: int, radius_ratio: float, cross_scale: float, path: Path) -> None:
    base = _gradient_square(size, radius_ratio)
    cross = _cross(size, cross_scale)
    base.alpha_composite(cross)
    base.save(path)
    print("gerado", path.name, base.size)


# ícones "any" (com cantos arredondados, para manifest.json / favicon)
make_icon(192, 0.22, 0.5, OUT / "icon-192.png")
make_icon(512, 0.22, 0.5, OUT / "icon-512.png")

# ícone "maskable" — precisa de margem de segurança (zona central ~80%)
# porque o SO pode recortar em círculo/squircle
make_icon(512, 0.0, 0.36, OUT / "icon-maskable-512.png")

# apple-touch-icon: iOS já arredonda os cantos sozinho, então manda quadrado
make_icon(180, 0.0, 0.5, OUT / "apple-touch-icon.png")

# favicon simples
make_icon(32, 0.22, 0.5, OUT / "favicon-32.png")

print("OK")
