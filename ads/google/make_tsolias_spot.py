#!/usr/bin/env python3
"""Cartoon tsolias who loves Greece and trusts Taxi and Fly — folk-style song.

Original traditional-style melody + original Greek verses (not a known song).
"""

from __future__ import annotations

import asyncio
import math
import shutil
import sys
import time
import wave
from pathlib import Path

import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build" / "tsolias"
ART = Path("/opt/cursor/artifacts")
OUT = ROOT / "taxi-and-fly-tsolias.mp4"

sys.path.insert(0, str(ROOT))
from build_video import FONT, FONT_REG, duration, ff, mix  # noqa: E402
from rebuild_brand_process import icon_lettering  # noqa: E402
from spot_audio import logo_sting, write_wav  # noqa: E402

W, H, FPS = 1080, 1920, 30
SR = 44100
GOLD = (255, 210, 40)
WHITE = (255, 255, 255)
INK = (40, 30, 40)
SKY_TOP = (120, 198, 235)
SKY_BOT = (185, 225, 245)
GRASS = (90, 170, 70)
HILL = (70, 150, 55)
BLUE = (0, 100, 180)
RED = (200, 40, 50)
BLACK = (30, 30, 30)
VOICE = "el-GR-NestorasNeural"
RATE = "-8%"

# Story + original folk-style verses (Taxi and Fly)
BEATS = [
    ("love_greece", "Ένας Έλληνας τσολιάς\nπου αγαπάει την Ελλάδα"),
    ("trust", "Εμπιστεύεται την Taxi and Fly\nγια τις διαδρομές του"),
    ("sing1", "Taxi and Fly, Taxi and Fly\nστην πατρίδα σε εμπιστεύομαι"),
    ("sing2", "Από την πόλη στο αεροδρόμιο\nμε σιγουριά σε καλημερίζω"),
    ("sing3", "Taxi and Fly, καλό μου ταξί\nστην Ελλάδα σε εμπιστεύομαι"),
]


def ease(k: float) -> float:
    k = max(0.0, min(k, 1.0))
    return 1 - (1 - k) ** 3


def mix_rgb(a, b, k: float):
    k = max(0.0, min(k, 1.0))
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def sky_bg() -> Image.Image:
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        arr[y, :] = mix_rgb(SKY_TOP, SKY_BOT, y / (H - 1))
    img = Image.fromarray(arr, "RGB").convert("RGBA")
    draw = ImageDraw.Draw(img)
    for cx, cy, s in ((200, 220, 1.0), (700, 180, 1.2), (920, 280, 0.8)):
        for ox, oy, r in ((0, 0, 50), (-40, 8, 38), (42, 10, 40)):
            draw.ellipse(
                (cx + ox * s - r * s, cy + oy * s - r * s, cx + ox * s + r * s, cy + oy * s + r * s),
                fill=WHITE + (255,),
            )
    return img


def greek_flag(base: Image.Image, x: float, y: float, scale: float = 1.0) -> None:
    draw = ImageDraw.Draw(base)
    w, h = 160 * scale, 100 * scale
    # blue/white stripes
    for i in range(9):
        fill = BLUE if i % 2 == 0 else WHITE
        draw.rectangle((x, y + i * (h / 9), x + w, y + (i + 1) * (h / 9)), fill=fill)
    # canton
    draw.rectangle((x, y, x + w * 0.4, y + h * 5 / 9), fill=BLUE)
    # white cross
    cx, cy = x + w * 0.2, y + h * 2.5 / 9
    draw.rectangle((cx - 8 * scale, y + 8 * scale, cx + 8 * scale, y + h * 5 / 9 - 8 * scale), fill=WHITE)
    draw.rectangle((x + 10 * scale, cy - 8 * scale, x + w * 0.4 - 10 * scale, cy + 8 * scale), fill=WHITE)
    draw.rectangle((x, y, x + w, y + h), outline=INK, width=4)


def taxi_car(base: Image.Image, cx: float, cy: float, scale: float = 1.0, wheel_spin: float = 0.0) -> None:
    draw = ImageDraw.Draw(base)
    s = scale
    body = (cx - 110 * s, cy - 70 * s, cx + 110 * s, cy - 10 * s)
    draw.rounded_rectangle(body, radius=28 * s, fill=GOLD, outline=INK, width=6)
    draw.rounded_rectangle((cx - 70 * s, cy - 120 * s, cx + 70 * s, cy - 70 * s), radius=22 * s, fill=GOLD, outline=INK, width=6)
    for wx in (cx - 40 * s, cx + 20 * s):
        draw.ellipse((wx, cy - 110 * s, wx + 35 * s, cy - 78 * s), fill=(140, 210, 255), outline=INK, width=4)
    draw.rounded_rectangle((cx - 28 * s, cy - 145 * s, cx + 28 * s, cy - 118 * s), radius=8, fill=WHITE, outline=INK, width=3)
    f = ImageFont.truetype(FONT, max(14, int(18 * s)))
    t = "TAXI"
    tw = draw.textlength(t, font=f)
    draw.text((cx - tw / 2, cy - 140 * s), t, font=f, fill=INK)
    for wx in (cx - 70 * s, cx + 40 * s):
        draw.ellipse((wx, cy - 30 * s, wx + 45 * s, cy + 15 * s), fill=INK)
        ang = wheel_spin * 40
        draw.ellipse((wx + 10 * s, cy - 20 * s, wx + 35 * s, cy + 5 * s), fill=GOLD)
        draw.line((wx + 22 * s, cy - 8 * s, wx + 22 * s + 12 * s * math.cos(ang), cy - 8 * s + 12 * s * math.sin(ang)), fill=INK, width=3)


def tsolias(
    base: Image.Image,
    cx: float,
    cy: float,
    scale: float = 1.0,
    smile: bool = True,
    wave: float = 0.0,
    sing: float = 0.0,
) -> None:
    """Cartoon Greek tsolias — fez, foustanella, tsarouhia."""
    draw = ImageDraw.Draw(base)
    s = scale
    head_r = 44 * s
    body = 70 * s
    leg = 70 * s
    thick = max(9, int(11 * s))
    hip_y = cy - leg
    shoulder_y = hip_y - body
    head_y = shoulder_y - head_r

    # shadow
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((cx - 50 * s, cy - 8 * s, cx + 50 * s, cy + 14 * s), fill=(0, 0, 0, 45))
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))

    # foustanella (white pleated skirt)
    skirt_top = hip_y - 10 * s
    for i in range(10):
        a = -50 + i * 11
        x1 = cx + 70 * s * math.sin(math.radians(a - 8))
        x2 = cx + 70 * s * math.sin(math.radians(a + 8))
        draw.polygon(
            [(cx, skirt_top), (x1, hip_y + 55 * s), (x2, hip_y + 55 * s)],
            fill=WHITE,
            outline=INK,
        )
    draw.arc((cx - 72 * s, skirt_top - 10 * s, cx + 72 * s, hip_y + 60 * s), 10, 170, fill=INK, width=4)

    # blue vest
    draw.rounded_rectangle(
        (cx - 38 * s, shoulder_y - 5 * s, cx + 38 * s, hip_y + 5 * s),
        radius=14 * s,
        fill=BLUE,
        outline=INK,
        width=5,
    )
    # gold embroidery lines
    for dy in (10, 28, 46):
        draw.line((cx - 28 * s, shoulder_y + dy * s, cx + 28 * s, shoulder_y + dy * s), fill=GOLD, width=3)

    # legs + white hose
    draw.line((cx - 18 * s, hip_y + 40 * s, cx - 28 * s, cy), fill=WHITE, width=thick + 2)
    draw.line((cx + 18 * s, hip_y + 40 * s, cx + 28 * s, cy), fill=WHITE, width=thick + 2)
    draw.line((cx - 18 * s, hip_y + 40 * s, cx - 28 * s, cy), fill=INK, width=3)
    draw.line((cx + 18 * s, hip_y + 40 * s, cx + 28 * s, cy), fill=INK, width=3)

    # tsarouhia (red pompon shoes)
    for sx in (cx - 34 * s, cx + 22 * s):
        draw.ellipse((sx, cy - 12 * s, sx + 28 * s, cy + 10 * s), fill=RED, outline=INK, width=4)
        draw.ellipse((sx + 16 * s, cy - 22 * s, sx + 34 * s, cy - 4 * s), fill=BLACK, outline=INK, width=3)

    # arms
    ax = cx + 55 * s * math.cos(math.radians(-30 + wave * 50))
    ay = shoulder_y + 50 * s + 20 * s * math.sin(math.radians(40 - wave * 30))
    draw.line((cx, shoulder_y + 10 * s, ax, ay), fill=INK, width=thick)
    draw.line((cx, shoulder_y + 10 * s, cx - 50 * s, shoulder_y + 55 * s), fill=INK, width=thick)

    # head
    mouth_open = 4 * s * max(0.0, math.sin(sing * 10))
    draw.ellipse(
        (cx - head_r, head_y - head_r, cx + head_r, head_y + head_r),
        fill=WHITE,
        outline=INK,
        width=thick,
    )
    er = max(3, int(4 * s))
    draw.ellipse((cx - 14 * s - er, head_y - 6 * s - er, cx - 14 * s + er, head_y - 6 * s + er), fill=INK)
    draw.ellipse((cx + 14 * s - er, head_y - 6 * s - er, cx + 14 * s + er, head_y - 6 * s + er), fill=INK)
    draw.ellipse((cx - 26 * s, head_y + 8 * s, cx - 12 * s, head_y + 20 * s), fill=(255, 170, 170))
    draw.ellipse((cx + 12 * s, head_y + 8 * s, cx + 26 * s, head_y + 20 * s), fill=(255, 170, 170))
    if smile:
        draw.arc(
            (cx - 16 * s, head_y + 4 * s, cx + 16 * s, head_y + 26 * s + mouth_open),
            15,
            165,
            fill=INK,
            width=max(4, int(5 * s)),
        )

    # red fez + black tassel
    draw.ellipse((cx - 38 * s, head_y - head_r - 8 * s, cx + 38 * s, head_y - head_r + 28 * s), fill=RED, outline=INK, width=5)
    draw.rectangle((cx - 32 * s, head_y - head_r - 35 * s, cx + 32 * s, head_y - head_r + 5 * s), fill=RED, outline=INK, width=4)
    tass = 35 * s + 8 * s * math.sin(wave * 3 + sing)
    draw.line((cx + 20 * s, head_y - head_r - 30 * s, cx + 20 * s + tass, head_y - head_r + 10 * s), fill=INK, width=5)
    draw.ellipse((cx + 14 * s + tass, head_y - head_r + 5 * s, cx + 28 * s + tass, head_y - head_r + 20 * s), fill=INK)


def caption(base: Image.Image, text: str, y: int = 140) -> None:
    draw = ImageDraw.Draw(base)
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()] or [text]
    f = ImageFont.truetype(FONT, 44 if len(lines) > 1 else 48)
    for size in range(getattr(f, "size", 48), 28, -2):
        f = ImageFont.truetype(FONT, size)
        if all(draw.textlength(ln, font=f) <= 940 for ln in lines):
            break
    widths = [draw.textlength(ln, font=f) for ln in lines]
    tw = max(widths)
    line_h = int(getattr(f, "size", 44) + 10)
    pad_x, pad_y = 28, 16
    box = ((W - tw) / 2 - pad_x, y - pad_y, (W + tw) / 2 + pad_x, y + len(lines) * line_h + pad_y)
    draw.rounded_rectangle(box, radius=26, fill=(255, 248, 170), outline=INK, width=5)
    for i, ln in enumerate(lines):
        draw.text(((W - widths[i]) / 2, y + i * line_h), ln, font=f, fill=INK)


BADGE = None


def brand_end(t: float, start: float) -> Image.Image:
    global BADGE
    if BADGE is None:
        size = 520
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
    since = max(t - start, 0.0)
    k = ease(min(since / 0.5, 1.0))
    size = int(520 * (0.9 + 0.1 * k))
    mark = BADGE.resize((size, size), Image.Resampling.LANCZOS)
    img.alpha_composite(mark, ((W - size) // 2, 420))
    draw = ImageDraw.Draw(img)
    f_brand = ImageFont.truetype(FONT, 72)
    f_line = ImageFont.truetype(FONT_REG, 38)
    bw = draw.textlength("Taxi and Fly", font=f_brand)
    draw.text(((W - bw) / 2, 1000), "Taxi and Fly", font=f_brand, fill=GOLD + (255,))
    line = "Από και προς το αεροδρόμιο"
    tw = draw.textlength(line, font=f_line)
    draw.text(((W - tw) / 2, 1120), line, font=f_line, fill=WHITE + (255,))
    return img


def scene_love_greece(local: float, dur: float, line: str) -> Image.Image:
    img = sky_bg()
    draw = ImageDraw.Draw(img)
    draw.ellipse((-200, 1100, 700, 1700), fill=HILL + (255,))
    draw.ellipse((400, 1150, 1300, 1750), fill=GRASS + (255,))
    draw.rectangle((0, 1450, W, H), fill=GRASS)
    greek_flag(img, 120, 720, scale=1.3)
    # little sun
    draw.ellipse((820, 280, 940, 400), fill=GOLD, outline=INK, width=5)
    bob = math.sin(local * 2.5) * 4
    tsolias(img, W / 2, 1580 + bob, scale=1.45, smile=True, wave=0.3 + 0.2 * math.sin(local * 2))
    caption(img, line)
    return img


def scene_trust(local: float, dur: float, line: str) -> Image.Image:
    img = sky_bg()
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 1400, W, H), fill=GRASS)
    draw.ellipse((-100, 1200, 600, 1600), fill=HILL + (255,))
    k = ease(min(local / max(dur * 0.7, 0.1), 1.0))
    car_x = -200 + 700 * k
    taxi_car(img, car_x, 1550, scale=1.15, wheel_spin=local * 2)
    tsolias(img, 780, 1580, scale=1.25, smile=True, wave=0.5)
    greek_flag(img, 100, 800, scale=0.9)
    caption(img, line)
    return img


def scene_sing(local: float, dur: float, line: str, verse: int = 1) -> Image.Image:
    img = sky_bg()
    draw = ImageDraw.Draw(img)
    draw.ellipse((-150, 1050, 750, 1650), fill=HILL + (255,))
    draw.ellipse((350, 1100, 1250, 1700), fill=GRASS + (255,))
    draw.rectangle((0, 1480, W, H), fill=GRASS)
    greek_flag(img, 80, 700, scale=1.1)
    greek_flag(img, 820, 740, scale=0.95)
    # bouncing taxi
    bounce = abs(math.sin(local * 6)) * 8
    taxi_car(img, 280, 1580 - bounce, scale=1.0, wheel_spin=local * 3)
    # singing tsolias
    tsolias(img, 700, 1580, scale=1.4, smile=True, wave=0.6, sing=local)
    # music notes
    for i, (ox, oy) in enumerate(((-80, -220), (40, -260), (120, -200))):
        pulse = 0.5 + 0.5 * math.sin(local * 5 + i)
        nx, ny = 700 + ox, 1200 + oy - 10 * pulse
        draw.ellipse((nx, ny, nx + 22, ny + 18), fill=INK)
        draw.line((nx + 20, ny + 4, nx + 20, ny - 40), fill=INK, width=4)
    caption(img, line, y=120)
    return img


SCENES = {
    "love_greece": scene_love_greece,
    "trust": scene_trust,
    "sing1": lambda l, d, line: scene_sing(l, d, line, 1),
    "sing2": lambda l, d, line: scene_sing(l, d, line, 2),
    "sing3": lambda l, d, line: scene_sing(l, d, line, 3),
}


def folk_bed(seconds: float, dst: Path) -> None:
    """Original folk-style bed (kalamatiano-ish 7/8 feel) — not a known song."""
    n = int(SR * seconds)
    out = np.zeros(n)
    # 7/8: 2+2+3 at ~120bpm → beat unit ~0.25s, bar ~1.75s
    unit = 0.22
    bar = unit * 7
    rng = np.random.default_rng(42)

    def place(at: float, sound: np.ndarray) -> None:
        j0 = int(at * SR)
        if 0 <= j0 < n:
            leng = min(len(sound), n - j0)
            out[j0 : j0 + leng] += sound[:leng]

    # A minor-ish folk palette
    roots = [220.00, 246.94, 196.00, 220.00]
    bars = int(seconds / bar) + 2
    for b in range(bars):
        t0 = b * bar
        if t0 >= seconds:
            break
        root = roots[b % len(roots)]
        chord = (root, root * 1.25, root * 1.5)

        # drone
        hold = min(bar * 1.05, seconds - t0)
        if hold > 0.05:
            tt = np.linspace(0, hold, int(hold * SR), False)
            shape = np.minimum(tt / 0.05, 1.0) * np.minimum((hold - tt) / 0.1, 1.0)
            pad = 0.04 * np.sin(2 * math.pi * root * 0.5 * tt)
            pad += 0.025 * np.sin(2 * math.pi * chord[1] * tt)
            place(t0, pad * np.clip(shape, 0, 1))

        # bouzouki-ish plucks on 7/8 accents: 1, 3, 5
        for step, amp in ((0, 1.0), (2, 0.85), (4, 1.0), (5, 0.55), (6, 0.7)):
            at = t0 + step * unit
            f0 = chord[step % 3] * (2 if step in (0, 4) else 1)
            tt = np.linspace(0, 0.35, int(0.35 * SR), False)
            pluck = (
                0.11 * amp * np.sin(2 * math.pi * f0 * tt)
                + 0.05 * amp * np.sin(2 * math.pi * f0 * 2 * tt)
                + 0.02 * amp * np.sin(2 * math.pi * f0 * 3 * tt)
            ) * np.exp(-5.5 * tt)
            place(at, pluck)

        # light daouli / hand drum
        for step, amp in ((0, 0.35), (2, 0.22), (4, 0.32)):
            at = t0 + step * unit
            tt = np.linspace(0, 0.18, int(0.18 * SR), False)
            drum = amp * np.sin(2 * math.pi * (90 + 40 * np.exp(-30 * tt)) * tt) * np.exp(-14 * tt)
            noise = rng.normal(0, 1, len(tt))
            drum += 0.08 * amp * noise * np.exp(-40 * tt)
            place(at, drum)

    # clarinet-ish melody hook
    melody = [440, 493.88, 523.25, 493.88, 440, 392, 349.23, 392, 440, 523.25, 493.88, 440]
    step = unit
    for i, f0 in enumerate(melody * (int(seconds / (step * len(melody))) + 1)):
        t0 = 0.4 + i * step
        if t0 >= seconds - 0.2:
            break
        leng = int(0.28 * SR)
        j0 = int(t0 * SR)
        if j0 >= n:
            break
        tt = np.linspace(0, 0.28, leng, False)
        # soft square-ish clarinet
        tone = 0.055 * np.sin(2 * math.pi * f0 * tt)
        tone += 0.025 * np.sin(2 * math.pi * f0 * 3 * tt) / 3
        tone *= np.exp(-3.2 * tt) * np.minimum(tt / 0.01, 1.0)
        sl = slice(j0, min(j0 + leng, n))
        out[sl] += tone[: sl.stop - sl.start]

    t = np.linspace(0, seconds, n, False)
    fade = np.minimum(np.minimum(t / 0.8, 1.0), np.minimum((seconds - t) / 1.5, 1.0))
    write_wav(dst, out * np.clip(fade, 0, 1) * 0.85)


async def speak(text: str, dst: Path, rate: str = RATE) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    last: Exception | None = None
    for attempt in range(8):
        try:
            # slightly higher pitch for sung verses
            pitch = "+4Hz" if "Taxi and Fly" in text and "εμπιστεύομαι" in text.replace("\n", " ") else "+0Hz"
            if any(x in text for x in ("πατρίδα", "καλημερίζω", "καλό μου ταξί")):
                pitch = "+6Hz"
            comm = edge_tts.Communicate(text, VOICE, rate=rate, pitch=pitch)
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
            time.sleep(0.8 + attempt * 0.3)
    raise RuntimeError(last)


def mix_audio(vo: Path, bed: Path, sting: Path, total: float, dst: Path) -> None:
    ff(
        "-i", str(bed), "-i", str(sting), "-i", str(vo),
        "-filter_complex",
        "[0:a]volume=0.32,afade=t=in:st=0:d=0.6,"
        f"afade=t=out:st={max(total - 1.4, 0.5):.2f}:d=1.2,"
        "aformat=sample_rates=44100:channel_layouts=stereo[m];"
        "[1:a]volume=0.48,aformat=sample_rates=44100:channel_layouts=stereo[s];"
        "[2:a]highpass=f=90,equalizer=f=220:t=q:w=1:g=1.2,equalizer=f=2800:t=q:w=1:g=1.1,"
        "acompressor=threshold=-18dB:ratio=1.5:attack=10:release=100,"
        "aformat=sample_rates=44100:channel_layouts=stereo,volume=1.18,"
        "apad=pad_dur=1.2[v];"
        "[m][s][v]amix=inputs=3:duration=longest:dropout_transition=0:normalize=0,"
        "loudnorm=I=-14:TP=-1.0:LRA=11,"
        f"alimiter=limit=0.96,atrim=0:{total:.3f},asetpts=PTS-STARTPTS[a]",
        "-map", "[a]", "-t", f"{total:.3f}",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k", str(dst),
    )


async def build() -> Path:
    work = BUILD
    work.mkdir(parents=True, exist_ok=True)

    parts: list[Path] = []
    scene_durs: list[float] = []
    hold = 0.55
    for i, (key, line) in enumerate(BEATS):
        mp3 = work / f"line_{i}.mp3"
        wav = work / f"line_{i}.wav"
        # sung verses a bit more rhythmic / upbeat
        rate = "+2%" if key.startswith("sing") else RATE
        await speak(line.replace("\n", " ") + ".", mp3, rate=rate)
        ff("-i", str(mp3), "-ac", "1", "-ar", "44100", str(wav))
        # light melodic pitch lift for sung lines
        if key.startswith("sing"):
            sung = work / f"line_{i}_sung.wav"
            ff(
                "-i", str(wav),
                "-af", "asetrate=44100*1.06,aresample=44100,atempo=0.96",
                str(sung),
            )
            wav = sung
        pad = work / f"line_{i}_pad.wav"
        ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{hold:.3f}", str(pad))
        d = duration(wav) + hold
        scene_durs.append(d)
        parts.extend([wav, pad])
        print(f"[tsolias] {key}: «{line.replace(chr(10), ' ')}» {d:.2f}s")

    brand_mp3 = work / "brand.mp3"
    brand_wav = work / "brand.wav"
    await speak("Taxi and Fly. Από και προς το αεροδρόμιο.", brand_mp3)
    ff("-i", str(brand_mp3), "-ac", "1", "-ar", "44100", str(brand_wav))
    brand_pad = work / "brand_pad.wav"
    ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "1.2", str(brand_pad))
    brand_dur = duration(brand_wav) + 1.2 + 1.2
    parts.extend([brand_wav, brand_pad])

    lst = work / "vo_join.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    vo_wav = work / "vo.wav"
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(vo_wav))

    story_dur = sum(scene_durs)
    brand_start = story_dur
    total = story_dur + brand_dur
    print(f"[tsolias] total {total:.2f}s")

    frames = work / "frames"
    shutil.rmtree(frames, ignore_errors=True)
    frames.mkdir(parents=True)
    idx = 0
    for (key, line), seconds in zip(BEATS, scene_durs):
        fn = SCENES[key]
        n = int(round(seconds * FPS))
        for i in range(n):
            img = fn(i / FPS, seconds, line)
            img.convert("RGB").save(frames / f"{idx:05d}.png")
            idx += 1
    need = int(round(total * FPS))
    while idx < need:
        img = brand_end(idx / FPS, brand_start)
        img.convert("RGB").save(frames / f"{idx:05d}.png")
        idx += 1

    silent = work / "silent.mp4"
    ff(
        "-framerate", str(FPS), "-i", str(frames / "%05d.png"),
        "-vf", "format=yuv420p,setsar=1",
        "-fps_mode", "cfr", "-r", str(FPS),
        "-frames:v", str(need),
        "-c:v", "libx264", "-preset", "medium", "-crf", "17",
        "-profile:v", "high", "-level", "4.0",
        "-an", str(silent),
    )

    vlen = duration(silent)
    bed = work / "bed.wav"
    folk_bed(vlen + 0.5, bed)
    sting = work / "sting.wav"
    logo_sting(vlen + 0.5, brand_start + 0.1, sting)
    audio = work / "mix.m4a"
    mix_audio(vo_wav, bed, sting, vlen, audio)

    tmp = work / "tmp.mp4"
    mix(silent, audio, tmp)
    ff(
        "-i", str(tmp),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high",
        "-preset", "medium", "-crf", "17",
        "-fps_mode", "cfr", "-r", str(FPS),
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
        "-movflags", "+faststart", str(OUT),
    )

    ART.mkdir(parents=True, exist_ok=True)
    (ART / "downloads").mkdir(parents=True, exist_ok=True)
    data = OUT.read_bytes()
    (ART / "taxi_and_fly_tsolias.mp4").write_bytes(data)
    (ART / "downloads" / "tsolias.mp4").write_bytes(data)
    shutil.rmtree(frames, ignore_errors=True)
    print("Wrote", OUT.name, round(duration(OUT), 2), "s")
    return OUT


if __name__ == "__main__":
    raise SystemExit(asyncio.run(build()) and 0)
