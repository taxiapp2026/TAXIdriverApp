#!/usr/bin/env python3
"""15s text spot: Taxi and Fly — Η δύναμη είσαι εσύ.

Serious black/gold typography + natural VO + hope music. No cartoons.
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
BUILD = ROOT / "build" / "dynami"
ART = Path("/opt/cursor/artifacts")
OUT = ROOT / "taxi-and-fly-text-dynami.mp4"

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
RATE = "-6%"

# ~15s story: brand → meaning → punch → end card
LINES = [
    "Taxi and Fly",
    "Για κάθε διαδρομή σου",
    "Η δύναμη είσαι εσύ",
]
# Pause after each line (shorter after brand, longer on punch)
HOLDS = [0.85, 0.75, 1.35]


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
    drift = int(18 * math.sin(t * 0.45))
    img.alpha_composite(GLOW, (0, drift))
    return img


def fit_block(draw: ImageDraw.ImageDraw, text: str, max_w: float = 920, start: int = 64):
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()] or [text]
    for size in range(start, 28, -2):
        f = ImageFont.truetype(FONT, size)
        if all(draw.textlength(ln, font=f) <= max_w for ln in lines):
            return f, lines, int(size + 16)
    f = ImageFont.truetype(FONT, 28)
    return f, lines, 42


def text_frame(t: float, local: float, line: str, index: int) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    total = len(LINES)
    for i in range(total):
        cx = W / 2 - (total - 1) * 16 + i * 32
        r = 6 if i == index else 3
        fill = GOLD if i <= index else (70, 70, 70)
        draw.ellipse((cx - r, 160 - r, cx + r, 160 + r), fill=fill + (255,))

    fade = ease(min(local / 0.35, 1.0))
    rise = (1 - fade) * 22
    # Punch line a bit larger
    start_size = 72 if index == 2 else 58
    f, lines, line_h = fit_block(draw, line, start=start_size)
    block_h = len(lines) * line_h
    top = H / 2 - block_h / 2 - 40 + rise
    color = GOLD if index == 2 else WHITE
    for i, ln in enumerate(lines):
        tw = draw.textlength(ln, font=f)
        draw.text(((W - tw) / 2, top + i * line_h), ln, font=f, fill=color + (int(255 * fade),))
    bar_w = (280 if index == 2 else 200) * fade
    bar_y = top + block_h + 40
    if bar_w > 2:
        draw.rounded_rectangle(
            (W / 2 - bar_w / 2, bar_y, W / 2 + bar_w / 2, bar_y + 7),
            radius=4,
            fill=GOLD + (int(230 * fade),),
        )
    return img


def brand_frame(t: float, start: float) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    since = max(t - start, 0.0)
    k = ease(min(since / 0.5, 1.0))
    mark = badge_image()
    size = int(520 * (0.92 + 0.08 * k))
    mark = mark.resize((size, size), Image.Resampling.LANCZOS)
    img.alpha_composite(mark, ((W - size) // 2, 400))

    f_brand = ImageFont.truetype(FONT, 72)
    f_line = ImageFont.truetype(FONT_REG, 38)
    f_url = ImageFont.truetype(FONT_REG, 26)
    fade = ease(min(max((since - 0.15) / 0.4, 0.0), 1.0))
    bw = draw.textlength("Taxi and Fly", font=f_brand)
    draw.text(((W - bw) / 2, 980), "Taxi and Fly", font=f_brand, fill=GOLD + (255,))
    line = "Από και προς το αεροδρόμιο"
    tw = draw.textlength(line, font=f_line)
    draw.text(((W - tw) / 2, 1090), line, font=f_line, fill=WHITE + (int(245 * fade),))
    uw = draw.textlength(APP_URL, font=f_url)
    draw.text(((W - uw) / 2, 1185), APP_URL, font=f_url, fill=SOFT + (int(220 * fade),))
    return img


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
        "[0:a]volume=0.17,afade=t=in:st=0:d=0.4,"
        f"afade=t=out:st={max(total - 1.2, 0.4):.2f}:d=1.0,"
        "aformat=sample_rates=44100:channel_layouts=stereo[m];"
        "[1:a]volume=0.40,aformat=sample_rates=44100:channel_layouts=stereo[s];"
        "[2:a]highpass=f=90,equalizer=f=220:t=q:w=1:g=1.2,equalizer=f=2800:t=q:w=1:g=1.1,"
        "acompressor=threshold=-18dB:ratio=1.5:attack=10:release=100,"
        "aformat=sample_rates=44100:channel_layouts=stereo,volume=1.15,"
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
    for i, line in enumerate(LINES):
        mp3 = work / f"line_{i}.mp3"
        wav = work / f"line_{i}.wav"
        spoken = line.replace("\n", " ")
        if not spoken.endswith("."):
            spoken += "."
        await speak(spoken, mp3)
        ff("-i", str(mp3), "-ac", "1", "-ar", "44100", str(wav))
        hold = HOLDS[i] if i < len(HOLDS) else 0.8
        pad = work / f"line_{i}_pad.wav"
        ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{hold:.3f}", str(pad))
        d = duration(wav) + hold
        scene_durs.append(d)
        parts.extend([wav, pad])
        print(f"[dynami] {i}: «{line}» {d:.2f}s")

    brand_mp3 = work / "brand.mp3"
    brand_wav = work / "brand.wav"
    await speak("Από και προς το αεροδρόμιο.", brand_mp3)
    ff("-i", str(brand_mp3), "-ac", "1", "-ar", "44100", str(brand_wav))
    brand_pad = work / "brand_pad.wav"
    # Target ~15.0s total for Google Ads 15s slots
    story_so_far = sum(scene_durs) + duration(brand_wav)
    brand_tail = max(0.9, 15.0 - story_so_far - 0.05)
    ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{brand_tail:.3f}", str(brand_pad))
    brand_dur = duration(brand_wav) + brand_tail
    parts.extend([brand_wav, brand_pad])

    lst = work / "vo_join.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    vo_wav = work / "vo.wav"
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(vo_wav))

    story_dur = sum(scene_durs)
    brand_start = story_dur
    total = story_dur + brand_dur
    print(f"[dynami] total {total:.2f}s")

    frames = work / "frames"
    frames.mkdir(parents=True)
    idx = 0
    for i, (line, seconds) in enumerate(zip(LINES, scene_durs)):
        n = int(round(seconds * FPS))
        for j in range(n):
            img = text_frame(idx / FPS, j / FPS, line, i)
            img.convert("RGB").save(frames / f"{idx:05d}.png")
            idx += 1
    need = int(round(total * FPS))
    while idx < need:
        img = brand_frame(idx / FPS, brand_start)
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
    (ART / "taxi-and-fly-text-dynami.mp4").write_bytes(data)
    (ART / "taxi_and_fly_text_dynami.mp4").write_bytes(data)
    (ART / "downloads" / "dynami.mp4").write_bytes(data)
    shutil.rmtree(frames, ignore_errors=True)
    print("Wrote", OUT.name, round(duration(OUT), 2), "s")
    return OUT


if __name__ == "__main__":
    raise SystemExit(asyncio.run(build()) and 0)
