#!/usr/bin/env python3
"""Professional black stick-figure cartoon for Taxi and Fly.

home → call app → taxi pickup → drive → happy airport drop-off → brand.
Video length follows the voiceover so nothing is cut off.
"""

from __future__ import annotations

import asyncio
import math
import shutil
import sys
import time
from pathlib import Path

import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build" / "stick"
ART = Path("/opt/cursor/artifacts")

sys.path.insert(0, str(ROOT))
from add_pretty_music import pretty_music  # noqa: E402
from build_video import FONT, FONT_REG, duration, ff, mix  # noqa: E402
from rebuild_brand_process import icon_lettering  # noqa: E402
from spot_audio import logo_sting, reggae_music  # noqa: E402

W, H, FPS = 1080, 1920, 30
# Peppa-like bright cartoon palette
GOLD = (255, 210, 40)
WHITE = (255, 255, 255)
INK = (40, 30, 40)
SOFT_INK = (90, 70, 90)
TAXI = (255, 214, 10)
ROAD = (170, 165, 160)
SKY_TOP = (120, 198, 235)
SKY_BOT = (185, 225, 245)
ROOM = (255, 236, 220)
GRASS = (110, 196, 80)
HILL = (90, 176, 70)
HILL2 = (130, 210, 95)
HOUSE_WALL = (255, 245, 230)
ROOF = (230, 70, 85)
WINDOW = (120, 210, 255)
DOOR = (255, 160, 70)
CLOUD = (255, 255, 255)
CAPTION_BG = (255, 248, 170)
SHADOW = (0, 0, 0, 40)
VOICE = "el-GR-NestorasNeural"
RATE = "-16%"  # slower, clearer
TAIL = 1.4
LINE_GAP = 0.55  # pause between spoken lines

# 3 simple spots. On-screen text = exactly what is spoken.
# Each beat: scene key + one clear Greek line.
VARIANTS = {
    # 1) Wherever you are → appointment / destination
    "rantevou": {
        "out": ROOT / "taxi-and-fly-stick-rantevou.mp4",
        "art": "taxi_and_fly_stick_rantevou.mp4",
        "download": "stick-rantevou.mp4",
        "brand_lines": ["Από και προς το αεροδρόμιο"],
        "beats": [
            ("start_city", "Όπου κι αν βρίσκεσαι"),
            ("call", "Κλείσε Taxi and Fly"),
            ("pickup_city", "Έρχεται το ταξί"),
            (
                "drive",
                "Σε πάει με πιστοποιημένους οδηγούς ταξί\nμε ασφάλεια στον προορισμό σου",
            ),
        ],
    },
    # 2) Arrive Athens (El. Venizelos) → your destination
    "prosgeiosi": {
        "out": ROOT / "taxi-and-fly-stick-prosgeiosi.mp4",
        "art": "taxi_and_fly_stick_prosgeiosi.mp4",
        "download": "stick-prosgeiosi.mp4",
        "brand_lines": ["Από και προς το αεροδρόμιο"],
        "beats": [
            ("start_airport", "Έρχεσαι Αθήνα στο Ελ Βενιζέλος"),
            ("call", "Θες να πας στον προορισμό σου"),
            ("call", "Κλείσε Taxi and Fly"),
            ("pickup_airport", "Έρχεται το ταξί"),
            (
                "drive",
                "Σε πάει με πιστοποιημένους οδηγούς ταξί\nμε ασφάλεια στον προορισμό σου",
            ),
        ],
    },
    # 3) In Athens → airport
    "athina-aerodromio": {
        "out": ROOT / "taxi-and-fly-stick-athina-aerodromio.mp4",
        "art": "taxi_and_fly_stick_athina_aerodromio.mp4",
        "download": "stick-athina-aerodromio.mp4",
        "brand_lines": ["Από και προς το αεροδρόμιο"],
        "beats": [
            ("start_city", "Είσαι στην Αθήνα"),
            ("call", "Θες να πας στο αεροδρόμιο"),
            ("call", "Κλείσε Taxi and Fly"),
            ("pickup_city", "Έρχεται το ταξί"),
            (
                "drive",
                "Σε πάει με πιστοποιημένους οδηγούς ταξί\nμε ασφάλεια στο αεροδρόμιο",
            ),
        ],
    },
    # 4) Landed calm booking vs stressed crowd looking for taxis
    "eftasa": {
        "out": ROOT / "taxi-and-fly-stick-eftasa.mp4",
        "art": "taxi_and_fly_stick_eftasa.mp4",
        "download": "stick-eftasa.mp4",
        "brand_lines": ["Από και προς το αεροδρόμιο"],
        "hold": 1.25,  # calmer pacing — let the contrast breathe
        "music": "happy",  # sunny reggae bed
        "beats": [
            ("plane_land", "Προσγειώνεσαι"),
            ("arrivals_stress", "Οι άλλοι ψάχνουν ταξί\nκαι δεν βρίσκουν"),
            (
                "you_smile",
                "Εσύ περνάς ανέμελος\nγιατί ξέρεις ότι ένας οδηγός ταξί σε περιμένει",
            ),
            (
                "press_eftasa",
                "Πατάς το κουμπί «Έφτασα»\nνα έρθει ο οδηγός να σε πάρει",
            ),
            ("send_exit", "Διαλέγεις έξοδο από 1 έως 5\nκαι τη στέλνεις στον οδηγό"),
            ("calm_taxi", "Το ταξί είναι καθ' οδόν"),
            ("relax_end", "Φεύγεις άνετα\nτόσο απλά και ξεκούραστα"),
        ],
    },
}


def ease(k: float) -> float:
    k = max(0.0, min(k, 1.0))
    return 1 - (1 - k) ** 3


def lerp(a: float, b: float, k: float) -> float:
    return a + (b - a) * k


def mix_rgb(a, b, k: float):
    k = max(0.0, min(k, 1.0))
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def sky_bg() -> Image.Image:
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        k = y / (H - 1)
        arr[y, :] = mix_rgb(SKY_TOP, SKY_BOT, min(k * 1.15, 1.0))
    img = Image.fromarray(arr, "RGB").convert("RGBA")
    draw = ImageDraw.Draw(img)
    # fluffy Peppa-style clouds
    for cx, cy, s in ((180, 220, 1.0), (520, 160, 1.25), (860, 250, 0.9), (700, 340, 0.7)):
        for ox, oy, r in ((0, 0, 55), (-48, 10, 42), (48, 12, 44), (-10, -28, 36), (30, -22, 34)):
            draw.ellipse(
                (cx + ox * s - r * s, cy + oy * s - r * s, cx + ox * s + r * s, cy + oy * s + r * s),
                fill=CLOUD + (255,),
            )
    return img


def peppa_hills(base: Image.Image) -> None:
    draw = ImageDraw.Draw(base)
    draw.ellipse((-220, 1080, 720, 1680), fill=HILL + (255,))
    draw.ellipse((380, 1120, 1320, 1720), fill=HILL2 + (255,))


def airport_asphalt(base: Image.Image, y0: int = 1280) -> None:
    """Cartoon grey curb / taxi lane — airport ground, not grass."""
    draw = ImageDraw.Draw(base)
    draw.rectangle((0, y0, W, H), fill=(165, 168, 172, 255))
    # lighter sidewalk strip
    draw.rectangle((0, y0, W, y0 + 70), fill=(210, 212, 216, 255))
    # yellow curb
    draw.rectangle((0, y0 + 70, W, y0 + 95), fill=GOLD + (255,))
    draw.rectangle((0, y0 + 95, W, y0 + 102), fill=INK + (255,))
    # lane dashes
    for i in range(9):
        x = 40 + i * 120
        draw.rectangle((x, y0 + 220, x + 70, y0 + 245), fill=WHITE + (255,))


def cartoon_arrivals_facade(base: Image.Image) -> None:
    """Cartoon glass arrivals doors + ΑΦΙΞΕΙΣ sign (Peppa-style)."""
    draw = ImageDraw.Draw(base)
    # canopy first so the sign sits on top
    draw.polygon([(20, 780), (W / 2, 640), (W - 20, 780)], fill=(255, 190, 150, 255), outline=INK)
    draw.line([(20, 780), (W / 2, 640), (W - 20, 780)], fill=INK, width=6)
    # terminal facade band
    draw.rounded_rectangle((40, 780, W - 40, 1180), radius=28, fill=(255, 250, 235, 255), outline=INK, width=7)
    # glass door panes
    for i in range(4):
        x0 = 80 + i * 240
        draw.rounded_rectangle((x0, 860, x0 + 210, 1160), radius=18, fill=WINDOW + (255,), outline=INK, width=5)
        draw.line((x0 + 105, 860, x0 + 105, 1160), fill=INK, width=4)
        # door handle
        draw.ellipse((x0 + 90, 1000, x0 + 120, 1030), fill=GOLD, outline=INK, width=3)
    # ΑΦΙΞΕΙΣ sign on the canopy face
    f = ImageFont.truetype(FONT, 40)
    t = "ΑΦΙΞΕΙΣ"
    tw = draw.textlength(t, font=f)
    draw.rounded_rectangle(
        ((W - tw) / 2 - 36, 680, (W + tw) / 2 + 36, 760),
        radius=20,
        fill=(255, 90, 90, 255),
        outline=INK,
        width=5,
    )
    draw.text(((W - tw) / 2, 698), t, font=f, fill=WHITE)


def room_bg() -> Image.Image:
    img = Image.new("RGBA", (W, H), ROOM + (255,))
    draw = ImageDraw.Draw(img)
    # warm peppa indoor wall + dotted wallpaper
    draw.rectangle((0, 0, W, 90), fill=(255, 200, 160, 255))
    for y in range(140, 1400, 70):
        for x in range(40, W, 70):
            draw.ellipse((x, y, x + 10, y + 10), fill=(255, 190, 170, 255))
    draw.rectangle((0, 1480, W, H), fill=(255, 210, 180, 255))
    return img


def put_shadow(base: Image.Image, cx: float, cy: float, rx: float, ry: float) -> None:
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=SHADOW)
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))


def rounded_line(draw, a, b, width: int, fill=INK) -> None:
    draw.line([a, b], fill=fill, width=width)
    r = width / 2
    for x, y in (a, b):
        draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def stick(
    base: Image.Image,
    cx: float,
    cy: float,
    scale: float = 1.0,
    wave: float = 0.0,
    smile: bool = False,
    walk: float = 0.0,
) -> None:
    """Black stick person with big round Peppa-like head. cy = feet."""
    draw = ImageDraw.Draw(base)
    s = scale
    head_r = 42 * s
    body = 88 * s
    arm = 70 * s
    leg = 78 * s
    thick = max(10, int(12 * s))
    phase = walk * math.pi * 2
    hip_y = cy - leg
    shoulder_y = hip_y - body
    head_y = shoulder_y - head_r + 2 * s

    put_shadow(base, cx, cy + 6, 52 * s, 16 * s)

    # big round white head, thick black outline
    draw.ellipse(
        (cx - head_r, head_y - head_r, cx + head_r, head_y + head_r),
        fill=WHITE,
        outline=INK,
        width=thick,
    )
    # simple oval eyes + rosy cheeks
    er = max(3, int(4.2 * s))
    draw.ellipse((cx - 14 * s - er, head_y - 6 * s - er, cx - 14 * s + er, head_y - 6 * s + er), fill=INK)
    draw.ellipse((cx + 14 * s - er, head_y - 6 * s - er, cx + 14 * s + er, head_y - 6 * s + er), fill=INK)
    draw.ellipse((cx - 28 * s, head_y + 8 * s, cx - 14 * s, head_y + 20 * s), fill=(255, 170, 170, 255))
    draw.ellipse((cx + 14 * s, head_y + 8 * s, cx + 28 * s, head_y + 20 * s), fill=(255, 170, 170, 255))
    if smile:
        draw.arc(
            (cx - 18 * s, head_y + 2 * s, cx + 18 * s, head_y + 24 * s),
            15,
            165,
            fill=INK,
            width=max(4, int(5 * s)),
        )

    rounded_line(draw, (cx, head_y + head_r - 2 * s), (cx, hip_y), thick)
    swing = math.sin(phase) * 16 if walk else 0
    rounded_line(
        draw,
        (cx, shoulder_y + 14 * s),
        (cx - arm * 0.9, shoulder_y + arm * 0.6 - swing),
        thick,
    )
    ax = cx + arm * math.cos(math.radians(-20 + wave * 55 + swing * 0.4))
    ay = shoulder_y + 14 * s + arm * math.sin(math.radians(50 - wave * 40))
    rounded_line(draw, (cx, shoulder_y + 14 * s), (ax, ay), thick)
    leg_swing = math.sin(phase) * 20 if walk else 0
    rounded_line(draw, (cx, hip_y), (cx - 28 * s - leg_swing * 0.3, cy), thick)
    rounded_line(draw, (cx, hip_y), (cx + 28 * s + leg_swing * 0.3, cy), thick)


def house(base: Image.Image, x: float, y: float, w: float = 380, h: float = 310) -> None:
    draw = ImageDraw.Draw(base)
    put_shadow(base, x + w / 2, y + h + 18, w * 0.48, 22)
    roof_h = h * 0.48
    # chubby peppa house body
    draw.rounded_rectangle((x, y, x + w, y + h), radius=28, outline=INK, width=8, fill=HOUSE_WALL)
    # round red roof
    draw.polygon(
        [(x - 36, y + 18), (x + w / 2, y - roof_h), (x + w + 36, y + 18)],
        fill=ROOF,
        outline=INK,
    )
    draw.line([(x - 36, y + 18), (x + w / 2, y - roof_h), (x + w + 36, y + 18)], fill=INK, width=8)
    # chimney with puff
    draw.rounded_rectangle(
        (x + w * 0.72, y - roof_h + 50, x + w * 0.72 + 42, y + 8),
        radius=8,
        fill=(255, 190, 120),
        outline=INK,
        width=5,
    )
    draw.ellipse((x + w * 0.72 + 30, y - roof_h + 10, x + w * 0.72 + 70, y - roof_h + 45), fill=CLOUD, outline=INK, width=3)
    # door
    dw, dh = 86, 140
    dx = x + w / 2 - dw / 2
    draw.rounded_rectangle((dx, y + h - dh, dx + dw, y + h), radius=40, outline=INK, width=6, fill=DOOR)
    draw.ellipse((dx + dw - 24, y + h - dh / 2 - 8, dx + dw - 8, y + h - dh / 2 + 8), fill=GOLD, outline=INK, width=3)
    # round windows
    for wx in (x + 40, x + w - 40 - 86):
        draw.ellipse((wx, y + 55, wx + 86, y + 141), outline=INK, width=6, fill=WINDOW)
        draw.line((wx + 43, y + 55, wx + 43, y + 141), fill=INK, width=4)
        draw.line((wx, y + 98, wx + 86, y + 98), fill=INK, width=4)


def phone(base: Image.Image, cx: float, cy: float, lit: bool = True, bounce: float = 0.0) -> None:
    draw = ImageDraw.Draw(base)
    pw, ph = 150, 270
    x0, y0 = cx - pw / 2, cy - ph / 2 + bounce
    put_shadow(base, cx, y0 + ph + 10, 70, 16)
    draw.rounded_rectangle((x0 - 4, y0 - 4, x0 + pw + 4, y0 + ph + 4), radius=30, fill=(0, 0, 0, 40))
    draw.rounded_rectangle((x0, y0, x0 + pw, y0 + ph), radius=28, fill=INK)
    screen = GOLD if lit else (35, 35, 38)
    draw.rounded_rectangle((x0 + 12, y0 + 28, x0 + pw - 12, y0 + ph - 34), radius=16, fill=screen)
    # notch
    draw.rounded_rectangle((cx - 22, y0 + 12, cx + 22, y0 + 22), radius=4, fill=(50, 50, 50))
    if lit:
        f = ImageFont.truetype(FONT, 20)
        t = "Taxi and Fly"
        tw = draw.textlength(t, font=f)
        draw.text((cx - tw / 2, cy - 8 + bounce), t, font=f, fill=INK)
        # app glyph ring
        draw.ellipse((cx - 34, cy - 70 + bounce, cx + 34, cy - 2 + bounce), outline=INK, width=4)
        f2 = ImageFont.truetype(FONT, 14)
        for i, word in enumerate(("Taxi", "Fly")):
            ww = draw.textlength(word, font=f2)
            draw.text((cx - ww / 2, cy - 58 + bounce + i * 18), word, font=f2, fill=INK)


def taxi_car(base: Image.Image, cx: float, cy: float, scale: float = 1.0, wheel_spin: float = 0.0) -> None:
    draw = ImageDraw.Draw(base)
    s = scale
    body_w, body_h = 270 * s, 90 * s
    cabin_w, cabin_h = 160 * s, 70 * s
    x0 = cx - body_w / 2
    y0 = cy - body_h
    put_shadow(base, cx, cy + 8, body_w * 0.42, 18 * s)

    # chubby cartoon taxi
    draw.rounded_rectangle((x0, y0, x0 + body_w, y0 + body_h), radius=40, fill=TAXI, outline=INK, width=8)
    draw.rounded_rectangle(
        (cx - cabin_w / 2, y0 - cabin_h + 20, cx + cabin_w / 2, y0 + 20),
        radius=32,
        fill=TAXI,
        outline=INK,
        width=8,
    )
    draw.ellipse(
        (cx - cabin_w / 2 + 16, y0 - cabin_h + 30, cx - 4, y0 + 8),
        fill=WINDOW,
        outline=INK,
        width=4,
    )
    draw.ellipse(
        (cx + 4, y0 - cabin_h + 30, cx + cabin_w / 2 - 16, y0 + 8),
        fill=WINDOW,
        outline=INK,
        width=4,
    )
    draw.ellipse((x0 + 14, y0 + 30, x0 + 42, y0 + 58), fill=WHITE, outline=INK, width=3)
    draw.ellipse((x0 + body_w - 42, y0 + 30, x0 + body_w - 14, y0 + 58), fill=(255, 140, 90), outline=INK, width=3)

    for wx in (cx - 78 * s, cx + 78 * s):
        draw.ellipse((wx - 30 * s, cy - 30 * s, wx + 30 * s, cy + 30 * s), fill=INK)
        draw.ellipse((wx - 14 * s, cy - 14 * s, wx + 14 * s, cy + 14 * s), fill=(255, 230, 80))
        ang = wheel_spin * 360
        for a in (ang, ang + 90):
            rad = math.radians(a)
            draw.line(
                (wx, cy, wx + 11 * s * math.cos(rad), cy + 11 * s * math.sin(rad)),
                fill=SOFT_INK,
                width=3,
            )

    draw.rounded_rectangle(
        (cx - 40 * s, y0 - cabin_h - 14 * s, cx + 40 * s, y0 - cabin_h + 10),
        radius=12,
        fill=WHITE,
        outline=INK,
        width=5,
    )
    f = ImageFont.truetype(FONT, max(16, int(20 * s)))
    tw = draw.textlength("TAXI", font=f)
    draw.text((cx - tw / 2, y0 - cabin_h - 12 * s), "TAXI", font=f, fill=INK)


def suitcase(base: Image.Image, x: float, y: float, scale: float = 1.0) -> None:
    draw = ImageDraw.Draw(base)
    s = scale
    put_shadow(base, x + 28 * s, y + 78 * s, 30 * s, 10 * s)
    draw.rounded_rectangle((x, y, x + 60 * s, y + 76 * s), radius=16, outline=INK, width=5, fill=(255, 120, 150))
    draw.line((x + 14 * s, y - 18 * s, x + 46 * s, y - 18 * s), fill=INK, width=6)
    draw.line((x + 14 * s, y - 18 * s, x + 14 * s, y), fill=INK, width=6)
    draw.line((x + 46 * s, y - 18 * s, x + 46 * s, y), fill=INK, width=6)
    draw.ellipse((x + 20 * s, y + 28 * s, x + 40 * s, y + 48 * s), fill=GOLD, outline=INK, width=3)


def airport(base: Image.Image) -> None:
    draw = ImageDraw.Draw(base)
    put_shadow(base, W / 2, 1295, 420, 24)
    # pastel peppa terminal
    draw.rounded_rectangle((90, 960, 990, 1290), radius=36, fill=(255, 250, 235), outline=INK, width=8)
    draw.polygon([(70, 968), (540, 760), (1010, 968)], fill=(255, 170, 180), outline=INK)
    draw.line([(70, 968), (540, 760), (1010, 968)], fill=INK, width=8)
    draw.rounded_rectangle((850, 700, 910, 960), radius=16, fill=(255, 210, 120), outline=INK, width=5)
    draw.ellipse((825, 640, 935, 730), fill=GOLD, outline=INK, width=5)
    for i in range(3):
        x = 230 + i * 200
        draw.rounded_rectangle((x, 1060, x + 150, 1290), radius=20, outline=INK, width=5, fill=WINDOW)
        draw.line((x + 75, 1060, x + 75, 1290), fill=INK, width=4)
    # friendly plane
    px, py = 200, 620
    draw.ellipse((px, py, px + 200, py + 50), fill=WHITE, outline=INK, width=5)
    draw.polygon([(px + 50, py + 12), (px + 20, py - 40), (px + 90, py + 12)], fill=(255, 170, 180), outline=INK)
    draw.polygon([(px + 120, py + 18), (px + 180, py + 72), (px + 105, py + 28)], fill=(255, 170, 180), outline=INK)
    f = ImageFont.truetype(FONT, 40)
    t = "ΑΕΡΟΔΡΟΜΙΟ"
    tw = draw.textlength(t, font=f)
    draw.rounded_rectangle(((W - tw) / 2 - 28, 870, (W + tw) / 2 + 28, 945), radius=22, fill=CAPTION_BG, outline=INK, width=5)
    draw.text(((W - tw) / 2, 885), t, font=f, fill=INK)


def fit_text(draw: ImageDraw.ImageDraw, text: str, font, max_w: float) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Shrink title a bit if a long Greek line would overflow."""
    size = getattr(font, "size", 50)
    path = FONT
    for s in range(int(size), 34, -2):
        f = ImageFont.truetype(path, s)
        if draw.textlength(text, font=f) <= max_w:
            return f
    return ImageFont.truetype(path, 34)


def caption(base: Image.Image, text: str, y: int = 140, sub: str | None = None) -> None:
    draw = ImageDraw.Draw(base)
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()] or [text]
    f = ImageFont.truetype(FONT, 44 if len(lines) > 1 else 48)
    # Shrink until every line fits.
    for size in range(getattr(f, "size", 48), 30, -2):
        f = ImageFont.truetype(FONT, size)
        if all(draw.textlength(ln, font=f) <= 920 for ln in lines):
            break
    widths = [draw.textlength(ln, font=f) for ln in lines]
    tw = max(widths)
    line_h = int(getattr(f, "size", 44) + 10)
    pad_x, pad_y = 32, 18
    box_h = len(lines) * line_h + pad_y
    box = ((W - tw) / 2 - pad_x, y - pad_y, (W + tw) / 2 + pad_x, y + box_h)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (box[0] + 4, box[1] + 6, box[2] + 4, box[3] + 6), radius=22, fill=(0, 0, 0, 40)
    )
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(4)))
    draw.rounded_rectangle(box, radius=28, fill=CAPTION_BG, outline=INK, width=5)
    for i, ln in enumerate(lines):
        lw = widths[i]
        draw.text(((W - lw) / 2, y + i * line_h), ln, font=f, fill=INK)
    if sub:
        fs = fit_text(draw, sub, ImageFont.truetype(FONT_REG, 34), 960)
        sw = draw.textlength(sub, font=fs)
        draw.text(((W - sw) / 2, box[3] + 16), sub, font=fs, fill=SOFT_INK)


def road_layer(base: Image.Image, y0: int = 1280, scroll: float = 0.0) -> None:
    """Soft Peppa-style path on grass — not a real highway."""
    draw = ImageDraw.Draw(base)
    draw.rectangle((0, y0, W, H), fill=GRASS)
    # wide rounded dirt/path band
    draw.rounded_rectangle((40, y0 + 80, W - 40, H - 40), radius=80, fill=(210, 185, 140), outline=INK, width=6)
    for i in range(10):
        x = (i * 140 - int(scroll) % 140)
        draw.ellipse((x + 40, y0 + 200, x + 100, y0 + 240), fill=(230, 210, 170))


BADGE = None


def brand_end(t: float, start: float, lines: list[str]) -> Image.Image:
    global BADGE
    if BADGE is None:
        size = 560
        mark = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(mark)
        d.ellipse((12, 12, size - 12, size - 12), outline=GOLD + (255,), width=18)
        letters = icon_lettering()
        inner = int(size * 0.58)
        sc = min(inner / letters.width, inner / letters.height)
        letters = letters.resize(
            (max(1, int(letters.width * sc)), max(1, int(letters.height * sc))),
            Image.Resampling.LANCZOS,
        )
        mark.alpha_composite(letters, ((size - letters.width) // 2, (size - letters.height) // 2))
        BADGE = mark

    img = Image.new("RGBA", (W, H), (8, 8, 8, 255))
    yy, xx = np.mgrid[0:H, 0:W]
    dmap = np.sqrt(((xx - W / 2) / 500.0) ** 2 + ((yy - 780) / 680.0) ** 2)
    a = np.clip(1.0 - dmap, 0.0, 1.0) ** 2.3 * 78
    glow = np.zeros((H, W, 4), dtype=np.uint8)
    glow[..., 0], glow[..., 1], glow[..., 2] = GOLD
    glow[..., 3] = a.astype(np.uint8)
    img.alpha_composite(Image.fromarray(glow, "RGBA"))

    since = max(t - start, 0.0)
    k = ease(min(since / 0.55, 1.0))
    size = int(560 * (0.90 + 0.10 * k))
    mark = BADGE.resize((size, size), Image.Resampling.LANCZOS)
    img.alpha_composite(mark, ((W - size) // 2, 380))

    draw = ImageDraw.Draw(img)
    f_brand = ImageFont.truetype(FONT, 80)
    f_line = ImageFont.truetype(FONT_REG, 42)
    f_url = ImageFont.truetype(FONT_REG, 30)
    fade = ease(min(max((since - 0.2) / 0.45, 0.0), 1.0))
    bw = draw.textlength("Taxi and Fly", font=f_brand)
    draw.text(((W - bw) / 2, 980), "Taxi and Fly", font=f_brand, fill=GOLD + (255,))
    y = 1105
    for line in lines:
        tw = draw.textlength(line, font=f_line)
        draw.text(((W - tw) / 2, y), line, font=f_line, fill=WHITE + (int(245 * fade),))
        y += 56
    uw = draw.textlength("taxiapp2026.github.io/taxi-client-app", font=f_url)
    draw.text(
        ((W - uw) / 2, y + 36),
        "taxiapp2026.github.io/taxi-client-app",
        font=f_url,
        fill=(160, 160, 160, int(230 * fade)),
    )
    return img


def scene_start_city(local: float, dur: float, line: str) -> Image.Image:
    img = sky_bg()
    peppa_hills(img)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 1340, W, H), fill=GRASS)
    house(img, 170, 760)
    k = ease(min(local / max(dur * 0.75, 0.1), 1.0))
    x = lerp(700, 780, k)
    walk = local * 1.1 if local < dur * 0.75 else 0.0
    stick(img, x, 1370, scale=1.25, walk=walk)
    suitcase(img, x + 62, 1295, scale=1.05)
    caption(img, line)
    return img


def scene_start_airport(local: float, dur: float, line: str) -> Image.Image:
    img = sky_bg()
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 1320, W, H), fill=GRASS)
    airport(img)
    k = ease(min(local / max(dur * 0.75, 0.1), 1.0))
    x = lerp(520, 640, k)
    stick(img, x, 1560, scale=1.25, walk=local * 1.0 if local < dur * 0.75 else 0.0, smile=True)
    suitcase(img, x + 62, 1485, scale=1.05)
    caption(img, line)
    return img


def scene_call(local: float, dur: float, line: str) -> Image.Image:
    img = room_bg()
    bob = math.sin(local * 4.2) * 8
    phone(img, W / 2, 720, lit=True, bounce=bob)
    stick(img, W / 2, 1520, scale=1.15)
    draw = ImageDraw.Draw(img)
    for i in range(3):
        pulse = 0.4 + 0.6 * abs(math.sin(local * 5 + i))
        r = 8 + 4 * pulse
        x = W / 2 + 110 + i * 28
        draw.ellipse(
            (x - r, 640 - r + bob, x + r, 640 + r + bob),
            fill=mix_rgb(GOLD, (255, 255, 255), 1 - pulse) + (255,),
        )
    caption(img, line)
    return img


def scene_pickup_city(local: float, dur: float, line: str) -> Image.Image:
    """Taxi arrives at the house — grass yard, no highway."""
    img = sky_bg()
    peppa_hills(img)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 1340, W, H), fill=GRASS)
    # little flowers
    for fx, fy, col in ((120, 1420, (255, 120, 160)), (260, 1480, (255, 220, 80)), (940, 1450, (255, 140, 180))):
        draw.ellipse((fx, fy, fx + 28, fy + 28), fill=col, outline=INK, width=3)
    house(img, 140, 780)
    k = ease(min(local / (dur * 0.65), 1.0))
    car_x = lerp(-220, 560, k)
    taxi_car(img, car_x, 1505, scale=1.2, wheel_spin=local * 1.6)
    if local < dur * 0.78:
        stick(img, 820, 1505, scale=1.2)
        suitcase(img, 880, 1430, scale=1.0)
    else:
        board = ease((local - dur * 0.78) / max(dur * 0.22, 0.01))
        stick(img, lerp(820, 600, board), 1505, scale=1.08)
    caption(img, line)
    return img


def scene_pickup_airport(local: float, dur: float, line: str) -> Image.Image:
    """Taxi arrives at the airport front — terminal + grass, no highway."""
    img = sky_bg()
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 1320, W, H), fill=GRASS)
    airport(img)
    k = ease(min(local / (dur * 0.65), 1.0))
    car_x = lerp(-220, 500, k)
    taxi_car(img, car_x, 1565, scale=1.15, wheel_spin=local * 1.6)
    if local < dur * 0.78:
        stick(img, 780, 1565, scale=1.2)
        suitcase(img, 840, 1490, scale=1.0)
    else:
        board = ease((local - dur * 0.78) / max(dur * 0.22, 0.01))
        stick(img, lerp(780, 560, board), 1565, scale=1.08)
    caption(img, line)
    return img


def scene_drive(local: float, dur: float, line: str) -> Image.Image:
    img = sky_bg()
    draw = ImageDraw.Draw(img)
    offset = int(local * 160) % 900
    draw.ellipse((-200 - offset, 980, 520 - offset, 1500), fill=HILL)
    draw.ellipse((500 - offset * 0.6, 1020, 1300 - offset * 0.6, 1520), fill=HILL2)
    road_layer(img, 1240, scroll=local * 480)
    bounce = math.sin(local * 12) * 4
    taxi_car(img, 540, 1475 + bounce, scale=1.4, wheel_spin=local * 3.5)
    draw.ellipse((505, 1335 + bounce, 548, 1378 + bounce), fill=WHITE, outline=INK, width=5)
    caption(img, line)
    return img


def _angry_stick(
    base: Image.Image,
    cx: float,
    cy: float,
    scale: float = 0.9,
    shake: float = 0.0,
    tired: bool = False,
) -> None:
    """Stressed person: frown + phone up + optional sweat/tired marks."""
    draw = ImageDraw.Draw(base)
    s = scale
    jx = math.sin(shake * 14) * 5 + math.sin(shake * 29) * 2
    head_r = 34 * s
    body = 70 * s
    leg = 64 * s
    thick = max(8, int(10 * s))
    hip_y = cy - leg
    shoulder_y = hip_y - body
    head_y = shoulder_y - head_r
    cx = cx + jx
    put_shadow(base, cx, cy + 4, 40 * s, 12 * s)
    draw.ellipse((cx - head_r, head_y - head_r, cx + head_r, head_y + head_r), fill=WHITE, outline=INK, width=thick)
    er = max(2, int(3.5 * s))
    draw.ellipse((cx - 12 * s - er, head_y - 4 * s - er, cx - 12 * s + er, head_y - 4 * s + er), fill=INK)
    draw.ellipse((cx + 12 * s - er, head_y - 4 * s - er, cx + 12 * s + er, head_y - 4 * s + er), fill=INK)
    # frown
    draw.arc((cx - 14 * s, head_y + 10 * s, cx + 14 * s, head_y + 28 * s), 200, 340, fill=INK, width=max(3, int(4 * s)))
    # angry brows
    draw.line((cx - 18 * s, head_y - 12 * s, cx - 6 * s, head_y - 6 * s), fill=INK, width=4)
    draw.line((cx + 6 * s, head_y - 6 * s, cx + 18 * s, head_y - 12 * s), fill=INK, width=4)
    # sweat drops / fatigue
    if tired:
        for sx, sy in ((-22, -8), (-28, 6), (26, -4)):
            draw.ellipse(
                (cx + sx * s, head_y + sy * s, cx + (sx + 8) * s, head_y + (sy + 14) * s),
                fill=(120, 200, 255),
                outline=INK,
                width=2,
            )
        # zig-zag frustration above head
        zx, zy = cx - 8 * s, head_y - head_r - 28 * s
        draw.line(
            [(zx, zy + 18), (zx + 10, zy), (zx + 2, zy + 10), (zx + 16, zy - 6)],
            fill=(230, 60, 70),
            width=4,
        )
    rounded_line(draw, (cx, head_y + head_r), (cx, hip_y), thick)
    # phone raised — red fail screen
    px, py = cx + 38 * s, shoulder_y - 10 * s
    draw.rounded_rectangle((px, py, px + 28 * s, py + 48 * s), radius=6, fill=INK)
    draw.rounded_rectangle((px + 4 * s, py + 6 * s, px + 24 * s, py + 38 * s), radius=4, fill=(255, 100, 100))
    # big X on phone = no taxi found
    draw.line((px + 8 * s, py + 12 * s, px + 20 * s, py + 30 * s), fill=WHITE, width=3)
    draw.line((px + 20 * s, py + 12 * s, px + 8 * s, py + 30 * s), fill=WHITE, width=3)
    rounded_line(draw, (cx, shoulder_y + 8 * s), (px + 8 * s, py + 40 * s), thick)
    rounded_line(draw, (cx, shoulder_y + 8 * s), (cx - 40 * s, shoulder_y + 50 * s), thick)
    rounded_line(draw, (cx, hip_y), (cx - 22 * s, cy), thick)
    rounded_line(draw, (cx, hip_y), (cx + 22 * s, cy), thick)


def scene_plane_land(local: float, dur: float, line: str) -> Image.Image:
    img = sky_bg()
    draw = ImageDraw.Draw(img)
    # runway strip at bottom
    draw.rectangle((0, 1500, W, H), fill=(190, 195, 200))
    draw.rectangle((0, 1580, W, 1620), fill=GOLD)
    for i in range(8):
        x = 80 + i * 130
        draw.rectangle((x, 1680, x + 70, 1710), fill=WHITE)
    # plane descending slowly / calmly
    k = ease(min(local / max(dur * 0.9, 0.1), 1.0))
    px = lerp(-120, 620, k)
    py = lerp(520, 1180, k)
    draw.ellipse((px, py, px + 260, py + 70), fill=WHITE, outline=INK, width=6)
    draw.polygon([(px + 60, py + 15), (px + 20, py - 55), (px + 110, py + 15)], fill=(255, 170, 180), outline=INK)
    draw.polygon([(px + 150, py + 25), (px + 230, py + 95), (px + 130, py + 40)], fill=(255, 170, 180), outline=INK)
    draw.ellipse((px + 210, py + 10, px + 250, py + 50), fill=WINDOW, outline=INK, width=4)
    # little windows
    for i in range(4):
        wx = px + 70 + i * 30
        draw.ellipse((wx, py + 22, wx + 18, py + 42), fill=WINDOW, outline=INK, width=2)
    caption(img, line)
    return img


def scene_arrivals_stress(local: float, dur: float, line: str) -> Image.Image:
    """Crowd frantically searching apps — clearly failing to find a taxi."""
    img = sky_bg()
    draw = ImageDraw.Draw(img)
    airport_asphalt(img, y0=1180)
    cartoon_arrivals_facade(img)
    # big failed-search banner mid scene
    mid = local > dur * 0.35
    if mid:
        banner = "Δεν βρίσκουν ταξί…"
        fb = ImageFont.truetype(FONT, 34)
        bw = draw.textlength(banner, font=fb)
        draw.rounded_rectangle(
            ((W - bw) / 2 - 28, 1220, (W + bw) / 2 + 28, 1290),
            radius=18,
            fill=(255, 90, 90),
            outline=INK,
            width=4,
        )
        draw.text(((W - bw) / 2, 1235), banner, font=fb, fill=WHITE)
    # stressed crowd with phones — searching, failing, tired
    positions = (180, 360, 540, 720, 900)
    fail_labels = ("Uber?", "Bolt?", "Taxi??", "??? ", "0 διαθέσιμα")
    for i, x in enumerate(positions):
        _angry_stick(
            img,
            x,
            1580 + (i % 2) * 24,
            scale=0.85 + (i % 3) * 0.05,
            shake=local + i * 0.7,
            tired=True,
        )
        # app bubble that flips to FAIL / X
        bob = math.sin(local * 5 + i) * 8
        bx, by = x - 36, 1320 - (i % 3) * 36 + bob
        failed = (local + i * 0.35) % 2.4 > 1.1
        fill = (255, 160, 160) if failed else (255, 230, 180)
        draw.rounded_rectangle((bx, by, bx + 120, by + 48), radius=14, fill=fill, outline=INK, width=3)
        fs = ImageFont.truetype(FONT, 18)
        label = "✗ όχι" if failed else fail_labels[i % len(fail_labels)]
        lw = draw.textlength(label, font=fs)
        draw.text((bx + (120 - lw) / 2, by + 12), label, font=fs, fill=INK)
        if failed:
            # empty taxi silhouette with slash
            tx, ty = x - 10, 1450
            draw.ellipse((tx, ty, tx + 50, ty + 22), fill=(220, 220, 220), outline=INK, width=3)
            draw.line((tx - 4, ty + 24, tx + 54, ty - 2), fill=(220, 50, 60), width=5)
    caption(img, line)
    return img


def scene_you_smile(local: float, dur: float, line: str) -> Image.Image:
    """You stroll calmly past the stressed crowd — big contrast."""
    img = sky_bg()
    draw = ImageDraw.Draw(img)
    airport_asphalt(img, y0=1180)
    cartoon_arrivals_facade(img)
    # stressed people left/right — still failing, smaller / behind
    for i, x in enumerate((140, 280, 800, 940)):
        _angry_stick(img, x, 1520 + (i % 2) * 18, scale=0.72, shake=local + i, tired=True)
        bx, by = x - 28, 1280 + math.sin(local * 6 + i) * 5
        draw.rounded_rectangle((bx, by, bx + 88, by + 36), radius=12, fill=(255, 170, 170), outline=INK, width=3)
        fs = ImageFont.truetype(FONT, 15)
        lab = "✗" if i % 2 else "???"
        lw = draw.textlength(lab, font=fs)
        draw.text((bx + (88 - lw) / 2, by + 8), lab, font=fs, fill=INK)
    # soft glow path under you — calm lane through chaos
    path = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(path)
    pd.ellipse((280, 1420, 860, 1720), fill=(255, 245, 160, 90))
    img.alpha_composite(path)
    # you walk slowly / calmly through smiling with suitcase
    k = ease(min(local / max(dur * 0.92, 0.1), 1.0))
    x = lerp(260, 740, k)
    walk_speed = 0.55  # slow stroll, not rush
    stick(img, x, 1600, scale=1.35, walk=local * walk_speed, smile=True, wave=0.15)
    suitcase(img, x + 70, 1520, scale=1.1)
    # little calm hearts / sparkles near you
    for j, (ox, oy) in enumerate(((-50, -180), (70, -200), (30, -150))):
        pulse = 0.5 + 0.5 * math.sin(local * 3 + j)
        r = 6 + 4 * pulse
        draw.ellipse((x + ox - r, 1600 + oy - r, x + ox + r, 1600 + oy + r), fill=(255, 180, 200), outline=INK, width=2)
    caption(img, line)
    return img


def scene_press_eftasa(local: float, dur: float, line: str) -> Image.Image:
    img = room_bg()
    # big phone with Έφτασα button — gentle pulse
    bob = math.sin(local * 2.2) * 3
    phone(img, W / 2, 700 + bob, lit=True, bounce=0)
    draw = ImageDraw.Draw(img)
    pulse = 0.5 + 0.5 * math.sin(local * 4)
    bw, bh = 220, 90
    bx, by = W / 2 - bw / 2, 780 + bob
    green = (80, int(200 + 40 * pulse), 110)
    draw.rounded_rectangle((bx, by, bx + bw, by + bh), radius=28, fill=green, outline=INK, width=6)
    f = ImageFont.truetype(FONT, 40)
    t = "ΕΦΤΑΣΑ"
    tw = draw.textlength(t, font=f)
    draw.text((W / 2 - tw / 2, by + 22), t, font=f, fill=WHITE)
    stick(img, W / 2, 1550, scale=1.15, smile=True)
    caption(img, line)
    return img


def scene_send_exit(local: float, dur: float, line: str) -> Image.Image:
    img = sky_bg()
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, H), fill=(255, 245, 230, 255))
    # phone UI choosing exit 1-5
    draw.rounded_rectangle((160, 420, 920, 1400), radius=48, fill=INK)
    draw.rounded_rectangle((190, 470, 890, 1320), radius=36, fill=(255, 252, 240))
    f = ImageFont.truetype(FONT, 36)
    title = "Ποια έξοδος είσαι;"
    tw = draw.textlength(title, font=f)
    draw.text(((W - tw) / 2, 520), title, font=f, fill=INK)
    # exit buttons 1-5 — slow deliberate selection
    selected = 1 + int(min(local / max(dur * 0.75, 0.01), 0.999) * 5)
    for i in range(1, 6):
        x = 230 + (i - 1) * 120
        y = 680
        fill = GOLD if i == selected else (230, 230, 230)
        draw.rounded_rectangle((x, y, x + 100, y + 100), radius=24, fill=fill, outline=INK, width=5)
        fs = ImageFont.truetype(FONT, 48)
        n = str(i)
        nw = draw.textlength(n, font=fs)
        draw.text((x + (100 - nw) / 2, y + 22), n, font=fs, fill=INK)
    # send chip
    draw.rounded_rectangle((300, 980, 780, 1100), radius=30, fill=(80, 200, 120), outline=INK, width=5)
    fs = ImageFont.truetype(FONT, 34)
    msg = f"Στέλνω έξοδο {selected}"
    mw = draw.textlength(msg, font=fs)
    draw.text(((W - mw) / 2, 1015), msg, font=fs, fill=WHITE)
    caption(img, line)
    return img


def scene_calm_taxi(local: float, dur: float, line: str) -> Image.Image:
    """Taxi glides calmly through the chaos; you board while others stay stressed."""
    img = sky_bg()
    draw = ImageDraw.Draw(img)
    airport_asphalt(img, y0=1260)
    airport(img)
    # stressed crowd left behind — still searching on the curb
    for i, x in enumerate((120, 250, 380, 860, 980)):
        _angry_stick(img, x, 1380 + (i % 2) * 16, scale=0.58, shake=local + i, tired=True)
        if i < 3:
            bx, by = x - 20, 1180 + math.sin(local * 5 + i) * 4
            draw.rounded_rectangle((bx, by, bx + 70, by + 30), radius=10, fill=(255, 170, 170), outline=INK, width=2)
            fs = ImageFont.truetype(FONT, 14)
            draw.text((bx + 18, by + 6), "✗", font=fs, fill=INK)
    # soft calm lane for your taxi
    path = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(path).rounded_rectangle((40, 1450, W - 40, 1780), radius=60, fill=(255, 245, 170, 70))
    img.alpha_composite(path)
    # calm taxi arrives slowly (not rushing)
    k = ease(min(local / (dur * 0.62), 1.0))
    car_x = lerp(-240, 500, k)
    taxi_car(img, car_x, 1620, scale=1.28, wheel_spin=local * 0.9)
    if local < dur * 0.7:
        stick(img, 780, 1620, scale=1.25, smile=True)
        suitcase(img, 840, 1545, scale=1.05)
    else:
        board = ease((local - dur * 0.7) / max(dur * 0.3, 0.01))
        stick(img, lerp(780, 560, board), 1620, scale=1.12, smile=True, walk=0.0)
    caption(img, line)
    return img


def scene_relax_end(local: float, dur: float, line: str) -> Image.Image:
    """You drive away comfortably — crowd left behind at cartoon airport curb."""
    img = sky_bg()
    draw = ImageDraw.Draw(img)
    airport_asphalt(img, y0=1240)
    # smaller distant cartoon terminal
    draw.rounded_rectangle((80, 820, 1000, 1120), radius=28, fill=(255, 250, 235, 255), outline=INK, width=6)
    draw.polygon([(60, 828), (540, 660), (1020, 828)], fill=(255, 170, 180, 255), outline=INK)
    draw.line([(60, 828), (540, 660), (1020, 828)], fill=INK, width=6)
    for i in range(3):
        x = 220 + i * 220
        draw.rounded_rectangle((x, 900, x + 140, 1120), radius=16, fill=WINDOW + (255,), outline=INK, width=4)
    f = ImageFont.truetype(FONT, 32)
    t = "ΑΕΡΟΔΡΟΜΙΟ"
    tw = draw.textlength(t, font=f)
    draw.rounded_rectangle(((W - tw) / 2 - 20, 760, (W + tw) / 2 + 20, 820), radius=16, fill=CAPTION_BG, outline=INK, width=4)
    draw.text(((W - tw) / 2, 772), t, font=f, fill=INK)
    # tiny stressed figures fading in the distance (left behind)
    for i, x in enumerate((100, 180, 260)):
        fade = max(0.35, 1.0 - local / max(dur, 0.1) * 0.5)
        _angry_stick(img, x, 1220, scale=0.45 * fade + 0.2, shake=local + i, tired=True)
    # taxi driving away calmly — slow ease
    k = ease(min(local / max(dur * 0.95, 0.1), 1.0))
    car_x = lerp(220, 980, k)
    taxi_car(img, car_x, 1560, scale=1.35, wheel_spin=local * 1.6)
    # smile face in window
    draw.ellipse((car_x - 18, 1415, car_x + 22, 1455), fill=WHITE, outline=INK, width=4)
    draw.arc((car_x - 10, 1428, car_x + 14, 1448), 20, 160, fill=INK, width=3)
    caption(img, line)
    return img


SCENES = {
    "start_city": scene_start_city,
    "start_airport": scene_start_airport,
    "call": scene_call,
    "pickup_city": scene_pickup_city,
    "pickup_airport": scene_pickup_airport,
    "drive": scene_drive,
    "plane_land": scene_plane_land,
    "arrivals_stress": scene_arrivals_stress,
    "you_smile": scene_you_smile,
    "press_eftasa": scene_press_eftasa,
    "send_exit": scene_send_exit,
    "calm_taxi": scene_calm_taxi,
    "relax_end": scene_relax_end,
}


async def speak(text: str, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    last: Exception | None = None
    for attempt in range(8):
        try:
            comm = edge_tts.Communicate(text, VOICE, rate=RATE, pitch="+0Hz")
            audio = bytearray()
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    audio.extend(chunk["data"])
            if len(audio) < 2000:
                raise RuntimeError("empty audio")
            dst.write_bytes(bytes(audio))
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            print("retry tts", exc)
            time.sleep(1.0 + attempt * 0.4)
    raise RuntimeError(last)


def mix_audio(vo: Path, bed: Path, sting: Path, total: float, dst: Path, bed_vol: float = 0.20) -> None:
    ff(
        "-i", str(bed), "-i", str(sting), "-i", str(vo),
        "-filter_complex",
        f"[0:a]volume={bed_vol:.2f},afade=t=in:st=0:d=0.7,"
        f"afade=t=out:st={max(total - 1.6, 0.5):.2f}:d=1.4,"
        "aformat=sample_rates=44100:channel_layouts=stereo[m];"
        "[1:a]volume=0.50,aformat=sample_rates=44100:channel_layouts=stereo[s];"
        "[2:a]highpass=f=80,equalizer=f=180:t=q:w=1:g=1.4,equalizer=f=2500:t=q:w=1:g=1.0,"
        "acompressor=threshold=-18dB:ratio=1.6:attack=12:release=120,"
        "aformat=sample_rates=44100:channel_layouts=stereo,volume=1.12,"
        f"apad=pad_dur={TAIL:.2f}[v];"
        "[m][s][v]amix=inputs=3:duration=longest:dropout_transition=0:normalize=0,"
        "loudnorm=I=-14:TP=-1.0:LRA=11,"
        f"alimiter=limit=0.96,atrim=0:{total:.3f},asetpts=PTS-STARTPTS[a]",
        "-map", "[a]", "-t", f"{total:.3f}",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k", str(dst),
    )


async def build_one(slug: str, copy: dict) -> Path:
    work = BUILD / slug
    work.mkdir(parents=True, exist_ok=True)
    out: Path = copy["out"]
    beats: list[tuple[str, str]] = list(copy["beats"])

    # Speak each line alone. Screen text == spoken line. Slow + simple.
    parts: list[Path] = []
    scene_durs: list[float] = []
    hold = float(copy.get("hold", 0.85))  # quiet beat after each line
    for i, (scene_key, line) in enumerate(beats):
        mp3 = work / f"line_{i}.mp3"
        wav = work / f"line_{i}.wav"
        await speak(line.replace("\n", " ") + ".", mp3)
        ff("-i", str(mp3), "-ac", "1", "-ar", "44100", str(wav))
        pad = work / f"line_{i}_pad.wav"
        ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{hold:.3f}", str(pad))
        d = duration(wav) + hold
        scene_durs.append(d)
        parts.extend([wav, pad])
        print(f"[{slug}] {scene_key}: «{line}» {d:.2f}s")

    brand_mp3 = work / "brand.mp3"
    brand_wav = work / "brand.wav"
    await speak("Taxi and Fly. Από και προς το αεροδρόμιο.", brand_mp3)
    ff("-i", str(brand_mp3), "-ac", "1", "-ar", "44100", str(brand_wav))
    brand_pad = work / "brand_pad.wav"
    ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{TAIL:.3f}", str(brand_pad))
    brand_voice = duration(brand_wav)
    brand_dur = brand_voice + TAIL + 1.6
    parts.extend([brand_wav, brand_pad])

    lst = work / "vo_join.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    vo_wav = work / "vo.wav"
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(vo_wav))

    story_dur = sum(scene_durs)
    brand_start = story_dur
    total = story_dur + brand_dur
    print(f"[{slug}] total {total:.2f}s (story {story_dur:.2f}s + brand {brand_dur:.2f}s)")

    frames_dir = work / "frames"
    shutil.rmtree(frames_dir, ignore_errors=True)
    frames_dir.mkdir(parents=True)

    idx = 0
    for (scene_key, line), seconds in zip(beats, scene_durs):
        fn = SCENES[scene_key]
        n = int(round(seconds * FPS))
        for i in range(n):
            img = fn(i / FPS, seconds, line)
            img.convert("RGB").save(frames_dir / f"{idx:05d}.png")
            idx += 1

    need = int(round(total * FPS))
    while idx < need:
        img = brand_end(idx / FPS, brand_start, copy["brand_lines"])
        img.convert("RGB").save(frames_dir / f"{idx:05d}.png")
        idx += 1

    silent = work / "silent.mp4"
    ff(
        "-framerate", str(FPS), "-i", str(frames_dir / "%05d.png"),
        "-vf", "format=yuv420p,setsar=1",
        "-fps_mode", "cfr", "-r", str(FPS),
        "-frames:v", str(need),
        "-c:v", "libx264", "-preset", "medium", "-crf", "17",
        "-profile:v", "high", "-level", "4.0",
        "-g", str(FPS * 2), "-keyint_min", str(FPS), "-sc_threshold", "0",
        "-an", str(silent),
    )

    vlen = duration(silent)
    bed = work / "bed.wav"
    happy = copy.get("music") == "happy"
    if happy:
        reggae_music(vlen + 0.5, bed)
    else:
        pretty_music(vlen + 0.5, bed)
    sting = work / "sting.wav"
    logo_sting(vlen + 0.5, brand_start + 0.15, sting)
    audio = work / "mix.m4a"
    mix_audio(vo_wav, bed, sting, vlen, audio, bed_vol=0.28 if happy else 0.20)

    tmp = work / "tmp.mp4"
    mix(silent, audio, tmp)
    ff(
        "-i", str(tmp),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
        "-preset", "medium", "-crf", "17",
        "-fps_mode", "cfr", "-r", str(FPS),
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
        "-movflags", "+faststart", str(out),
    )

    ART.mkdir(parents=True, exist_ok=True)
    (ART / "downloads").mkdir(parents=True, exist_ok=True)
    data = out.read_bytes()
    (ART / copy["art"]).write_bytes(data)
    (ART / "downloads" / copy["download"]).write_bytes(data)
    if slug == "athina-aerodromio":
        legacy = ROOT / "taxi-and-fly-stick-cartoon.mp4"
        legacy.write_bytes(data)
        (ART / "taxi_and_fly_stick_cartoon.mp4").write_bytes(data)

    shutil.rmtree(frames_dir, ignore_errors=True)
    print("Wrote", out.name, round(duration(out), 2), "s")
    return out


async def main(argv: list[str] | None = None) -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    wanted = set(sys.argv[1:] if argv is None else argv)
    items = [(k, v) for k, v in VARIANTS.items() if not wanted or k in wanted]
    if not items:
        print("Known:", ", ".join(VARIANTS))
        return 1
    for slug, copy in items:
        await build_one(slug, copy)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
