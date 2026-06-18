from __future__ import annotations

import csv
import math
from collections import defaultdict, Counter
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
PANEL = ROOT / "data" / "cleaned" / "city_panel_enriched.csv"
JOBS = ROOT / "data" / "cleaned" / "city_job_structure.csv"

W, H = 1200, 720
BG = "#FFFFFF"
INK = "#1F2937"
MUTED = "#64748B"
GRID = "#E2E8F0"
BLUE = "#2F78B7"
BLUE_LIGHT = "#78ADD8"
ORANGE = "#F2A65A"
RED = "#D96C75"
GREEN = "#5BAE7D"
PURPLE = "#8A78C2"
TEAL = "#4FA9A6"
YELLOW = "#E8C45B"
PINK = "#C76D9E"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if path and Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


FONT = font(24)
FONT_SM = font(19)
FONT_XS = font(16)
FONT_BOLD = font(24, True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def num(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "") or 0)
    except ValueError:
        return 0.0


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt=FONT) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def draw_wrapped_label(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, fill=INK, fnt=FONT_SM) -> None:
    draw.text((x, y), text, fill=fill, font=fnt)


def nice_max(value: float) -> float:
    if value <= 0:
        return 1
    exp = math.floor(math.log10(value))
    step = 10 ** max(exp - 1, 0)
    return math.ceil(value / step) * step


def save(img: Image.Image, name: str) -> None:
    FIG.mkdir(exist_ok=True)
    img.save(FIG / name)
    print(FIG / name)


def horizontal_bar(
    rows: list[tuple[str, float]],
    name: str,
    unit: str,
    value_suffix: str,
    width: int = W,
    height: int | None = None,
    allow_negative: bool = False,
) -> None:
    n = len(rows)
    height = height or max(640, 90 + n * 42)
    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)

    left, right, top, bottom = 150, 110, 58, 76
    plot_w = width - left - right
    plot_h = height - top - bottom
    row_h = plot_h / max(n, 1)

    values = [v for _, v in rows]
    if allow_negative and min(values) < 0:
        min_v = min(values)
        max_v = max(values)
        span_min = -nice_max(abs(min_v))
        span_max = nice_max(max_v)
    else:
        span_min = 0
        span_max = nice_max(max(values) * 1.06)
    span = span_max - span_min

    def xmap(v: float) -> float:
        return left + (v - span_min) / span * plot_w

    # Grid and x-axis labels
    for i in range(6):
        v = span_min + span * i / 5
        x = xmap(v)
        d.line((x, top, x, height - bottom + 8), fill=GRID, width=1)
        label = f"{v:,.0f}"
        tw, _ = text_size(d, label, FONT_XS)
        d.text((x - tw / 2, height - bottom + 18), label, fill="#8492A6", font=FONT_XS)
    if allow_negative and span_min < 0:
        x0 = xmap(0)
        d.line((x0, top - 8, x0, height - bottom), fill="#94A3B8", width=2)

    zero_x = xmap(0)
    colors = [BLUE_LIGHT] * n
    for i in range(n):
        if i >= n - 3:
            colors[i] = BLUE
    if allow_negative:
        colors = [RED if v < 0 else BLUE for _, v in rows]

    for i, (label, value) in enumerate(rows):
        cy = top + row_h * i + row_h / 2
        bar_h = min(28, row_h * 0.66)
        y1, y2 = cy - bar_h / 2, cy + bar_h / 2
        x1, x2 = (zero_x, xmap(value)) if value >= 0 else (xmap(value), zero_x)
        d.rounded_rectangle((x1, y1, x2, y2), radius=8, fill=colors[i])
        tw, th = text_size(d, label, FONT_SM)
        d.text((left - tw - 18, cy - th / 2), label, fill=INK, font=FONT_SM)
        value_text = f"{value:,.0f}{value_suffix}"
        if value >= 0:
            d.text((x2 + 10, cy - 10), value_text, fill=INK, font=FONT_XS)
        else:
            tw, _ = text_size(d, value_text, FONT_XS)
            d.text((x1 - tw - 10, cy - 10), value_text, fill=INK, font=FONT_XS)

    d.text((left, height - 38), f"单位：{unit}", fill=MUTED, font=FONT_SM)
    save(img, name)


def vertical_bar(rows: list[tuple[str, float]], name: str, unit: str, value_suffix: str) -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    left, right, top, bottom = 95, 70, 70, 115
    plot_w = W - left - right
    plot_h = H - top - bottom
    max_v = nice_max(max(v for _, v in rows) * 1.15)

    for i in range(6):
        v = max_v * i / 5
        y = top + plot_h - v / max_v * plot_h
        d.line((left, y, W - right, y), fill=GRID, width=1)
        d.text((22, y - 10), f"{v:,.0f}", fill="#8492A6", font=FONT_XS)

    gap = 22
    bar_w = (plot_w - gap * (len(rows) - 1)) / len(rows)
    for i, (label, value) in enumerate(rows):
        x = left + i * (bar_w + gap)
        y = top + plot_h - value / max_v * plot_h
        color = BLUE if i in (0, len(rows) - 1) else BLUE_LIGHT
        d.rounded_rectangle((x, y, x + bar_w, top + plot_h), radius=8, fill=color)
        vtxt = f"{value:,.0f}{value_suffix}"
        tw, th = text_size(d, vtxt, FONT_XS)
        d.text((x + bar_w / 2 - tw / 2, y - th - 8), vtxt, fill=INK, font=FONT_XS)
        tw, _ = text_size(d, label, FONT_SM)
        d.text((x + bar_w / 2 - tw / 2, top + plot_h + 16), label, fill=INK, font=FONT_SM)

    d.text((left, H - 38), f"单位：{unit}", fill=MUTED, font=FONT_SM)
    save(img, name)


def stacked_industry(job_rows: list[dict[str, str]]) -> None:
    city_order = []
    industries = []
    data: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in job_rows:
        c, ind = r["city_name_zh"], r["industry"]
        if c not in city_order:
            city_order.append(c)
        if ind not in industries:
            industries.append(ind)
        data[c][ind] += num(r, "job_share_percent")

    totals = Counter()
    for ind in industries:
        totals[ind] = sum(data[c][ind] for c in city_order)
    industries = [i for i, _ in totals.most_common(6)]
    colors = [BLUE, ORANGE, GREEN, PURPLE, TEAL, YELLOW]

    img = Image.new("RGB", (1300, 920), BG)
    d = ImageDraw.Draw(img)
    left, right, top, bottom = 150, 180, 64, 90
    plot_w = 1300 - left - right
    row_h = (920 - top - bottom) / len(city_order)

    for i in range(6):
        x = left + plot_w * i / 5
        d.line((x, top - 8, x, 920 - bottom), fill=GRID, width=1)
        lab = f"{i * 20}%"
        tw, _ = text_size(d, lab, FONT_XS)
        d.text((x - tw / 2, 920 - bottom + 18), lab, fill="#8492A6", font=FONT_XS)

    for idx, city in enumerate(city_order):
        cy = top + idx * row_h + row_h / 2
        tw, th = text_size(d, city, FONT_SM)
        d.text((left - tw - 18, cy - th / 2), city, fill=INK, font=FONT_SM)
        x = left
        for ind, color in zip(industries, colors):
            v = data[city][ind]
            seg_w = plot_w * v / 100
            if seg_w > 0:
                d.rectangle((x, cy - 13, x + seg_w, cy + 13), fill=color)
            x += seg_w

    lx, ly = 1135, top
    for ind, color in zip(industries, colors):
        d.rounded_rectangle((lx, ly, lx + 24, ly + 16), radius=4, fill=color)
        d.text((lx + 34, ly - 3), ind, fill=INK, font=FONT_XS)
        ly += 36
    d.text((left, 920 - 38), "单位：岗位占比（%）", fill=MUTED, font=FONT_SM)
    save(img, "图3-8_行业结构对比图.png")


def top_position_salary(job_rows: list[dict[str, str]]) -> None:
    rows = []
    for r in job_rows:
        rows.append((f"{r['city_name_zh']}·{r['position_type']}", num(r, "position_avg_salary_rmb")))
    rows = sorted(rows, key=lambda x: x[1])[-12:]
    horizontal_bar(rows, "图3-9_岗位类型与薪资对比图.png", "元/月", " 元", width=1300, height=760)


def education_pie(job_rows: list[dict[str, str]]) -> None:
    cnt = Counter(r["education_requirement"] for r in job_rows)
    rows = cnt.most_common()
    colors = [BLUE, ORANGE, GREEN, PURPLE, RED]
    img = Image.new("RGB", (1000, 680), BG)
    d = ImageDraw.Draw(img)
    cx, cy, r = 350, 330, 210
    start = -90
    total = sum(cnt.values())
    for i, (label, value) in enumerate(rows):
        end = start + value / total * 360
        d.pieslice((cx - r, cy - r, cx + r, cy + r), start=start, end=end, fill=colors[i % len(colors)], outline=BG, width=2)
        mid = math.radians((start + end) / 2)
        px, py = cx + math.cos(mid) * (r + 35), cy + math.sin(mid) * (r + 35)
        txt = f"{value}条"
        tw, th = text_size(d, txt, FONT_XS)
        d.text((px - tw / 2, py - th / 2), txt, fill=INK, font=FONT_XS)
        start = end

    lx, ly = 660, 205
    for i, (label, value) in enumerate(rows):
        pct = value / total * 100
        d.rounded_rectangle((lx, ly, lx + 28, ly + 18), radius=4, fill=colors[i % len(colors)])
        d.text((lx + 42, ly - 5), f"{label}：{value}条，{pct:.1f}%", fill=INK, font=FONT_SM)
        ly += 52
    d.text((90, 620), "单位：就业结构记录数量", fill=MUTED, font=FONT_SM)
    save(img, "图3-10_学历要求结构图.png")


def scatter(
    rows: list[dict[str, str]],
    x_key: str,
    y_key: str,
    name: str,
    x_unit: str,
    y_unit: str,
    x_label: str,
    y_label: str,
    quadrant: bool = False,
    label_offsets: dict[str, tuple[int, int]] | None = None,
) -> None:
    img_w, img_h = (1500, 900) if quadrant else (1300, 820)
    img = Image.new("RGB", (img_w, img_h), BG)
    d = ImageDraw.Draw(img)
    left, right, top, bottom = 125, 90, 80, 125
    plot_w = img_w - left - right
    plot_h = img_h - top - bottom
    xs = [num(r, x_key) for r in rows]
    ys = [num(r, y_key) for r in rows]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    xpad = (xmax - xmin) * 0.12 or 1
    ypad = (ymax - ymin) * 0.16 or 1
    xmin, xmax = xmin - xpad, xmax + xpad
    ymin, ymax = ymin - ypad, ymax + ypad

    def xm(v: float) -> float:
        return left + (v - xmin) / (xmax - xmin) * plot_w

    def ym(v: float) -> float:
        return top + plot_h - (v - ymin) / (ymax - ymin) * plot_h

    for i in range(6):
        x = left + plot_w * i / 5
        y = top + plot_h * i / 5
        d.line((x, top, x, top + plot_h), fill=GRID, width=1)
        d.line((left, y, left + plot_w, y), fill=GRID, width=1)
        xv = xmin + (xmax - xmin) * i / 5
        yv = ymax - (ymax - ymin) * i / 5
        d.text((x - 24, top + plot_h + 18), f"{xv:,.0f}", fill="#8492A6", font=FONT_XS)
        d.text((30, y - 10), f"{yv:,.0f}", fill="#8492A6", font=FONT_XS)

    avg_x = sum(xs) / len(xs)
    avg_y = sum(ys) / len(ys)
    d.line((xm(avg_x), top, xm(avg_x), top + plot_h), fill="#94A3B8", width=2)
    d.line((left, ym(avg_y), left + plot_w, ym(avg_y)), fill="#94A3B8", width=2)

    color_by_region = {
        "华东": BLUE,
        "华南": ORANGE,
        "华北": GREEN,
        "西南": PURPLE,
        "华中": TEAL,
        "西北": RED,
    }
    offsets = [(8, -20), (8, 8), (-44, -20), (-44, 8), (12, -4)]
    label_offsets = label_offsets or {}
    for idx, r0 in enumerate(rows):
        x, y = xm(num(r0, x_key)), ym(num(r0, y_key))
        color = color_by_region.get(r0.get("region", ""), BLUE)
        d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=color, outline=BG, width=2)
        ox, oy = label_offsets.get(r0["city_name_zh"], offsets[idx % len(offsets)])
        if abs(ox) > 18 or abs(oy) > 18:
            d.line((x, y, x + ox * 0.75, y + oy * 0.75), fill="#CBD5E1", width=1)
        d.text((x + ox, y + oy), r0["city_name_zh"], fill=INK, font=FONT_XS)

    if quadrant:
        d.text((xm(avg_x) + 12, top + 12), "高薪低结余", fill=MUTED, font=FONT_XS)
        d.text((xm(avg_x) + 12, ym(avg_y) - 32), "高薪高结余", fill=MUTED, font=FONT_XS)
        d.text((left + 14, ym(avg_y) - 32), "低薪高结余", fill=MUTED, font=FONT_XS)
        d.text((left + 14, top + plot_h - 34), "低薪低结余", fill=MUTED, font=FONT_XS)

    d.text((left, img_h - 44), f"横轴：{x_label}（{x_unit}）    纵轴：{y_label}（{y_unit}）", fill=MUTED, font=FONT_SM)
    save(img, name)


def grouped_income_cost(rows: list[dict[str, str]]) -> None:
    selected_names = ["北京", "上海", "深圳", "杭州", "南京", "广州", "长沙", "成都", "宁波", "青岛"]
    data = [r for r in rows if r["city_name_zh"] in selected_names]
    order = {name: i for i, name in enumerate(selected_names)}
    data.sort(key=lambda r: order[r["city_name_zh"]])
    metrics = [
        ("税后月薪", "avg_salary", BLUE),
        ("生活成本", "monthly_cost_single_rmb", ORANGE),
        ("市中心租金", "rent_1br_city_centre_rmb", RED),
        ("实际月结余", "monthly_balance_after_rent_cost_rmb", GREEN),
    ]
    img = Image.new("RGB", (1500, 820), BG)
    d = ImageDraw.Draw(img)
    left, right, top, bottom = 100, 60, 72, 130
    plot_w = 1500 - left - right
    plot_h = 820 - top - bottom
    values = [num(r, key) for r in data for _, key, _ in metrics]
    max_v = nice_max(max(values) * 1.12)
    min_v = min(0, min(values))
    span = max_v - min_v

    def ym(v: float) -> float:
        return top + plot_h - (v - min_v) / span * plot_h

    for i in range(6):
        v = min_v + span * i / 5
        y = ym(v)
        d.line((left, y, 1500 - right, y), fill=GRID, width=1)
        d.text((24, y - 10), f"{v:,.0f}", fill="#8492A6", font=FONT_XS)

    group_w = plot_w / len(data)
    bar_w = min(24, group_w / 5.5)
    zero = ym(0)
    for i, r in enumerate(data):
        base_x = left + i * group_w + group_w * 0.14
        for j, (_, key, color) in enumerate(metrics):
            v = num(r, key)
            x = base_x + j * (bar_w + 5)
            y = ym(v)
            d.rounded_rectangle((x, min(y, zero), x + bar_w, max(y, zero)), radius=5, fill=color)
        label = r["city_name_zh"]
        tw, _ = text_size(d, label, FONT_SM)
        d.text((left + i * group_w + group_w / 2 - tw / 2, top + plot_h + 18), label, fill=INK, font=FONT_SM)

    lx, ly = 780, 24
    for label, _, color in metrics:
        d.rounded_rectangle((lx, ly, lx + 24, ly + 16), radius=4, fill=color)
        d.text((lx + 34, ly - 4), label, fill=INK, font=FONT_XS)
        lx += 150
    d.text((left, 820 - 42), "单位：元/月", fill=MUTED, font=FONT_SM)
    save(img, "图3-16_城市收入成本差异对比图.png")


def main() -> None:
    rows = read_csv(PANEL)
    jobs = read_csv(JOBS)

    horizontal_bar(
        sorted([(r["city_name_zh"], num(r, "population_2020") / 10000) for r in rows], key=lambda x: x[1])[-10:],
        "图3-4_人口规模对比图.png",
        "万人",
        " 万人",
    )

    region_values: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        region_values[r["region"]].append(num(r, "monthly_balance_after_rent_cost_rmb"))
    vertical_bar(
        sorted([(k, sum(v) / len(v)) for k, v in region_values.items()], key=lambda x: x[1]),
        "图3-5_区域平均月结余对比图.png",
        "元/月",
        " 元",
    )

    horizontal_bar(
        sorted([(r["city_name_zh"], num(r, "avg_salary")) for r in rows], key=lambda x: x[1]),
        "图3-6_城市平均薪资对比图.png",
        "元/月",
        " 元",
        height=900,
    )

    horizontal_bar(
        sorted([(r["city_name_zh"], num(r, "job_market_proxy") * 100) for r in rows], key=lambda x: x[1])[-10:],
        "图3-7_就业热度代理指标对比图.png",
        "指数（0-100）",
        "",
    )

    stacked_industry(jobs)
    top_position_salary(jobs)
    education_pie(jobs)

    horizontal_bar(
        sorted([(r["city_name_zh"], num(r, "monthly_cost_single_rmb")) for r in rows], key=lambda x: x[1]),
        "图3-11_单人月生活成本对比图.png",
        "元/月",
        " 元",
        height=900,
    )

    horizontal_bar(
        sorted([(r["city_name_zh"], num(r, "rent_1br_city_centre_rmb")) for r in rows], key=lambda x: x[1]),
        "图3-12_市中心一居室租金对比图.png",
        "元/月",
        " 元",
        height=900,
    )

    scatter(
        rows,
        "monthly_cost_single_rmb",
        "rent_1br_city_centre_rmb",
        "图3-13_生活成本与租房压力对比图.png",
        "元/月",
        "元/月",
        "单人月生活成本",
        "市中心一居室租金",
        label_offsets={
            "天津": (-60, 8),
            "郑州": (-58, -18),
            "东莞": (18, -6),
            "厦门": (18, 18),
            "青岛": (18, 8),
            "宁波": (18, -14),
            "重庆": (-58, 8),
            "成都": (-58, -16),
            "合肥": (-58, 8),
            "长沙": (18, 8),
        },
    )

    scatter(
        rows,
        "monthly_cost_single_rmb",
        "avg_salary",
        "图3-14_税后月薪与生活成本散点图.png",
        "元/月",
        "元/月",
        "单人月生活成本",
        "税后月薪",
        label_offsets={
            "天津": (-58, 10),
            "郑州": (-58, -20),
            "东莞": (18, -4),
            "厦门": (18, 18),
            "青岛": (18, 8),
            "宁波": (18, -16),
            "重庆": (-58, 8),
            "成都": (-58, -16),
            "合肥": (-58, 10),
            "长沙": (18, 8),
        },
    )

    horizontal_bar(
        sorted([(r["city_name_zh"], num(r, "monthly_balance_after_rent_cost_rmb")) for r in rows], key=lambda x: x[1]),
        "图3-15_实际月结余排名图.png",
        "元/月",
        " 元",
        height=900,
        allow_negative=True,
    )

    grouped_income_cost(rows)

    scatter(
        rows,
        "avg_salary",
        "monthly_balance_after_rent_cost_rmb",
        "图3-17_城市类型四象限图.png",
        "元/月",
        "元/月",
        "税后月薪",
        "实际月结余",
        quadrant=True,
        label_offsets={
            "北京": (18, 8),
            "上海": (18, 8),
            "深圳": (-58, -16),
            "广州": (-54, -10),
            "杭州": (26, -28),
            "南京": (24, -54),
            "苏州": (38, 42),
            "成都": (-72, -38),
            "宁波": (52, -24),
            "青岛": (52, -2),
            "重庆": (-54, -12),
            "武汉": (-82, 22),
            "西安": (-80, -24),
            "天津": (-84, -56),
            "郑州": (-92, -10),
            "长沙": (18, 8),
            "东莞": (52, 20),
            "厦门": (18, 50),
            "合肥": (-58, -14),
            "佛山": (-58, 12),
        },
    )


if __name__ == "__main__":
    main()
