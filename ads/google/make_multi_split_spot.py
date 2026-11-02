#!/usr/bin/env python3
"""Taxi and Fly Multi — polished motion split spot.

Careful timing: walks finish before SPLIT; VO clear (Μούλτι / σπλιτάρουμε).
Punch: Εμείς σου βρίσκουμε την παρέα, εσύ σπλιτάρεις την τιμή.
End: Taxi and Fly Multi — Δοκίμασέ το.
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
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build" / "multi_split"
ART = Path("/opt/cursor/artifacts")
OUT = ROOT / "taxi-and-fly-multi-split.mp4"

sys.path.insert(0, str(ROOT))
from build_video import FONT, FONT_REG, duration, ff, mix  # noqa: E402
from rebuild_brand_process import icon_lettering  # noqa: E402
from spot_audio import hope_music, logo_sting  # noqa: E402

W, H, FPS = 1080, 1920, 30
GOLD = (255, 210, 40)
WHITE = (248, 248, 248)
SOFT = (175, 175, 175)
INK = (22, 22, 22)
COIN = (55, 168, 95)
ROAD = (32, 32, 32)
BG = (8, 8, 8, 255)
APP_URL = "taxiapp2026.github.io/taxi-client-app"
VOICE = "el-GR-NestorasNeural"
RATE = "+0%"
BRAND_TAIL = 1.0

# spoken, hold after — scene key drives visuals; animation uses local/dur
BEATS = [
    ("intro", "Taxi and Fly Μούλτι.", 0.30),
    ("alone", "Μόνος σου. Πενήντα ευρώ.", 0.25),
    ("pair", "Έρχεται παρέα. Σπλιτάρουμε. Είκοσι πέντε.", 0.30),
    ("trio", "Και τρίτος. Σπλιτάρουμε. Είκοσι.", 0.35),
    ("punch", "Εμείς σου βρίσκουμε την παρέα, εσύ σπλιτάρεις την τιμή.", 0.85),
    ("cta", "Taxi and Fly Μούλτι. Δοκίμασέ το.", 0.90),
]

# minimum visual seconds so walks can finish cleanly
MIN_VIS = {
    "alone": 2.6,
    "pair": 4.2,
    "trio": 4.0,
}


def ease(k: float) -> float:
    k = max(0.0, min(k, 1.0))
    return 1 - (1 - k) ** 3


def ease_in_out(k: float) -> float:
    k = max(0.0, min(k, 1.0))
    return 0.5 - 0.5 * math.cos(math.pi * k)


def glow_layer() -> Image.Image:
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / 520.0) ** 2 + ((yy - H * 0.38) / 680.0) ** 2)
    a = np.clip(1.0 - d, 0.0, 1.0) ** 2.3 * 80.0
    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = GOLD
    rgba[..., 3] = a.astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


GLOW = glow_layer()
BADGE: Image.Image | None = None


def badge_image() -> Image.Image:
    global BADGE
    if BADGE is None:
        size = 500
        mark = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(mark)
        d.ellipse((10, 10, size - 10, size - 10), outline=GOLD + (255,), width=16)
        letters = icon_lettering()
        inner = int(size * 0.58)
        sc = min(inner / letters.width, inner / letters.height)
        letters = letters.resize(
            (max(1, int(letters.width * sc)), max(1, int(letters.height * sc))),
            Image.Resampling.LANCZOS,
        )
        mark.alpha_composite(letters, ((size - letters.width) // 2, (size - letters.height) // 2))
        BADGE = mark
    return BADGE


def background(t: float) -> Image.Image:
    img = Image.new("RGBA", (W, H), BG)
    img.alpha_composite(GLOW, (0, int(8 * math.sin(t * 0.35))))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((50, 1290, W - 50, 1375), radius=24, fill=ROAD + (255,))
    # soft lane mark
    for i in range(6):
        x0 = 120 + i * 150
        draw.rounded_rectangle((x0, 1326, x0 + 70, 1336), radius=3, fill=(55, 55, 55, 255))
    return img


def text_c(draw, text: str, y: float, size: int, fill, font_path=FONT) -> None:
    f = ImageFont.truetype(font_path, size)
    while draw.textlength(text, font=f) > 960 and size > 24:
        size -= 2
        f = ImageFont.truetype(font_path, size)
    tw = draw.textlength(text, font=f)
    draw.text(((W - tw) / 2, y), text, font=f, fill=fill)


def walker(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    digit: str,
    t: float,
    phase: float = 0.0,
    alpha: float = 1.0,
    scale: float = 1.0,
    moving: float = 1.0,
) -> None:
    """Number-head figure. moving=0 freezes pose; moving=1 full walk cycle."""
    a = int(255 * max(0.0, min(alpha, 1.0)))
    if a < 10:
        return
    s = scale
    moving = max(0.0, min(moving, 1.0))
    step = math.sin(t * 8.5 + phase) * moving
    bob = abs(math.sin(t * 8.5 + phase)) * 4.5 * s * moving
    arm = step * 20 * s
    leg = step * 24 * s

    head_r = 44 * s
    head_y = y - 100 * s - bob
    # soft shadow
    draw.ellipse((x - 28 * s, y + 48 * s, x + 28 * s, y + 62 * s), fill=(0, 0, 0, int(50 * alpha)))
    # head
    draw.ellipse(
        (x - head_r, head_y - head_r, x + head_r, head_y + head_r),
        fill=GOLD + (a,),
        outline=INK + (a,),
        width=5,
    )
    f = ImageFont.truetype(FONT, max(30, int(48 * s)))
    tw = draw.textlength(digit, font=f)
    draw.text((x - tw / 2, head_y - int(26 * s)), digit, font=f, fill=INK + (a,))

    body_top = head_y + head_r
    hip = y - bob
    thick = max(6, int(8 * s))
    draw.line((x, body_top, x, hip), fill=WHITE + (a,), width=thick)
    draw.line((x, body_top + 24 * s, x - 34 * s + arm, body_top + 60 * s), fill=WHITE + (a,), width=6)
    draw.line((x, body_top + 24 * s, x + 34 * s - arm, body_top + 60 * s), fill=WHITE + (a,), width=6)
    # legs to ground
    foot_y = hip + 55 * s
    draw.line((x, hip, x - 20 * s - leg, foot_y), fill=WHITE + (a,), width=6)
    draw.line((x, hip, x + 20 * s + leg, foot_y), fill=WHITE + (a,), width=6)


def coin(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    label: str,
    pop: float,
    t: float,
    phase: float = 0.0,
) -> None:
    pop = max(0.0, min(pop, 1.0))
    if pop < 0.02:
        return
    # settle bounce
    bounce = (1 - pop) ** 2 * 55 + math.sin(t * 4.5 + phase) * 2.5 * pop
    r = 66 * (0.5 + 0.5 * pop)
    cy = y - bounce
    a = int(255 * pop)
    draw.ellipse((x - r - 4, cy + r - 6, x + r + 4, cy + r + 10), fill=(0, 0, 0, int(40 * pop)))
    draw.ellipse((x - r, cy - r, x + r, cy + r), fill=COIN + (a,), outline=GOLD + (a,), width=6)
    draw.ellipse((x - r + 9, cy - r + 9, x + r - 9, cy + r - 9), outline=GOLD + (int(150 * pop),), width=3)
    f = ImageFont.truetype(FONT, max(28, int(36 * pop + 6)))
    tw = draw.textlength(label, font=f)
    draw.text((x - tw / 2, cy - 22), label, font=f, fill=WHITE + (a,))


def split_banner(draw: ImageDraw.ImageDraw, y: float, t: float, show: float) -> None:
    show = max(0.0, min(show, 1.0))
    if show < 0.04:
        return
    # scale pop then settle
    pop = ease(min(show / 0.35, 1.0))
    pulse = 0.92 + 0.08 * math.sin(t * 10) * show
    size = int(64 + 12 * pop)
    f = ImageFont.truetype(FONT, size)
    label = "SPLIT"
    tw = draw.textlength(label, font=f)
    pad_x, pad_y = 32, 12
    a = int(255 * show)
    cx = W / 2
    box = (
        cx - tw / 2 * pulse - pad_x,
        y,
        cx + tw / 2 * pulse + pad_x,
        y + size + pad_y * 2,
    )
    draw.rounded_rectangle(box, radius=16, fill=(35, 32, 12, int(180 * show)), outline=GOLD + (a,), width=6)
    draw.text((cx - tw / 2, y + pad_y), label, font=f, fill=GOLD + (a,))


def scene_intro(t: float, local: float, dur: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    k = ease(min(local / 0.45, 1.0))
    text_c(draw, "Taxi and Fly Multi", H / 2 - 55, 58, WHITE + (int(255 * k),))
    bar = 250 * k
    draw.rounded_rectangle(
        (W / 2 - bar / 2, H / 2 + 35, W / 2 + bar / 2, H / 2 + 42),
        radius=4,
        fill=GOLD + (int(230 * k),),
    )
    return img


def scene_alone(t: float, local: float, dur: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    # 0–70% walk to center, then stand
    p = ease_in_out(min(local / max(dur * 0.72, 0.1), 1.0))
    x = 150 + p * 390
    moving = 1.0 if p < 0.98 else 0.0
    walker(draw, x, 1255, "1", t, 0.0, 1.0, 1.18, moving=moving)
    # price after he arrives a bit
    price = ease(min(max((local - dur * 0.35) / 0.4, 0.0), 1.0))
    text_c(draw, "50€", 390 + (1 - price) * 18, 128, WHITE + (int(255 * price),))
    text_c(draw, "μόνος", 545, 38, SOFT + (int(200 * price),), FONT_REG)
    return img


def scene_pair(t: float, local: float, dur: float) -> Image.Image:
    """Meet as παρέα (first ~55%), then SPLIT → 25€."""
    img = background(t)
    draw = ImageDraw.Draw(img)
    u = local / max(dur, 0.01)
    text_c(draw, "1 + 1", 340, 86, GOLD + (255,))

    if u < 0.52:
        # walk together
        p = ease_in_out(u / 0.52)
        x1 = 340
        x2 = 1000 - p * 380
        walker(draw, x1, 1255, "1", t, 0.0, 1.0, 1.05, moving=0.15)
        walker(draw, x2, 1255, "1", t, 1.8, 1.0, 1.05, moving=1.0 if p < 0.97 else 0.0)
        if p > 0.82:
            hi = ease((p - 0.82) / 0.18)
            text_c(draw, "παρέα!", 480, 44, WHITE + (int(235 * hi),))
    else:
        # SPLIT morph
        s = (u - 0.52) / 0.48
        morph = ease_in_out(min(s / 0.35, 1.0))
        walker(draw, W / 2 - 155, 1255, "1", t, 0.0, 1.0 - morph, 1.0 - 0.25 * morph, moving=0.0)
        walker(draw, W / 2 + 155, 1255, "1", t, 1.5, 1.0 - morph, 1.0 - 0.25 * morph, moving=0.0)
        split_banner(draw, 430, t, ease(min(s / 0.2, 1.0)))
        pop = ease(min(max((s - 0.22) / 0.4, 0.0), 1.0))
        coin(draw, W / 2 - 175, 1140, "25€", pop, t, 0.0)
        coin(draw, W / 2 + 175, 1140, "25€", pop, t, 1.1)
        text_c(draw, "ο καθένας", 1320, 34, SOFT + (int(210 * pop),), FONT_REG)
    return img


def scene_trio(t: float, local: float, dur: float) -> Image.Image:
    """Third joins (~50%), then SPLIT → 20€."""
    img = background(t)
    draw = ImageDraw.Draw(img)
    u = local / max(dur, 0.01)
    text_c(draw, "1 + 2", 340, 86, GOLD + (255,))

    if u < 0.50:
        p = ease_in_out(u / 0.50)
        x3 = 1020 - p * 440
        walker(draw, W / 2 - 210, 1255, "1", t, 0.0, 1.0, 0.98, moving=0.1)
        walker(draw, W / 2, 1255, "1", t, 1.2, 1.0, 0.98, moving=0.1)
        walker(draw, x3, 1255, "1", t, 2.5, 1.0, 0.98, moving=1.0 if p < 0.97 else 0.0)
        if p > 0.8:
            hi = ease((p - 0.8) / 0.2)
            text_c(draw, "και τρίτος!", 480, 42, WHITE + (int(235 * hi),))
    else:
        s = (u - 0.50) / 0.50
        morph = ease_in_out(min(s / 0.35, 1.0))
        for i, ox in enumerate((-210, 0, 210)):
            walker(draw, W / 2 + ox, 1255, "1", t, i * 1.1, 1.0 - morph, 0.95 - 0.2 * morph, moving=0.0)
        split_banner(draw, 410, t, ease(min(s / 0.2, 1.0)))
        pop = ease(min(max((s - 0.2) / 0.4, 0.0), 1.0))
        for i, ox in enumerate((-235, 0, 235)):
            coin(draw, W / 2 + ox, 1120, "20€", pop, t, i * 0.85)
        text_c(draw, "ο καθένας", 1320, 34, SOFT + (int(210 * pop),), FONT_REG)
    return img


def scene_punch(t: float, local: float, dur: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    k = ease(min(local / 0.4, 1.0))
    a = int(255 * k)
    # line 1 then line 2 stagger
    k2 = ease(min(max((local - 0.35) / 0.4, 0.0), 1.0))
    lines = [
        ("Εμείς σου βρίσκουμε την παρέα", WHITE, 42, k),
        ("εσύ σπλιτάρεις την τιμή", GOLD, 50, k2),
    ]
    y = H / 2 - 115
    for text, color, size, kk in lines:
        f = ImageFont.truetype(FONT, size)
        while draw.textlength(text, font=f) > 940 and size > 26:
            size -= 2
            f = ImageFont.truetype(FONT, size)
        tw = draw.textlength(text, font=f)
        draw.text(((W - tw) / 2, y), text, font=f, fill=color + (int(255 * kk),))
        y += size + 30
    bar = 270 * k2
    if bar > 2:
        draw.rounded_rectangle(
            (W / 2 - bar / 2, y + 8, W / 2 + bar / 2, y + 15),
            radius=4,
            fill=GOLD + (int(230 * k2),),
        )
    return img


def scene_cta(t: float, local: float, dur: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    k = ease(min(local / 0.4, 1.0))
    a = int(255 * k)
    text_c(draw, "Taxi and Fly Multi", H / 2 - 120, 56, WHITE + (a,))
    k2 = ease(min(max((local - 0.25) / 0.4, 0.0), 1.0))
    text_c(draw, "Δοκίμασέ το", H / 2 - 15, 70, GOLD + (int(255 * k2),))
    bar = 280 * k2
    draw.rounded_rectangle(
        (W / 2 - bar / 2, H / 2 + 85, W / 2 + bar / 2, H / 2 + 92),
        radius=4,
        fill=GOLD + (int(230 * k2),),
    )
    pop = ease(min(max((local - 0.35) / 0.4, 0.0), 1.0))
    coin(draw, 200, 1280, "€", pop, t, 0.0)
    coin(draw, W - 200, 1280, "€", pop, t, 1.3)
    return img


SCENES = {
    "intro": scene_intro,
    "alone": scene_alone,
    "pair": scene_pair,
    "trio": scene_trio,
    "punch": scene_punch,
    "cta": scene_cta,
}


def brand_frame(t: float, start: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    since = max(t - start, 0.0)
    k = ease(min(since / 0.5, 1.0))
    mark = badge_image()
    size = int(460 * (0.92 + 0.08 * k))
    mark = mark.resize((size, size), Image.Resampling.LANCZOS)
    img.alpha_composite(mark, ((W - size) // 2, 400))
    fade = ease(min(max((since - 0.12) / 0.4, 0.0), 1.0))
    f_brand = ImageFont.truetype(FONT, 56)
    f_cta = ImageFont.truetype(FONT, 48)
    f_url = ImageFont.truetype(FONT_REG, 26)
    for text, font, y, color in (
        ("Taxi and Fly Multi", f_brand, 960, GOLD),
        ("Δοκίμασέ το", f_cta, 1045, WHITE),
    ):
        tw = draw.textlength(text, font=font)
        draw.text(((W - tw) / 2, y), text, font=font, fill=color + (int(255 * fade),))
    uw = draw.textlength(APP_URL, font=f_url)
    draw.text(((W - uw) / 2, 1145), APP_URL, font=f_url, fill=SOFT + (int(210 * fade),))
    return img


def blend(a: Image.Image, b: Image.Image, k: float) -> Image.Image:
    k = max(0.0, min(k, 1.0))
    return Image.blend(a.convert("RGB"), b.convert("RGB"), k).convert("RGBA")


async def speak(text: str, dst: Path, rate: str = RATE) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    last: Exception | None = None
    for attempt in range(8):
        try:
            comm = edge_tts.Communicate(text, VOICE, rate=rate, pitch="+0Hz")
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
        "[0:a]volume=0.14,afade=t=in:st=0:d=0.5,"
        f"afade=t=out:st={max(total - 1.3, 0.4):.2f}:d=1.1,"
        "aformat=sample_rates=44100:channel_layouts=stereo[m];"
        "[1:a]volume=0.36,aformat=sample_rates=44100:channel_layouts=stereo[s];"
        "[2:a]highpass=f=90,equalizer=f=220:t=q:w=1:g=1.2,equalizer=f=2800:t=q:w=1:g=1.15,"
        "acompressor=threshold=-18dB:ratio=1.5:attack=10:release=100,"
        "aformat=sample_rates=44100:channel_layouts=stereo,volume=1.16,"
        "apad=pad_dur=0.8[v];"
        "[m][s][v]amix=inputs=3:duration=longest:dropout_transition=0:normalize=0,"
        "loudnorm=I=-14:TP=-1.0:LRA=11,"
        f"alimiter=limit=0.96,atrim=0:{total:.3f},asetpts=PTS-STARTPTS[a]",
        "-map", "[a]", "-t", f"{total:.3f}",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k", str(dst),
    )


async def build() -> Path:
    work = BUILD
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)

    parts: list[Path] = []
    scene_durs: list[float] = []
    keys: list[str] = []
    for i, (key, spoken, hold) in enumerate(BEATS):
        mp3 = work / f"line_{i}.mp3"
        wav = work / f"line_{i}.wav"
        await speak(spoken, mp3)
        ff("-i", str(mp3), "-ac", "1", "-ar", "44100", str(wav))
        d_vo = duration(wav) + hold
        need = MIN_VIS.get(key, 0.0)
        extra = max(0.0, need - d_vo)
        pad = work / f"line_{i}_pad.wav"
        ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{hold:.3f}", str(pad))
        chunks = [wav, pad]
        if extra > 0.05:
            pad2 = work / f"line_{i}_extra.wav"
            ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{extra:.3f}", str(pad2))
            chunks.append(pad2)
        d = d_vo + extra
        parts.extend(chunks)
        scene_durs.append(d)
        keys.append(key)
        print(f"[split] {key}: «{spoken}» {d:.2f}s")

    brand_pad = work / "brand_pad.wav"
    ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{BRAND_TAIL:.3f}", str(brand_pad))
    parts.append(brand_pad)

    lst = work / "vo_join.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    vo_wav = work / "vo.wav"
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(vo_wav))

    story_dur = sum(scene_durs)
    brand_start = story_dur
    total = story_dur + BRAND_TAIL
    print(f"[split] total {total:.2f}s")

    frames = work / "frames"
    frames.mkdir(parents=True)
    idx = 0
    xfade = 0.28
    for i, (key, seconds) in enumerate(zip(keys, scene_durs)):
        n = int(round(seconds * FPS))
        fn = SCENES[key]
        for j in range(n):
            local = j / FPS
            t = idx / FPS
            base = fn(t, local, seconds)
            remaining = seconds - local
            if remaining < xfade and i < len(keys) - 1:
                k = ease(1.0 - remaining / xfade)
                nxt = SCENES[keys[i + 1]](t, 0.0, scene_durs[i + 1])
                base = blend(base, nxt, k * 0.65)
            elif remaining < xfade and i == len(keys) - 1:
                k = ease(1.0 - remaining / xfade)
                nxt = brand_frame(brand_start, brand_start)
                base = blend(base, nxt, k * 0.55)
            base.convert("RGB").save(frames / f"{idx:05d}.png")
            idx += 1

    need = int(round(total * FPS))
    while idx < need:
        brand_frame(idx / FPS, brand_start).convert("RGB").save(frames / f"{idx:05d}.png")
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
    hope_music(vlen + 0.4, bed)
    sting = work / "sting.wav"
    logo_sting(vlen + 0.4, brand_start + 0.1, sting)
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
    (ART / "taxi-and-fly-multi-split.mp4").write_bytes(data)
    (ART / "downloads" / "taxi-and-fly-multi-split.mp4").write_bytes(data)
    shutil.rmtree(frames, ignore_errors=True)
    print("Wrote", OUT.name, round(duration(OUT), 2), "s")
    return OUT


if __name__ == "__main__":
    raise SystemExit(asyncio.run(build()) and 0)
