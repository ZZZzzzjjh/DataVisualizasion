from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "数据采集方法与流程图.png"


W, H = 1600, 1000
BG = "white"
INK = "#2F3A45"
TEXT = "#1F2933"
SOURCE = "#EEF5FF"
PROCESS = "#F7F7F2"
FINAL = "#EAF7EF"


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


FONT = load_font(32)


def box(draw: ImageDraw.ImageDraw, cx: int, cy: int, w: int, h: int, label: str, fill: str = "white", lw: int = 3) -> None:
    x1, y1 = cx - w // 2, cy - h // 2
    x2, y2 = cx + w // 2, cy + h // 2
    draw.rounded_rectangle((x1, y1, x2, y2), radius=16, fill=fill, outline=INK, width=lw)
    bbox = draw.textbbox((0, 0), label, font=FONT)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw / 2, cy - th / 2 - 2), label, font=FONT, fill=TEXT)


def line(draw: ImageDraw.ImageDraw, p1: tuple[int, int], p2: tuple[int, int], width: int = 4) -> None:
    draw.line((p1, p2), fill=INK, width=width)


def arrow(draw: ImageDraw.ImageDraw, p1: tuple[int, int], p2: tuple[int, int], width: int = 4) -> None:
    draw.line((p1, p2), fill=INK, width=width)
    x1, y1 = p1
    x2, y2 = p2
    if abs(x2 - x1) > abs(y2 - y1):
        if x2 >= x1:
            pts = [(x2, y2), (x2 - 18, y2 - 10), (x2 - 18, y2 + 10)]
        else:
            pts = [(x2, y2), (x2 + 18, y2 - 10), (x2 + 18, y2 + 10)]
    else:
        if y2 >= y1:
            pts = [(x2, y2), (x2 - 10, y2 - 18), (x2 + 10, y2 - 18)]
        else:
            pts = [(x2, y2), (x2 - 10, y2 + 18), (x2 + 10, y2 + 18)]
    draw.polygon(pts, fill=INK)


img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

# Main vertical steps
box(draw, 800, 90, 360, 78, "确定研究主题")
box(draw, 800, 220, 360, 78, "选取研究城市")
box(draw, 800, 350, 360, 78, "明确数据需求")

arrow(draw, (800, 129), (800, 181))
arrow(draw, (800, 259), (800, 311))

# Four source nodes
sources = [
    (230, 550, "招聘数据"),
    (610, 550, "统计数据"),
    (990, 550, "生活成本"),
    (1370, 550, "地图边界"),
]
for cx, cy, label in sources:
    box(draw, cx, cy, 250, 82, label, fill=SOURCE)

# Split arrows
split_y = 450
line(draw, (800, 389), (800, split_y))
line(draw, (230, split_y), (1370, split_y))
for cx, _, _ in sources:
    arrow(draw, (cx, split_y), (cx, 507))

# Integration node
box(draw, 800, 705, 380, 78, "整理结构化表格", fill=PROCESS)

join_y = 640
for cx, _, _ in sources:
    line(draw, (cx, 591), (cx, join_y))
line(draw, (230, join_y), (1370, join_y))
arrow(draw, (800, join_y), (800, 666))

box(draw, 800, 825, 380, 78, "清洗与标准化", fill=PROCESS)
box(draw, 800, 945, 380, 78, "城市综合数据集", fill=FINAL, lw=4)

arrow(draw, (800, 744), (800, 786))
arrow(draw, (800, 864), (800, 906))

img.save(OUT)
print(OUT)
