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
from spot_audio import logo_sting  # noqa: E402

W, H, FPS = 1080, 1920, 30
GOLD = (255, 210, 40)
WHITE = (250, 250, 250)
INK = (18, 18, 20)
SOFT_INK = (40, 42, 48)
TAXI = (255, 204, 0)
ROAD = (48, 52, 60)
SKY_TOP = (186, 214, 236)
SKY_BOT = (232, 240, 246)
ROOM = (244, 241, 236)
GRASS = (148, 186, 132)
SHADOW = (0, 0, 0, 55)
VOICE = "el-GR-NestorasNeural"
RATE = "-8%"
TAIL = 1.25  # silence after last spoken word

# Two clear spots: to airport, and the opposite (from airport).
VARIANTS = {
    "to-airport": {
        "out": ROOT / "taxi-and-fly-stick-pros-aerodromio.mp4",
        "art": "taxi_and_fly_stick_pros_aerodromio.mp4",
        "download": "stick-pros-aerodromio.mp4",
        "spoken": (
            "Όπου κι αν βρίσκεσαι — αν θες να πας στο αεροδρόμιο, "
            "κλείσε Taxi and Fly. "
            "Επαγγελματίες οδηγοί ταξί έρχονται στην ώρα τους "
            "και σε πάνε με ασφάλεια στο αεροδρόμιο. "
            "Taxi and Fly. Από και προς Ελ Βενιζέλος, Αθήνα."
        ),
        "caps": [
            ("Όπου κι αν βρίσκεσαι", "Θέλεις να πας αεροδρόμιο;"),
            ("Κλείσε Taxi and Fly", "Απλά και γρήγορα"),
            ("Έρχονται στην ώρα τους", "Επαγγελματίες οδηγοί ταξί"),
            ("Με ασφάλεια", "Προς το αεροδρόμιο"),
            ("Στο αεροδρόμιο", "Έφτασες ήρεμα και στην ώρα σου"),
        ],
        "brand_lines": [
            "Από και προς αεροδρόμιο",
            "Ελ. Βενιζέλος · Αθήνα",
            "Επαγγελματίες οδηγοί ταξί",
        ],
        "direction": "to",
    },
    "from-airport": {
        "out": ROOT / "taxi-and-fly-stick-apo-aerodromio.mp4",
        "art": "taxi_and_fly_stick_apo_aerodromio.mp4",
        "download": "stick-apo-aerodromio.mp4",
        "spoken": (
            "Μόλις προσγειωθείς — αν θες να φύγεις από το αεροδρόμιο, "
            "κλείσε Taxi and Fly. "
            "Επαγγελματίες οδηγοί ταξί σε περιμένουν στην ώρα τους "
            "και σε πάνε με ασφάλεια στον προορισμό σου. "
            "Taxi and Fly. Από και προς Ελ Βενιζέλος, Αθήνα."
        ),
        "caps": [
            ("Μόλις προσγειωθείς", "Θέλεις να φύγεις από το αεροδρόμιο;"),
            ("Κλείσε Taxi and Fly", "Απλά και γρήγορα"),
            ("Σε περιμένουν στην ώρα τους", "Επαγγελματίες οδηγοί ταξί"),
            ("Με ασφάλεια", "Προς τον προορισμό σου"),
            ("Στο σπίτι σου", "Έφτασες ήρεμα και στην ώρα σου"),
        ],
        "brand_lines": [
            "Από και προς αεροδρόμιο",
            "Ελ. Βενιζέλος · Αθήνα",
            "Επαγγελματίες οδηγοί ταξί",
        ],
        "direction": "from",
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
        arr[y, :] = mix_rgb(SKY_TOP, SKY_BOT, k)
    return Image.fromarray(arr, "RGB").convert("RGBA")


def room_bg() -> Image.Image:
    img = Image.new("RGBA", (W, H), ROOM + (255,))
    draw = ImageDraw.Draw(img)
    # subtle wall panel
    draw.rectangle((0, 0, W, 70), fill=(232, 228, 222, 255))
    draw.rectangle((0, 1480, W, H), fill=(220, 214, 205, 255))
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
    """Black stick person. cy = feet. walk phase 0..1 animates legs/arms."""
    draw = ImageDraw.Draw(base)
    s = scale
    head_r = 32 * s
    body = 105 * s
    arm = 78 * s
    leg = 88 * s
    thick = max(7, int(9 * s))
    phase = walk * math.pi * 2
    hip_y = cy - leg
    shoulder_y = hip_y - body
    head_y = shoulder_y - head_r - 4 * s

    put_shadow(base, cx, cy + 6, 48 * s, 14 * s)

    # head fill + outline for cleaner look
    draw.ellipse(
        (cx - head_r, head_y - head_r, cx + head_r, head_y + head_r),
        fill=WHITE,
        outline=INK,
        width=thick,
    )
    # eyes
    er = max(2, int(3.2 * s))
    draw.ellipse((cx - 11 * s - er, head_y - 4 * s - er, cx - 11 * s + er, head_y - 4 * s + er), fill=INK)
    draw.ellipse((cx + 11 * s - er, head_y - 4 * s - er, cx + 11 * s + er, head_y - 4 * s + er), fill=INK)
    if smile:
        draw.arc(
            (cx - 15 * s, head_y - 2 * s, cx + 15 * s, head_y + 18 * s),
            15,
            165,
            fill=INK,
            width=max(3, int(4 * s)),
        )

    rounded_line(draw, (cx, head_y + head_r), (cx, hip_y), thick)
    # arms
    swing = math.sin(phase) * 18 if walk else 0
    rounded_line(
        draw,
        (cx, shoulder_y + 12 * s),
        (cx - arm * 0.9, shoulder_y + arm * 0.65 - swing),
        thick,
    )
    ax = cx + arm * math.cos(math.radians(-20 + wave * 55 + swing * 0.4))
    ay = shoulder_y + 12 * s + arm * math.sin(math.radians(50 - wave * 40))
    rounded_line(draw, (cx, shoulder_y + 12 * s), (ax, ay), thick)
    # legs
    leg_swing = math.sin(phase) * 22 if walk else 0
    rounded_line(draw, (cx, hip_y), (cx - 30 * s - leg_swing * 0.3, cy), thick)
    rounded_line(draw, (cx, hip_y), (cx + 30 * s + leg_swing * 0.3, cy), thick)


def house(base: Image.Image, x: float, y: float, w: float = 380, h: float = 310) -> None:
    draw = ImageDraw.Draw(base)
    put_shadow(base, x + w / 2, y + h + 18, w * 0.48, 22)
    roof_h = h * 0.42
    # body
    draw.rounded_rectangle((x, y, x + w, y + h), radius=8, outline=INK, width=7, fill=(252, 250, 246))
    # roof
    draw.polygon(
        [(x - 28, y + 8), (x + w / 2, y - roof_h), (x + w + 28, y + 8)],
        fill=(196, 72, 68),
        outline=INK,
    )
    draw.line([(x - 28, y + 8), (x + w / 2, y - roof_h), (x + w + 28, y + 8)], fill=INK, width=7)
    # chimney
    draw.rectangle((x + w * 0.72, y - roof_h + 40, x + w * 0.72 + 36, y - 10), fill=(120, 120, 125), outline=INK, width=4)
    # door
    dw, dh = 78, 135
    dx = x + w / 2 - dw / 2
    draw.rounded_rectangle((dx, y + h - dh, dx + dw, y + h), radius=6, outline=INK, width=5, fill=(168, 126, 88))
    draw.ellipse((dx + dw - 22, y + h - dh / 2 - 6, dx + dw - 10, y + h - dh / 2 + 6), fill=GOLD, outline=INK, width=2)
    # windows
    for wx in (x + 36, x + w - 36 - 78):
        draw.rounded_rectangle((wx, y + 55, wx + 78, y + 133), radius=6, outline=INK, width=5, fill=(164, 208, 230))
        draw.line((wx + 39, y + 55, wx + 39, y + 133), fill=INK, width=3)
        draw.line((wx, y + 94, wx + 78, y + 94), fill=INK, width=3)


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
    body_w, body_h = 260 * s, 78 * s
    cabin_w, cabin_h = 150 * s, 62 * s
    x0 = cx - body_w / 2
    y0 = cy - body_h
    put_shadow(base, cx, cy + 8, body_w * 0.42, 18 * s)

    # body
    draw.rounded_rectangle((x0, y0, x0 + body_w, y0 + body_h), radius=22, fill=TAXI, outline=INK, width=6)
    # cabin
    draw.rounded_rectangle(
        (cx - cabin_w / 2, y0 - cabin_h + 14, cx + cabin_w / 2, y0 + 14),
        radius=18,
        fill=TAXI,
        outline=INK,
        width=6,
    )
    # windows
    draw.rounded_rectangle(
        (cx - cabin_w / 2 + 14, y0 - cabin_h + 26, cx - 6, y0 + 2),
        radius=8,
        fill=(150, 200, 225),
        outline=INK,
        width=3,
    )
    draw.rounded_rectangle(
        (cx + 6, y0 - cabin_h + 26, cx + cabin_w / 2 - 14, y0 + 2),
        radius=8,
        fill=(150, 200, 225),
        outline=INK,
        width=3,
    )
    # headlights / bumper
    draw.ellipse((x0 + 12, y0 + 28, x0 + 34, y0 + 50), fill=WHITE, outline=INK, width=2)
    draw.ellipse((x0 + body_w - 34, y0 + 28, x0 + body_w - 12, y0 + 50), fill=(255, 120, 80), outline=INK, width=2)
    draw.rectangle((x0 + 18, y0 + body_h - 16, x0 + body_w - 18, y0 + body_h - 6), fill=SOFT_INK)

    # wheels with spin marks
    for wx in (cx - 78 * s, cx + 78 * s):
        draw.ellipse((wx - 26 * s, cy - 26 * s, wx + 26 * s, cy + 26 * s), fill=INK)
        draw.ellipse((wx - 12 * s, cy - 12 * s, wx + 12 * s, cy + 12 * s), fill=(210, 210, 210))
        ang = wheel_spin * 360
        for a in (ang, ang + 90):
            rad = math.radians(a)
            draw.line(
                (wx, cy, wx + 10 * s * math.cos(rad), cy + 10 * s * math.sin(rad)),
                fill=SOFT_INK,
                width=3,
            )

    # roof light
    draw.rounded_rectangle(
        (cx - 34 * s, y0 - cabin_h - 16 * s, cx + 34 * s, y0 - cabin_h + 6),
        radius=6,
        fill=WHITE,
        outline=INK,
        width=4,
    )
    f = ImageFont.truetype(FONT, max(15, int(18 * s)))
    tw = draw.textlength("TAXI", font=f)
    draw.text((cx - tw / 2, y0 - cabin_h - 14 * s), "TAXI", font=f, fill=INK)


def suitcase(base: Image.Image, x: float, y: float, scale: float = 1.0) -> None:
    draw = ImageDraw.Draw(base)
    s = scale
    put_shadow(base, x + 28 * s, y + 78 * s, 30 * s, 10 * s)
    draw.rounded_rectangle((x, y, x + 58 * s, y + 74 * s), radius=10, outline=INK, width=5, fill=(70, 96, 130))
    draw.line((x + 14 * s, y - 20 * s, x + 44 * s, y - 20 * s), fill=INK, width=5)
    draw.line((x + 14 * s, y - 20 * s, x + 14 * s, y), fill=INK, width=5)
    draw.line((x + 44 * s, y - 20 * s, x + 44 * s, y), fill=INK, width=5)
    draw.line((x + 10 * s, y + 28 * s, x + 48 * s, y + 28 * s), fill=(200, 210, 220), width=3)


def airport(base: Image.Image) -> None:
    draw = ImageDraw.Draw(base)
    # terminal
    put_shadow(base, W / 2, 1295, 420, 24)
    draw.rounded_rectangle((90, 960, 990, 1290), radius=12, fill=(242, 245, 248), outline=INK, width=7)
    draw.polygon([(70, 968), (540, 780), (1010, 968)], fill=(210, 220, 230), outline=INK)
    draw.line([(70, 968), (540, 780), (1010, 968)], fill=INK, width=7)
    # control tower
    draw.rectangle((860, 700, 900, 960), fill=(200, 205, 212), outline=INK, width=4)
    draw.ellipse((835, 650, 925, 720), fill=GOLD, outline=INK, width=4)
    # glass doors
    for i in range(3):
        x = 230 + i * 200
        draw.rounded_rectangle((x, 1060, x + 150, 1290), radius=6, outline=INK, width=5, fill=(150, 198, 222))
        draw.line((x + 75, 1060, x + 75, 1290), fill=INK, width=3)
    # plane
    px, py = 200, 620
    draw.ellipse((px, py, px + 190, py + 46), fill=INK)
    draw.polygon([(px + 50, py + 12), (px + 20, py - 40), (px + 85, py + 12)], fill=INK)
    draw.polygon([(px + 120, py + 18), (px + 175, py + 70), (px + 105, py + 28)], fill=INK)
    f = ImageFont.truetype(FONT, 40)
    t = "ΑΕΡΟΔΡΟΜΙΟ"
    tw = draw.textlength(t, font=f)
    draw.rounded_rectangle(((W - tw) / 2 - 24, 870, (W + tw) / 2 + 24, 940), radius=14, fill=WHITE, outline=INK, width=4)
    draw.text(((W - tw) / 2, 882), t, font=f, fill=INK)


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
    f = fit_text(draw, text, ImageFont.truetype(FONT, 48), 920)
    tw = draw.textlength(text, font=f)
    pad_x, pad_y = 32, 20
    box_h = 56 + pad_y
    box = ((W - tw) / 2 - pad_x, y - pad_y, (W + tw) / 2 + pad_x, y + box_h)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (box[0] + 4, box[1] + 6, box[2] + 4, box[3] + 6), radius=22, fill=(0, 0, 0, 40)
    )
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(4)))
    draw.rounded_rectangle(box, radius=22, fill=WHITE, outline=INK, width=4)
    th = f.size if hasattr(f, "size") else 48
    draw.text(((W - tw) / 2, y + (48 - th) / 2), text, font=f, fill=INK)
    if sub:
        fs = fit_text(draw, sub, ImageFont.truetype(FONT_REG, 34), 960)
        sw = draw.textlength(sub, font=fs)
        draw.text(((W - sw) / 2, box[3] + 16), sub, font=fs, fill=SOFT_INK)


def road_layer(base: Image.Image, y0: int = 1280, scroll: float = 0.0) -> None:
    draw = ImageDraw.Draw(base)
    draw.rectangle((0, y0, W, H), fill=ROAD)
    draw.rectangle((0, y0, W, y0 + 14), fill=GOLD)
    for i in range(16):
        x = (i * 120 - int(scroll) % 120)
        draw.rounded_rectangle((x, y0 + 210, x + 64, y0 + 228), radius=4, fill=WHITE)


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


def scene_start(local: float, dur: float, copy: dict, direction: str) -> Image.Image:
    title, sub = copy["caps"][0]
    if direction == "to":
        img = sky_bg()
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 1260, W, H), fill=GRASS)
        for i in range(40):
            a = int(18 * (1 - i / 40))
            draw.line((0, 1260 - i, W, 1260 - i), fill=(255, 255, 255, a))
        house(img, 170, 760)
        k = ease(min(local / max(dur * 0.7, 0.1), 1.0))
        x = lerp(700, 780, k)
        walk = local * 1.4 if local < dur * 0.7 else 0.0
        stick(img, x, 1370, scale=1.25, walk=walk)
        suitcase(img, x + 62, 1295, scale=1.05)
    else:
        img = sky_bg()
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 1320, W, H), fill=(186, 192, 198))
        airport(img)
        k = ease(min(local / max(dur * 0.7, 0.1), 1.0))
        x = lerp(520, 640, k)
        stick(img, x, 1560, scale=1.25, walk=local * 1.2 if local < dur * 0.7 else 0.0, smile=True)
        suitcase(img, x + 62, 1485, scale=1.05)
    caption(img, title, sub=sub)
    return img


def scene_call(local: float, dur: float, copy: dict, direction: str) -> Image.Image:
    title, sub = copy["caps"][1]
    img = room_bg()
    bob = math.sin(local * 5.5) * 10
    phone(img, W / 2, 720, lit=True, bounce=bob)
    stick(img, W / 2, 1520, scale=1.15)
    draw = ImageDraw.Draw(img)
    for i in range(3):
        pulse = 0.4 + 0.6 * abs(math.sin(local * 7 + i))
        r = 8 + 4 * pulse
        x = W / 2 + 110 + i * 28
        draw.ellipse(
            (x - r, 640 - r + bob, x + r, 640 + r + bob),
            fill=mix_rgb(GOLD, (255, 255, 255), 1 - pulse) + (255,),
        )
    caption(img, title, sub=sub)
    return img


def scene_pickup(local: float, dur: float, copy: dict, direction: str) -> Image.Image:
    title, sub = copy["caps"][2]
    img = sky_bg()
    if direction == "from":
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 1280, W, 1320), fill=(186, 192, 198))
        # small terminal cue in background
        draw.rounded_rectangle((80, 900, 420, 1180), radius=10, fill=(242, 245, 248), outline=INK, width=5)
    road_layer(img, 1280, scroll=local * 180)
    k = ease(min(local / (dur * 0.55), 1.0))
    car_x = lerp(-240, 520, k)
    taxi_car(img, car_x, 1510, scale=1.25, wheel_spin=local * 3)
    if local < dur * 0.72:
        stick(img, 820, 1510, scale=1.2)
        suitcase(img, 880, 1435, scale=1.0)
    else:
        stick(img, lerp(820, 560, ease((local - dur * 0.72) / (dur * 0.28))), 1510, scale=1.05)
    caption(img, title, sub=sub)
    return img


def scene_drive(local: float, dur: float, copy: dict, direction: str) -> Image.Image:
    title, sub = copy["caps"][3]
    img = sky_bg()
    draw = ImageDraw.Draw(img)
    offset = int(local * 220) % 900
    draw.ellipse((-200 - offset, 980, 520 - offset, 1500), fill=GRASS)
    draw.ellipse((500 - offset * 0.6, 1020, 1300 - offset * 0.6, 1520), fill=(136, 174, 120))
    road_layer(img, 1240, scroll=local * 720)
    bounce = math.sin(local * 16) * 5
    taxi_car(img, 540, 1475 + bounce, scale=1.4, wheel_spin=local * 5)
    draw.ellipse((505, 1335 + bounce, 548, 1378 + bounce), fill=WHITE, outline=INK, width=4)
    caption(img, title, sub=sub)
    return img


def scene_arrive(local: float, dur: float, copy: dict, direction: str) -> Image.Image:
    title, sub = copy["caps"][4]
    img = sky_bg()
    draw = ImageDraw.Draw(img)
    if direction == "to":
        draw.rectangle((0, 1320, W, H), fill=(186, 192, 198))
        airport(img)
        ground_y = 1580
    else:
        draw.rectangle((0, 1260, W, H), fill=GRASS)
        house(img, 170, 760)
        ground_y = 1370
    arrive = ease(min(local / (dur * 0.35), 1.0))
    car_x = lerp(420, 260, arrive)
    if local < dur * 0.75:
        taxi_car(img, car_x, ground_y if direction == "to" else 1510, scale=1.1, wheel_spin=max(0, 1.2 - arrive) * local)
    exit_k = ease(max((local - dur * 0.28) / (dur * 0.55), 0.0))
    fig_x = lerp(420, 640, exit_k)
    wave = ease(max((local - dur * 0.4) / (dur * 0.4), 0.0))
    fy = ground_y if direction == "to" else 1370
    stick(
        img,
        fig_x,
        fy,
        scale=1.28,
        wave=wave,
        smile=local > dur * 0.35,
        walk=exit_k * 0.8 if exit_k < 0.95 else 0,
    )
    suitcase(img, fig_x + 68, fy - 75, scale=1.05)
    caption(img, title, sub=sub)
    return img


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


def mix_audio(vo: Path, bed: Path, sting: Path, total: float, dst: Path) -> None:
    ff(
        "-i", str(bed), "-i", str(sting), "-i", str(vo),
        "-filter_complex",
        "[0:a]volume=0.20,afade=t=in:st=0:d=0.7,"
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
    direction = copy["direction"]
    out: Path = copy["out"]

    vo_mp3 = work / "vo.mp3"
    await speak(copy["spoken"], vo_mp3)
    vo_wav = work / "vo.wav"
    ff("-i", str(vo_mp3), "-ac", "1", "-ar", "44100", str(vo_wav))
    vo_len = duration(vo_wav)
    total = vo_len + TAIL
    print(f"[{slug}] VO {vo_len:.2f}s → video {total:.2f}s")

    # Longer brand hold so the closing lines are never clipped.
    brand_dur = max(7.0, total * 0.40)
    story_dur = total - brand_dur
    beats = [
        ("start", 0.18, scene_start),
        ("call", 0.18, scene_call),
        ("pickup", 0.20, scene_pickup),
        ("drive", 0.18, scene_drive),
        ("arrive", 0.26, scene_arrive),
    ]

    frames_dir = work / "frames"
    shutil.rmtree(frames_dir, ignore_errors=True)
    frames_dir.mkdir(parents=True)

    brand_start = story_dur
    t = 0.0
    idx = 0
    for name, frac, fn in beats:
        seconds = story_dur * frac
        n = int(round(seconds * FPS))
        for i in range(n):
            local = i / FPS
            img = fn(local, seconds, copy, direction)
            img.convert("RGB").save(frames_dir / f"{idx:05d}.png")
            idx += 1
        t += seconds
        print(f"[{slug}] scene {name} {seconds:.2f}s")

    need = int(round(total * FPS))
    while idx < need:
        img = brand_end(idx / FPS, brand_start, copy["brand_lines"])
        img.convert("RGB").save(frames_dir / f"{idx:05d}.png")
        idx += 1
    # Also fill brand portion if beats undershot due to rounding
    brand_frames_needed = need - int(round(story_dur * FPS))
    # rewrite brand span cleanly
    brand_from = max(0, need - max(brand_frames_needed, int(round(brand_dur * FPS))))
    for i in range(brand_from, need):
        img = brand_end(i / FPS, brand_start, copy["brand_lines"])
        img.convert("RGB").save(frames_dir / f"{i:05d}.png")

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
    pretty_music(vlen + 0.5, bed)
    sting = work / "sting.wav"
    logo_sting(vlen + 0.5, brand_start + 0.18, sting)
    audio = work / "mix.m4a"
    mix_audio(vo_wav, bed, sting, vlen, audio)

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
    # Keep legacy filename pointing at the to-airport spot.
    if slug == "to-airport":
        legacy = ROOT / "taxi-and-fly-stick-cartoon.mp4"
        legacy.write_bytes(data)
        (ART / "taxi_and_fly_stick_cartoon.mp4").write_bytes(data)
        (ART / "downloads" / "stick-cartoon-taxi-and-fly.mp4").write_bytes(data)

    shutil.rmtree(frames_dir, ignore_errors=True)
    print("Wrote", out, "video", round(duration(out), 2), "s", "vo", round(vo_len, 2), "s")
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
