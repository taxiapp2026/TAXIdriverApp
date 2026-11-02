#!/usr/bin/env python3
"""Taxi and Fly Multi — split with numbers: 1→50, 1+1→25, 1+2→20 + SPLIT.

VO says Μούλτι / σπλιτάρουμε; on-screen Multi / SPLIT.
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
BG = (8, 8, 8, 255)
APP_URL = "taxiapp2026.github.io/taxi-client-app"
VOICE = "el-GR-NestorasNeural"
RATE = "+5%"
BRAND_TAIL = 1.0

# scene_key drives visuals; spoken uses Μούλτι; SPLIT is on-screen English
BEATS = [
    ("brand", "Taxi and Fly Μούλτι.", 0.15),
    ("alone", "Πενήντα.", 0.10),
    ("two", "Ένα συν ένα, είκοσι πέντε.", 0.10),
    ("three", "Ένα συν δύο, είκοσι.", 0.15),
    ("punch", "Εμείς την παρέα, εσύ σπλιτάρεις την τιμή.", 0.70),
]


def ease(k: float) -> float:
    k = max(0.0, min(k, 1.0))
    return 1 - (1 - k) ** 3


def glow_layer() -> Image.Image:
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / 540.0) ** 2 + ((yy - H * 0.42) / 720.0) ** 2)
    a = np.clip(1.0 - d, 0.0, 1.0) ** 2.2 * 95.0
    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = GOLD
    rgba[..., 3] = a.astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


GLOW = glow_layer()
BADGE: Image.Image | None = None


def badge_image() -> Image.Image:
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
    return BADGE


def background(t: float) -> Image.Image:
    img = Image.new("RGBA", (W, H), BG)
    drift = int(14 * math.sin(t * 0.4))
    img.alpha_composite(GLOW, (0, drift))
    return img


def person_dot(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float = 36) -> None:
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=GOLD + (255,), width=6)
    draw.ellipse((cx - r * 0.35, cy - r * 0.55, cx + r * 0.35, cy - r * 0.05), fill=GOLD + (255,))
    draw.arc((cx - r * 0.7, cy - r * 0.1, cx + r * 0.7, cy + r * 0.85), 10, 170, fill=GOLD + (255,), width=5)


def draw_centered(draw: ImageDraw.ImageDraw, text: str, y: float, size: int, fill, font_path=FONT) -> float:
    f = ImageFont.truetype(font_path, size)
    while draw.textlength(text, font=f) > 960 and size > 28:
        size -= 2
        f = ImageFont.truetype(font_path, size)
    tw = draw.textlength(text, font=f)
    draw.text(((W - tw) / 2, y), text, font=f, fill=fill)
    return size


def scene_brand(t: float, local: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    fade = ease(min(local / 0.35, 1.0))
    a = int(255 * fade)
    draw_centered(draw, "Taxi and Fly Multi", H / 2 - 80, 58, WHITE + (a,))
    bar = 220 * fade
    draw.rounded_rectangle(
        (W / 2 - bar / 2, H / 2 + 20, W / 2 + bar / 2, H / 2 + 27),
        radius=4,
        fill=GOLD + (int(230 * fade),),
    )
    return img


def scene_alone(t: float, local: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    fade = ease(min(local / 0.3, 1.0))
    a = int(255 * fade)
    draw_centered(draw, "1", 420, 120, GOLD + (a,))
    person_dot(draw, W / 2, 720)
    # price pops
    pop = ease(min(max((local - 0.25) / 0.35, 0.0), 1.0))
    draw_centered(draw, "50€", 980 + (1 - pop) * 30, 140, WHITE + (int(255 * pop),))
    draw_centered(draw, "μόνος", 1180, 40, SOFT + (int(200 * pop),), FONT_REG)
    return img


def scene_two(t: float, local: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    fade = ease(min(local / 0.28, 1.0))
    a = int(255 * fade)
    draw_centered(draw, "1 + 1", 360, 100, GOLD + (a,))
    person_dot(draw, W / 2 - 110, 620)
    person_dot(draw, W / 2 + 110, 620)
    # SPLIT badge
    split_a = ease(min(max((local - 0.15) / 0.3, 0.0), 1.0))
    f = ImageFont.truetype(FONT, 72)
    tw = draw.textlength("SPLIT", font=f)
    pad_x, pad_y = 36, 14
    box = (W / 2 - tw / 2 - pad_x, 780, W / 2 + tw / 2 + pad_x, 780 + 72 + pad_y * 2)
    draw.rounded_rectangle(box, radius=20, outline=GOLD + (int(255 * split_a),), width=6)
    draw.text(((W - tw) / 2, 780 + pad_y), "SPLIT", font=f, fill=GOLD + (int(255 * split_a),))
    pop = ease(min(max((local - 0.35) / 0.35, 0.0), 1.0))
    draw_centered(draw, "25€", 1020 + (1 - pop) * 24, 130, WHITE + (int(255 * pop),))
    draw_centered(draw, "ο καθένας", 1200, 38, SOFT + (int(200 * pop),), FONT_REG)
    return img


def scene_three(t: float, local: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    fade = ease(min(local / 0.28, 1.0))
    a = int(255 * fade)
    draw_centered(draw, "1 + 2", 360, 100, GOLD + (a,))
    person_dot(draw, W / 2 - 160, 620, r=32)
    person_dot(draw, W / 2, 620, r=32)
    person_dot(draw, W / 2 + 160, 620, r=32)
    split_a = ease(min(max((local - 0.12) / 0.3, 0.0), 1.0))
    f = ImageFont.truetype(FONT, 72)
    tw = draw.textlength("SPLIT", font=f)
    pad_x, pad_y = 36, 14
    box = (W / 2 - tw / 2 - pad_x, 780, W / 2 + tw / 2 + pad_x, 780 + 72 + pad_y * 2)
    draw.rounded_rectangle(box, radius=20, outline=GOLD + (int(255 * split_a),), width=6)
    draw.text(((W - tw) / 2, 780 + pad_y), "SPLIT", font=f, fill=GOLD + (int(255 * split_a),))
    pop = ease(min(max((local - 0.3) / 0.35, 0.0), 1.0))
    draw_centered(draw, "20€", 1020 + (1 - pop) * 24, 130, WHITE + (int(255 * pop),))
    draw_centered(draw, "ο καθένας", 1200, 38, SOFT + (int(200 * pop),), FONT_REG)
    return img


def scene_punch(t: float, local: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    fade = ease(min(local / 0.35, 1.0))
    a = int(255 * fade)
    lines = [
        ("Εμείς σου βρίσκουμε την παρέα", WHITE, 44),
        ("εσύ σπλιτάρεις την τιμή", GOLD, 52),
    ]
    y = H / 2 - 90
    for text, color, size in lines:
        f = ImageFont.truetype(FONT, size)
        while draw.textlength(text, font=f) > 940 and size > 28:
            size -= 2
            f = ImageFont.truetype(FONT, size)
        tw = draw.textlength(text, font=f)
        draw.text(((W - tw) / 2, y), text, font=f, fill=color + (a,))
        y += size + 28
    bar = 260 * fade
    draw.rounded_rectangle(
        (W / 2 - bar / 2, y + 10, W / 2 + bar / 2, y + 17),
        radius=4,
        fill=GOLD + (int(230 * fade),),
    )
    return img


SCENES = {
    "brand": scene_brand,
    "alone": scene_alone,
    "two": scene_two,
    "three": scene_three,
    "punch": scene_punch,
}


def brand_frame(t: float, start: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    since = max(t - start, 0.0)
    k = ease(min(since / 0.55, 1.0))
    mark = badge_image()
    size = int(500 * (0.92 + 0.08 * k))
    mark = mark.resize((size, size), Image.Resampling.LANCZOS)
    img.alpha_composite(mark, ((W - size) // 2, 420))
    f_brand = ImageFont.truetype(FONT, 70)
    f_line = ImageFont.truetype(FONT_REG, 36)
    f_url = ImageFont.truetype(FONT_REG, 26)
    fade = ease(min(max((since - 0.12) / 0.4, 0.0), 1.0))
    bw = draw.textlength("Taxi and Fly", font=f_brand)
    draw.text(((W - bw) / 2, 980), "Taxi and Fly", font=f_brand, fill=GOLD + (255,))
    line = "Από και προς το αεροδρόμιο"
    tw = draw.textlength(line, font=f_line)
    draw.text(((W - tw) / 2, 1085), line, font=f_line, fill=WHITE + (int(245 * fade),))
    uw = draw.textlength(APP_URL, font=f_url)
    draw.text(((W - uw) / 2, 1175), APP_URL, font=f_url, fill=SOFT + (int(220 * fade),))
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
        "[0:a]volume=0.16,afade=t=in:st=0:d=0.5,"
        f"afade=t=out:st={max(total - 1.3, 0.4):.2f}:d=1.1,"
        "aformat=sample_rates=44100:channel_layouts=stereo[m];"
        "[1:a]volume=0.38,aformat=sample_rates=44100:channel_layouts=stereo[s];"
        "[2:a]highpass=f=90,equalizer=f=220:t=q:w=1:g=1.15,equalizer=f=2800:t=q:w=1:g=1.05,"
        "acompressor=threshold=-18dB:ratio=1.5:attack=10:release=100,"
        "aformat=sample_rates=44100:channel_layouts=stereo,volume=1.12,"
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
    xfade = 0.32
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
                base = blend(base, nxt, k * 0.8)
            elif remaining < xfade and i == len(keys) - 1:
                k = ease(1.0 - remaining / xfade)
                nxt = brand_frame(brand_start, brand_start)
                base = blend(base, nxt, k * 0.7)
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
