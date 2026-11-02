#!/usr/bin/env python3
"""Humorous Taxi and Fly Multi split: numbers walk as παρέα → become money on SPLIT.

End card: Taxi and Fly Multi — Δοκίμασέ το.
VO: Μούλτι. On-screen: Multi / SPLIT.
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
SOFT = (190, 190, 190)
INK = (20, 20, 20)
GREEN = (70, 190, 110)
BG = (8, 8, 8, 255)
APP_URL = "taxiapp2026.github.io/taxi-client-app"
VOICE = "el-GR-NestorasNeural"
RATE = "+10%"
BRAND_TAIL = 0.85

# Fewer VO beats — visuals do the joke; punch is their exact line
BEATS = [
    ("intro", "Taxi and Fly Μούλτι.", 0.10),
    ("walk1", "Πενήντα.", 0.06),
    ("pair", "Παρέα. Σπλιτ. Είκοσι πέντε.", 0.08),
    ("trio", "Τρίτος. Σπλιτ. Είκοσι.", 0.08),
    ("punch", "Εμείς σου βρίσκουμε την παρέα, εσύ σπλιτάρεις την τιμή.", 0.45),
    ("cta", "Δοκίμασέ το.", 0.55),
]


def ease(k: float) -> float:
    k = max(0.0, min(k, 1.0))
    return 1 - (1 - k) ** 3


def glow_layer() -> Image.Image:
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / 540.0) ** 2 + ((yy - H * 0.42) / 720.0) ** 2)
    a = np.clip(1.0 - d, 0.0, 1.0) ** 2.2 * 90.0
    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = GOLD
    rgba[..., 3] = a.astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


GLOW = glow_layer()
BADGE: Image.Image | None = None


def badge_image() -> Image.Image:
    global BADGE
    if BADGE is None:
        size = 520
        mark = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(mark)
        d.ellipse((12, 12, size - 12, size - 12), outline=GOLD + (255,), width=16)
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
    img.alpha_composite(GLOW, (0, int(12 * math.sin(t * 0.45))))
    # ground line for walking
    draw = ImageDraw.Draw(img)
    draw.line((80, 1320, W - 80, 1320), fill=(50, 50, 50, 255), width=4)
    return img


def draw_centered(draw, text: str, y: float, size: int, fill, font_path=FONT) -> None:
    f = ImageFont.truetype(font_path, size)
    while draw.textlength(text, font=f) > 960 and size > 26:
        size -= 2
        f = ImageFont.truetype(font_path, size)
    tw = draw.textlength(text, font=f)
    draw.text(((W - tw) / 2, y), text, font=f, fill=fill)


def number_walker(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    digit: str,
    local: float,
    phase: float = 0.0,
    scale: float = 1.0,
) -> None:
    """Funny number-head stick figure that walks in place / along."""
    s = scale
    bob = math.sin(local * 10 + phase) * 6 * s
    swing = math.sin(local * 10 + phase) * 18
    head_y = cy - 90 * s + bob
    # head circle with digit
    r = 48 * s
    draw.ellipse((cx - r, head_y - r, cx + r, head_y + r), fill=GOLD + (255,), outline=INK + (255,), width=5)
    f = ImageFont.truetype(FONT, int(52 * s))
    tw = draw.textlength(digit, font=f)
    draw.text((cx - tw / 2, head_y - int(28 * s)), digit, font=f, fill=INK + (255,))
    # body
    body_top = head_y + r - 4
    body_bot = cy + bob
    draw.line((cx, body_top, cx, body_bot), fill=WHITE + (255,), width=max(6, int(8 * s)))
    # arms
    draw.line((cx, body_top + 25 * s, cx - 40 * s + swing * 0.3, body_top + 55 * s), fill=WHITE + (255,), width=6)
    draw.line((cx, body_top + 25 * s, cx + 40 * s - swing * 0.3, body_top + 55 * s), fill=WHITE + (255,), width=6)
    # legs walking
    draw.line((cx, body_bot, cx - 28 * s - swing * 0.5, body_bot + 55 * s), fill=WHITE + (255,), width=6)
    draw.line((cx, body_bot, cx + 28 * s + swing * 0.5, body_bot + 55 * s), fill=WHITE + (255,), width=6)


def money_coin(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    amount: str,
    local: float,
    phase: float = 0.0,
    pop: float = 1.0,
) -> None:
    """Coin that bounces in after SPLIT."""
    bounce = (1 - pop) * 40 + abs(math.sin(local * 6 + phase)) * 4 * pop
    y = cy - bounce
    r = 70 * (0.7 + 0.3 * pop)
    draw.ellipse((cx - r, y - r, cx + r, y + r), fill=GREEN + (255,), outline=GOLD + (255,), width=7)
    draw.ellipse((cx - r + 10, y - r + 10, cx + r - 10, y + r - 10), outline=GOLD + (180,), width=3)
    f = ImageFont.truetype(FONT, int(36 + 10 * pop))
    tw = draw.textlength(amount, font=f)
    draw.text((cx - tw / 2, y - 22), amount, font=f, fill=WHITE + (255,))


def split_badge(draw: ImageDraw.ImageDraw, y: float, local: float) -> None:
    flash = 0.75 + 0.25 * math.sin(local * 14)
    f = ImageFont.truetype(FONT, 78)
    tw = draw.textlength("SPLIT!", font=f)
    pad_x, pad_y = 40, 16
    box = (W / 2 - tw / 2 - pad_x, y, W / 2 + tw / 2 + pad_x, y + 78 + pad_y * 2)
    draw.rounded_rectangle(box, radius=22, fill=(40, 40, 20, int(200 * flash)), outline=GOLD + (255,), width=7)
    draw.text(((W - tw) / 2, y + pad_y), "SPLIT!", font=f, fill=GOLD + (255,))


def scene_intro(t: float, local: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    fade = ease(min(local / 0.3, 1.0))
    draw_centered(draw, "Taxi and Fly Multi", H / 2 - 60, 56, WHITE + (int(255 * fade),))
    bar = 240 * fade
    draw.rounded_rectangle(
        (W / 2 - bar / 2, H / 2 + 30, W / 2 + bar / 2, H / 2 + 37),
        radius=4,
        fill=GOLD + (int(230 * fade),),
    )
    return img


def scene_walk1(t: float, local: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    # lonely walker crossing
    x = 180 + min(local / 1.8, 1.0) * 360
    number_walker(draw, x, 1180, "1", local, 0.0, 1.15)
    pop = ease(min(max((local - 0.4) / 0.35, 0.0), 1.0))
    draw_centered(draw, "50€", 420 + (1 - pop) * 20, 120, WHITE + (int(255 * pop),))
    draw_centered(draw, "μόνος… βαριά η τσέπη", 560, 36, SOFT + (int(200 * pop),), FONT_REG)
    return img


def scene_pair(t: float, local: float) -> Image.Image:
    """1+1 walk as παρέα, then SPLIT → 25€ coins."""
    img = background(t)
    draw = ImageDraw.Draw(img)
    draw_centered(draw, "1 + 1", 360, 84, GOLD + (255,))
    meet = min(local / 1.1, 1.0)
    x1 = 300 + math.sin(local * 2) * 6
    x2 = 260 + meet * 400
    if local < 1.35:
        number_walker(draw, x1, 1180, "1", local, 0.0)
        number_walker(draw, x2, 1180, "1", local, 1.4)
        if meet > 0.85:
            draw_centered(draw, "παρέα!", 500, 44, WHITE + (220,))
    # SPLIT + money after they meet
    if local >= 1.2:
        split_local = local - 1.2
        split_badge(draw, 560, split_local)
        pop = ease(min(split_local / 0.35, 1.0))
        money_coin(draw, W / 2 - 160, 1100, "25€", local, 0.0, pop)
        money_coin(draw, W / 2 + 160, 1100, "25€", local, 1.0, pop)
        draw_centered(draw, "ο καθένας", 1280, 34, SOFT + (int(210 * pop),), FONT_REG)
    return img


def scene_trio(t: float, local: float) -> Image.Image:
    """Third joins, then SPLIT → 20€ coins."""
    img = background(t)
    draw = ImageDraw.Draw(img)
    draw_centered(draw, "1 + 2", 360, 84, GOLD + (255,))
    join = min(local / 0.9, 1.0)
    x3 = 180 + join * 360
    if local < 1.15:
        number_walker(draw, W / 2 - 200, 1180, "1", local, 0.0, 0.95)
        number_walker(draw, W / 2, 1180, "1", local, 1.1, 0.95)
        number_walker(draw, x3 + 180, 1180, "1", local, 2.0, 0.95)
        if join > 0.8:
            draw_centered(draw, "και τρίτος!", 500, 42, WHITE + (220,))
    if local >= 1.0:
        split_local = local - 1.0
        split_badge(draw, 540, split_local)
        pop = ease(min(split_local / 0.35, 1.0))
        for i, ox in enumerate((-220, 0, 220)):
            money_coin(draw, W / 2 + ox, 1080, "20€", local, i * 0.7, pop)
        draw_centered(draw, "ο καθένας — πιο ελαφριά!", 1280, 32, SOFT + (int(210 * pop),), FONT_REG)
    return img


def scene_punch(t: float, local: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    fade = ease(min(local / 0.32, 1.0))
    a = int(255 * fade)
    lines = [
        ("Εμείς σου βρίσκουμε την παρέα", WHITE, 42),
        ("εσύ σπλιτάρεις την τιμή", GOLD, 48),
    ]
    y = H / 2 - 100
    for text, color, size in lines:
        f = ImageFont.truetype(FONT, size)
        while draw.textlength(text, font=f) > 940 and size > 26:
            size -= 2
            f = ImageFont.truetype(FONT, size)
        tw = draw.textlength(text, font=f)
        draw.text(((W - tw) / 2, y), text, font=f, fill=color + (a,))
        y += size + 26
    bar = 260 * fade
    draw.rounded_rectangle(
        (W / 2 - bar / 2, y + 8, W / 2 + bar / 2, y + 15),
        radius=4,
        fill=GOLD + (int(230 * fade),),
    )
    # tiny celebrating coins
    pop = ease(min(max((local - 0.15) / 0.35, 0.0), 1.0))
    money_coin(draw, 200, 1280, "€", local, 0.0, pop)
    money_coin(draw, W - 200, 1280, "€", local, 1.2, pop)
    return img


def scene_cta(t: float, local: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    fade = ease(min(local / 0.35, 1.0))
    a = int(255 * fade)
    draw_centered(draw, "Taxi and Fly Multi", H / 2 - 120, 56, WHITE + (a,))
    draw_centered(draw, "Δοκίμασέ το", H / 2 - 20, 72, GOLD + (a,))
    bar = 280 * fade
    draw.rounded_rectangle(
        (W / 2 - bar / 2, H / 2 + 80, W / 2 + bar / 2, H / 2 + 87),
        radius=4,
        fill=GOLD + (int(230 * fade),),
    )
    pop = ease(min(max((local - 0.2) / 0.4, 0.0), 1.0))
    money_coin(draw, 220, 1280, "€", local, 0.0, pop)
    money_coin(draw, W - 220, 1280, "€", local, 1.5, pop)
    return img


SCENES = {
    "intro": scene_intro,
    "walk1": scene_walk1,
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
    size = int(480 * (0.92 + 0.08 * k))
    mark = mark.resize((size, size), Image.Resampling.LANCZOS)
    img.alpha_composite(mark, ((W - size) // 2, 400))
    fade = ease(min(max((since - 0.1) / 0.4, 0.0), 1.0))
    f_brand = ImageFont.truetype(FONT, 64)
    f_cta = ImageFont.truetype(FONT, 52)
    f_url = ImageFont.truetype(FONT_REG, 26)
    for text, font, y, color in (
        ("Taxi and Fly Multi", f_brand, 960, GOLD),
        ("Δοκίμασέ το", f_cta, 1055, WHITE),
    ):
        tw = draw.textlength(text, font=font)
        draw.text(((W - tw) / 2, y), text, font=font, fill=color + (int(255 * fade),))
    uw = draw.textlength(APP_URL, font=f_url)
    draw.text(((W - uw) / 2, 1160), APP_URL, font=f_url, fill=SOFT + (int(220 * fade),))
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
        "[0:a]volume=0.17,afade=t=in:st=0:d=0.45,"
        f"afade=t=out:st={max(total - 1.2, 0.4):.2f}:d=1.0,"
        "aformat=sample_rates=44100:channel_layouts=stereo[m];"
        "[1:a]volume=0.40,aformat=sample_rates=44100:channel_layouts=stereo[s];"
        "[2:a]highpass=f=90,equalizer=f=220:t=q:w=1:g=1.15,equalizer=f=2800:t=q:w=1:g=1.05,"
        "acompressor=threshold=-18dB:ratio=1.5:attack=10:release=100,"
        "aformat=sample_rates=44100:channel_layouts=stereo,volume=1.12,"
        "apad=pad_dur=0.7[v];"
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
        pad = work / f"line_{i}_pad.wav"
        ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{hold:.3f}", str(pad))
        d = duration(wav) + hold
        scene_durs.append(d)
        keys.append(key)
        parts.extend([wav, pad])
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
            base = fn(t, local)
            remaining = seconds - local
            if remaining < xfade and i < len(keys) - 1:
                k = ease(1.0 - remaining / xfade)
                nxt = SCENES[keys[i + 1]](t, 0.0)
                base = blend(base, nxt, k * 0.75)
            elif remaining < xfade and i == len(keys) - 1:
                k = ease(1.0 - remaining / xfade)
                nxt = brand_frame(brand_start, brand_start)
                base = blend(base, nxt, k * 0.65)
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
    logo_sting(vlen + 0.4, brand_start + 0.08, sting)
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
