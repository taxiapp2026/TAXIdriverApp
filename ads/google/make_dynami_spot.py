#!/usr/bin/env python3
"""Driver spot with real flow: Taxi and Fly — Η δύναμη είσαι εσύ.

One continuous thought for drivers. Text builds on screen (no hard card cuts).
Natural VO + hope music. No cartoons.
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
RATE = "-4%"  # natural flow, not rushed chops

# One arc for drivers — spoken continuously, text builds in place
BEATS = [
    # (spoken, lines visible so far, hold after VO)
    ("Οδηγέ ταξί.", ["Οδηγέ ταξί"], 0.25),
    ("Στην Taxi and Fly,", ["Οδηγέ ταξί", "στην Taxi and Fly"], 0.20),
    ("η δύναμη είσαι εσύ.", ["Οδηγέ ταξί", "στην Taxi and Fly", "Η δύναμη είσαι εσύ"], 1.15),
]
BRAND_TAIL = 1.6


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


def story_frame(t: float, local: float, visible: list[str], newest: int) -> Image.Image:
    """All visible lines stay on screen; newest line eases in — continuous flow."""
    img = background(t)
    draw = ImageDraw.Draw(img)

    # progress
    total = len(BEATS)
    for i in range(total):
        cx = W / 2 - (total - 1) * 16 + i * 32
        r = 6 if i == newest else 3
        fill = GOLD if i <= newest else (70, 70, 70)
        draw.ellipse((cx - r, 150 - r, cx + r, 150 + r), fill=fill + (255,))

    # Typography: stacked block, last line gold + larger
    sized: list[tuple[ImageFont.FreeTypeFont, str, tuple[int, int, int], float]] = []
    for i, ln in enumerate(visible):
        is_punch = i == len(visible) - 1 and newest == len(BEATS) - 1
        is_new = i == len(visible) - 1
        size = 70 if is_punch else (52 if i == 0 else 48)
        # shrink if needed
        f = ImageFont.truetype(FONT, size)
        while draw.textlength(ln, font=f) > 940 and size > 30:
            size -= 2
            f = ImageFont.truetype(FONT, size)
        color = GOLD if is_punch else WHITE
        alpha = ease(min(local / 0.32, 1.0)) if is_new else 1.0
        sized.append((f, ln, color, alpha))

    line_gap = 22
    heights = [int(getattr(f, "size", 48) + line_gap) for f, *_ in sized]
    block_h = sum(heights)
    # slight rise only for newest
    rise = (1 - sized[-1][3]) * 18 if sized else 0
    top = H / 2 - block_h / 2 - 20 + rise

    y = top
    for (f, ln, color, alpha), h in zip(sized, heights):
        tw = draw.textlength(ln, font=f)
        draw.text(((W - tw) / 2, y), ln, font=f, fill=color + (int(255 * alpha),))
        y += h

    # gold underline under punch when complete
    if newest == len(BEATS) - 1 and sized:
        fade = sized[-1][3]
        bar_w = 280 * fade
        bar_y = y + 8
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
    for i, (spoken, _visible, hold) in enumerate(BEATS):
        mp3 = work / f"line_{i}.mp3"
        wav = work / f"line_{i}.wav"
        await speak(spoken, mp3)
        ff("-i", str(mp3), "-ac", "1", "-ar", "44100", str(wav))
        pad = work / f"line_{i}_pad.wav"
        ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{hold:.3f}", str(pad))
        d = duration(wav) + hold
        scene_durs.append(d)
        parts.extend([wav, pad])
        print(f"[dynami] {i}: «{spoken}» {d:.2f}s")

    brand_pad = work / "brand_pad.wav"
    ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{BRAND_TAIL:.3f}", str(brand_pad))
    brand_dur = BRAND_TAIL
    parts.append(brand_pad)

    lst = work / "vo_join.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    vo_wav = work / "vo.wav"
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(vo_wav))

    story_dur = sum(scene_durs)
    brand_start = story_dur
    total = story_dur + brand_dur
    print(f"[dynami] total {total:.2f}s")

    # Pre-render scene stills, then crossfade between them for flow
    stills: list[Image.Image] = []
    for i, (_spoken, visible, _hold) in enumerate(BEATS):
        # settle frame (fully visible newest line)
        stills.append(story_frame(sum(scene_durs[: i + 1]), 1.0, visible, i))

    frames = work / "frames"
    frames.mkdir(parents=True)
    idx = 0
    xfade = 0.38  # seconds of soft blend into next beat

    for i, seconds in enumerate(scene_durs):
        n = int(round(seconds * FPS))
        for j in range(n):
            local = j / FPS
            t = idx / FPS
            visible = BEATS[i][1]
            base = story_frame(t, local, visible, i)
            # near end of beat, blend toward next still (or brand)
            remaining = seconds - local
            if remaining < xfade and i < len(stills) - 1:
                k = ease(1.0 - remaining / xfade)
                nxt = story_frame(t, 0.0, BEATS[i + 1][1], i + 1)
                # keep previous lines; newest of next at alpha via blend
                base = blend(base, nxt, k * 0.85)
            elif remaining < xfade and i == len(stills) - 1:
                k = ease(1.0 - remaining / xfade)
                nxt = brand_frame(brand_start, brand_start)
                base = blend(base, nxt, k * 0.7)
            base.convert("RGB").save(frames / f"{idx:05d}.png")
            idx += 1

    need = int(round(total * FPS))
    while idx < need:
        img = brand_frame(idx / FPS, brand_start)
        # soft entry already blended; keep easing badge
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
    (ART / "taxi-and-fly-text-dynami.mp4").write_bytes(data)
    (ART / "taxi_and_fly_text_dynami.mp4").write_bytes(data)
    (ART / "downloads" / "dynami.mp4").write_bytes(data)
    shutil.rmtree(frames, ignore_errors=True)
    print("Wrote", OUT.name, round(duration(OUT), 2), "s")
    return OUT


if __name__ == "__main__":
    raise SystemExit(asyncio.run(build()) and 0)
