"""生成与网页一致的高分辨率桌面图标（仅构建时使用）。"""

from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 512
SCALE = 4
OUTPUT = Path(__file__).resolve().parent / "build"
OUTPUT.mkdir(exist_ok=True)
image = Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)


def box(values: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    return tuple(value * SCALE for value in values)


def points(values: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return [(x * SCALE, y * SCALE) for x, y in values]


draw.rounded_rectangle(box((0, 0, 511, 511)), radius=112 * SCALE, fill="#183b32")
width = 34 * SCALE
cream = "#f4f1e9"
draw.line(points([(118, 148), (394, 148)]), fill=cream, width=width)
draw.line(
    points([(256, 148), (256, 366), (252, 386), (240, 404), (222, 420), (190, 438)]),
    fill=cream,
    width=width,
    joint="curve",
)
draw.line(
    points([(158, 242), (354, 242), (320, 362), (178, 362), (158, 242)]),
    fill=cream,
    width=width,
    joint="curve",
)
draw.ellipse(box((332, 324, 432, 424)), fill="#c45b3f")
image = image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
image.save(OUTPUT / "icon.png")
image.save(OUTPUT / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(f"Desktop icons written to {OUTPUT}")
