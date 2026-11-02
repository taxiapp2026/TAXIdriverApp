#!/usr/bin/env python3
"""Taxi and Fly Multi — clean motion split spot.

Smooth walkers → SPLIT → coins. Clear Greek VO (Μούλτι / σπλιτάρουμε).
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
WHITE = (245, 245, 245)
SOFT = (180, 180, 180)
INK = (25, 25, 25)
COIN = (60, 175, 100)
BG = (8, 8, 8, 255)
APP_URL = "taxiapp2026.github.io/taxi-client-app"
VOICE = "el-GR-NestorasNeural"
RATE = "+2%"  # clear but not rushed
BRAND_TAIL = 0.9

# Clear beats; VO phonetics for Multi; visuals timed to speech
BEATS = [
    ("intro", "Taxi and Fly Μούλτι.", 0.15),
    ("alone", "Μόνος, πενήντα.", 0.12),
    ("pair", "Παρέα. Ένα συν ένα.", 0.10),
    ("split2", "Σπλιτάρουμε. Είκοσι πέντε.", 0.12),
    ("trio", "Και τρίτος.", 0.10),
    ("split3", "Σπλιτάρουμε. Είκοσι.", 0.15),
    ("punch", "Εμείς σου βρίσκουμε την παρέα, εσύ σπλιτάρεις την τιμή.", 0.50),
    ("cta", "Μούλτι. Δοκίμασέ το.", 0.60),
]


def ease(k: float) -> float:
    k = max(0.0, min(k, 1.0))
    return 1 - (1 - k) ** 3


def ease_in_out(k: float) -> float:
    k = max(0.0, min(k, 1.0))
    return 0.5 - 0.5 * math.cos(math.pi * k)


def glow_layer() -> Image.Image:
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / 540.0) ** 2 + ((yy - H * 0.4) / 700.0) ** 2)
    a = np.clip(1.0 - d, 0.0, 1.0) ** 2.2 * 85.0
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
    img.alpha_composite(GLOW, (0, int(10 * math.sin(t * 0.4))))
    draw = ImageDraw.Draw(img)
    # soft road
    draw.rounded_rectangle((60, 1280, W - 60, 1360), radius=20, fill=(28, 28, 28, 255))
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
) -> None:
    """Smooth walking number-person (cycle synced to time)."""
    a = int(255 * max(0.0, min(alpha, 1.0)))
    if a < 8:
        return
    s = scale
    # walk cycle
    step = math.sin(t * 9.0 + phase)
    bob = abs(math.sin(t * 9.0 + phase)) * 5 * s
    arm = step * 22 * s
    leg = step * 26 * s

    head_r = 42 * s
    head_y = y - 95 * s - bob
    # head
    draw.ellipse(
        (x - head_r, head_y - head_r, x + head_r, head_y + head_r),
        fill=GOLD + (a,),
        outline=INK + (a,),
        width=5,
    )
    f = ImageFont.truetype(FONT, max(28, int(46 * s)))
    tw = draw.textlength(digit, font=f)
    draw.text((x - tw / 2, head_y - int(24 * s)), digit, font=f, fill=INK + (a,))

    body_top = head_y + head_r - 2
    hip = y - bob
    # torso
    draw.line((x, body_top, x, hip), fill=WHITE + (a,), width=max(5, int(7 * s)))
    # arms
    draw.line((x, body_top + 22 * s, x - 36 * s + arm, body_top + 58 * s), fill=WHITE + (a,), width=5)
    draw.line((x, body_top + 22 * s, x + 36 * s - arm, body_top + 58 * s), fill=WHITE + (a,), width=5)
    # legs
    draw.line((x, hip, x - 22 * s - leg, hip + 52 * s), fill=WHITE + (a,), width=5)
    draw.line((x, hip, x + 22 * s + leg, hip + 52 * s), fill=WHITE + (a,), width=5)


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
    bounce = (1 - pop) * 50 + math.sin(t * 5 + phase) * 3 * pop
    r = 62 * (0.55 + 0.45 * pop)
    cy = y - bounce
    a = int(255 * pop)
    draw.ellipse((x - r, cy - r, x + r, cy + r), fill=COIN + (a,), outline=GOLD + (a,), width=6)
    draw.ellipse((x - r + 8, cy - r + 8, x + r - 8, cy + r - 8), outline=GOLD + (int(160 * pop),), width=3)
    f = ImageFont.truetype(FONT, max(26, int(34 * pop + 8)))
    tw = draw.textlength(label, font=f)
    draw.text((x - tw / 2, cy - 20), label, font=f, fill=WHITE + (a,))


def split_banner(draw: ImageDraw.ImageDraw, y: float, t: float, show: float) -> None:
    show = max(0.0, min(show, 1.0))
    if show < 0.05:
        return
    pulse = 0.85 + 0.15 * math.sin(t * 12)
    f = ImageFont.truetype(FONT, 70)
    label = "SPLIT"
    tw = draw.textlength(label, font=f)
    pad_x, pad_y = 34, 14
    a = int(255 * show * pulse)
    box = (W / 2 - tw / 2 - pad_x, y, W / 2 + tw / 2 + pad_x, y + 70 + pad_y * 2)
    draw.rounded_rectangle(box, radius=18, outline=GOLD + (a,), width=6)
    draw.text(((W - tw) / 2, y + pad_y), label, font=f, fill=GOLD + (a,))


def scene_intro(t: float, local: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    k = ease(min(local / 0.4, 1.0))
    text_c(draw, "Taxi and Fly Multi", H / 2 - 50, 58, WHITE + (int(255 * k),))
    bar = 240 * k
    draw.rounded_rectangle(
        (W / 2 - bar / 2, H / 2 + 40, W / 2 + bar / 2, H / 2 + 47),
        radius=4,
        fill=GOLD + (int(230 * k),),
    )
    return img


def scene_alone(t: float, local: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    # walk from left toward center
    p = ease_in_out(min(local / 2.2, 1.0))
    x = 160 + p * 380
    walker(draw, x, 1240, "1", local, 0.0, 1.0, 1.2)
    price = ease(min(max((local - 0.5) / 0.4, 0.0), 1.0))
    text_c(draw, "50€", 400 + (1 - price) * 24, 130, WHITE + (int(255 * price),))
    text_c(draw, "μόνος", 560, 40, SOFT + (int(200 * price),), FONT_REG)
    return img


def scene_pair(t: float, local: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    text_c(draw, "1 + 1", 360, 88, GOLD + (255,))
    # second walks in from right to meet first
    p = ease_in_out(min(local / 2.0, 1.0))
    x1 = 360
    x2 = 980 - p * 340
    walker(draw, x1, 1240, "1", local, 0.0, 1.0, 1.05)
    walker(draw, x2, 1240, "1", local, 1.7, 1.0, 1.05)
    if p > 0.85:
        hi = ease((p - 0.85) / 0.15)
        text_c(draw, "παρέα!", 500, 46, WHITE + (int(230 * hi),))
    return img


def scene_split2(t: float, local: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    # walkers dissolve → coins
    morph = ease_in_out(min(local / 0.7, 1.0))
    walker(draw, W / 2 - 150, 1240, "1", local, 0.0, 1.0 - morph, 1.0)
    walker(draw, W / 2 + 150, 1240, "1", local, 1.5, 1.0 - morph, 1.0)
    split_banner(draw, 420, local, ease(min(local / 0.25, 1.0)))
    pop = ease(min(max((local - 0.35) / 0.45, 0.0), 1.0))
    coin(draw, W / 2 - 170, 1120, "25€", pop, local, 0.0)
    coin(draw, W / 2 + 170, 1120, "25€", pop, local, 1.2)
    text_c(draw, "ο καθένας", 1300, 36, SOFT + (int(210 * pop),), FONT_REG)
    return img


def scene_trio(t: float, local: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    text_c(draw, "1 + 2", 360, 88, GOLD + (255,))
    p = ease_in_out(min(local / 1.8, 1.0))
    x3 = 1000 - p * 420
    walker(draw, W / 2 - 200, 1240, "1", local, 0.0, 1.0, 0.98)
    walker(draw, W / 2, 1240, "1", local, 1.2, 1.0, 0.98)
    walker(draw, x3, 1240, "1", local, 2.4, 1.0, 0.98)
    if p > 0.8:
        hi = ease((p - 0.8) / 0.2)
        text_c(draw, "και τρίτος!", 500, 44, WHITE + (int(230 * hi),))
    return img


def scene_split3(t: float, local: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    morph = ease_in_out(min(local / 0.65, 1.0))
    for i, ox in enumerate((-200, 0, 200)):
        walker(draw, W / 2 + ox, 1240, "1", local, i * 1.1, 1.0 - morph, 0.95)
    split_banner(draw, 400, local, ease(min(local / 0.25, 1.0)))
    pop = ease(min(max((local - 0.3) / 0.45, 0.0), 1.0))
    for i, ox in enumerate((-230, 0, 230)):
        coin(draw, W / 2 + ox, 1100, "20€", pop, local, i * 0.9)
    text_c(draw, "ο καθένας", 1300, 36, SOFT + (int(210 * pop),), FONT_REG)
    return img


def scene_punch(t: float, local: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    k = ease(min(local / 0.35, 1.0))
    a = int(255 * k)
    lines = [
        ("Εμείς σου βρίσκουμε την παρέα", WHITE, 42),
        ("εσύ σπλιτάρεις την τιμή", GOLD, 50),
    ]
    y = H / 2 - 110
    for text, color, size in lines:
        f = ImageFont.truetype(FONT, size)
        while draw.textlength(text, font=f) > 940 and size > 26:
            size -= 2
            f = ImageFont.truetype(FONT, size)
        tw = draw.textlength(text, font=f)
        draw.text(((W - tw) / 2, y), text, font=f, fill=color + (a,))
        y += size + 28
    bar = 260 * k
    draw.rounded_rectangle(
        (W / 2 - bar / 2, y + 10, W / 2 + bar / 2, y + 17),
        radius=4,
        fill=GOLD + (int(230 * k),),
    )
    return img


def scene_cta(t: float, local: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    k = ease(min(local / 0.4, 1.0))
    a = int(255 * k)
    text_c(draw, "Taxi and Fly Multi", H / 2 - 110, 56, WHITE + (a,))
    text_c(draw, "Δοκίμασέ το", H / 2 - 10, 70, GOLD + (a,))
    bar = 280 * k
    draw.rounded_rectangle(
        (W / 2 - bar / 2, H / 2 + 90, W / 2 + bar / 2, H / 2 + 97),
        radius=4,
        fill=GOLD + (int(230 * k),),
    )
    pop = ease(min(max((local - 0.25) / 0.4, 0.0), 1.0))
    coin(draw, 210, 1280, "€", pop, local, 0.0)
    coin(draw, W - 210, 1280, "€", pop, local, 1.4)
    return img


SCENES = {
    "intro": scene_intro,
    "alone": scene_alone,
    "pair": scene_pair,
    "split2": scene_split2,
    "trio": scene_trio,
    "split3": scene_split3,
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
    fade = ease(min(max((since - 0.1) / 0.35, 0.0), 1.0))
    f_brand = ImageFont.truetype(FONT, 58)
    f_cta = ImageFont.truetype(FONT, 48)
    f_url = ImageFont.truetype(FONT_REG, 26)
    for text, font, y, color in (
        ("Taxi and Fly Multi", f_brand, 960, GOLD),
        ("Δοκίμασέ το", f_cta, 1050, WHITE),
    ):
        tw = draw.textlength(text, font=font)
        draw.text(((W - tw) / 2, y), text, font=font, fill=color + (int(255 * fade),))
    uw = draw.textlength(APP_URL, font=f_url)
    draw.text(((W - uw) / 2, 1150), APP_URL, font=f_url, fill=SOFT + (int(210 * fade),))
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
        "[0:a]volume=0.15,afade=t=in:st=0:d=0.5,"
        f"afade=t=out:st={max(total - 1.3, 0.4):.2f}:d=1.1,"
        "aformat=sample_rates=44100:channel_layouts=stereo[m];"
        "[1:a]volume=0.38,aformat=sample_rates=44100:channel_layouts=stereo[s];"
        "[2:a]highpass=f=90,equalizer=f=220:t=q:w=1:g=1.2,equalizer=f=2800:t=q:w=1:g=1.1,"
        "acompressor=threshold=-18dB:ratio=1.5:attack=10:release=100,"
        "aformat=sample_rates=44100:channel_layouts=stereo,volume=1.14,"
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
        # ensure enough visual time for walk/split motion
        min_vis = {
            "alone": 2.0,
            "pair": 2.1,
            "split2": 1.9,
            "trio": 1.9,
            "split3": 1.9,
        }.get(key, 0.0)
        d_vo = duration(wav) + hold
        extra = max(0.0, min_vis - d_vo)
        if extra > 0.05:
            pad2 = work / f"line_{i}_extra.wav"
            ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{extra:.3f}", str(pad2))
            pad = work / f"line_{i}_pad.wav"
            ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{hold:.3f}", str(pad))
            d = d_vo + extra
            parts.extend([wav, pad, pad2])
        else:
            pad = work / f"line_{i}_pad.wav"
            ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{hold:.3f}", str(pad))
            d = d_vo
            parts.extend([wav, pad])
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
    xfade = 0.30
    for i, (key, seconds) in enumerate(zip(keys, scene_durs)):
        n = int(round(seconds * FPS))
        fn = SCENES[key]
        for j in range(n):
            local = j / FPS
            t = idx / FPS
            base = fn(t, local)
            remaining = seconds - local
            if remaining < xfade and i < len(keys) - 1:
                k = ease(1.0 - remaining / xfade)
                nxt = SCENES[keys[i + 1]](t, 0.0)
                base = blend(base, nxt, k * 0.7)
            elif remaining < xfade and i == len(keys) - 1:
                k = ease(1.0 - remaining / xfade)
                nxt = brand_frame(brand_start, brand_start)
                base = blend(base, nxt, k * 0.6)
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
