#!/usr/bin/env python3
"""Two Taxi and Fly Multi text spots — one per tagline, continuous flow.

1) Εσύ τον προορισμό, εμείς την παρέα
2) Εσύ έχεις την πτήση, εμείς φτιάχνουμε την παρέα
No prices/logistics. Hope music + natural VO.
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
BUILD = ROOT / "build" / "parea"
ART = Path("/opt/cursor/artifacts")

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
RATE = "-4%"

SPOTS = {
    "proorismo": {
        "out": ROOT / "taxi-and-fly-multi-proorismo.mp4",
        "art": "taxi-and-fly-multi-proorismo.mp4",
        # On-screen: Multi | Spoken: Μούλτι (Greek pronunciation)
        "beats": [
            ("Taxi and Fly Μούλτι.", ["Taxi and Fly Multi"], 0.25),
            ("Εσύ τον προορισμό,", ["Taxi and Fly Multi", "Εσύ τον προορισμό"], 0.20),
            ("εμείς την παρέα.", ["Taxi and Fly Multi", "Εσύ τον προορισμό", "εμείς την παρέα"], 1.10),
        ],
        "brand_tail": 1.5,
    },
    "ptisi": {
        "out": ROOT / "taxi-and-fly-multi-ptisi.mp4",
        "art": "taxi-and-fly-multi-ptisi.mp4",
        "beats": [
            ("Taxi and Fly Μούλτι.", ["Taxi and Fly Multi"], 0.25),
            ("Εσύ έχεις την πτήση,", ["Taxi and Fly Multi", "Εσύ έχεις την πτήση"], 0.20),
            ("εμείς φτιάχνουμε την παρέα.", ["Taxi and Fly Multi", "Εσύ έχεις την πτήση", "εμείς φτιάχνουμε την παρέα"], 1.10),
        ],
        "brand_tail": 1.5,
    },
    "split": {
        "out": ROOT / "taxi-and-fly-multi-split.mp4",
        "art": "taxi-and-fly-multi-split.mp4",
        "beats": [
            ("Taxi and Fly Μούλτι.", ["Taxi and Fly Multi"], 0.25),
            ("Εμείς σου βρίσκουμε την παρέα,", ["Taxi and Fly Multi", "Εμείς σου βρίσκουμε την παρέα"], 0.20),
            ("εσύ σπλιτάρεις την τιμή.", ["Taxi and Fly Multi", "Εμείς σου βρίσκουμε την παρέα", "εσύ σπλιτάρεις την τιμή"], 1.10),
        ],
        "brand_tail": 1.5,
    },
}


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


def story_frame(
    t: float, local: float, visible: list[str], newest: int, n_beats: int
) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    for i in range(n_beats):
        cx = W / 2 - (n_beats - 1) * 16 + i * 32
        r = 6 if i == newest else 3
        fill = GOLD if i <= newest else (70, 70, 70)
        draw.ellipse((cx - r, 150 - r, cx + r, 150 + r), fill=fill + (255,))

    sized: list[tuple[ImageFont.FreeTypeFont, str, tuple[int, int, int], float]] = []
    for i, ln in enumerate(visible):
        is_punch = i == len(visible) - 1 and newest == n_beats - 1
        is_new = i == len(visible) - 1
        size = 64 if is_punch else (48 if i == 0 else 44)
        f = ImageFont.truetype(FONT, size)
        while draw.textlength(ln, font=f) > 940 and size > 26:
            size -= 2
            f = ImageFont.truetype(FONT, size)
        color = GOLD if is_punch else WHITE
        alpha = ease(min(local / 0.32, 1.0)) if is_new else 1.0
        sized.append((f, ln, color, alpha))

    line_gap = 20
    heights = [int(getattr(f, "size", 48) + line_gap) for f, *_ in sized]
    block_h = sum(heights)
    rise = (1 - sized[-1][3]) * 16 if sized else 0
    top = H / 2 - block_h / 2 - 20 + rise
    y = top
    for (f, ln, color, alpha), h in zip(sized, heights):
        tw = draw.textlength(ln, font=f)
        draw.text(((W - tw) / 2, y), ln, font=f, fill=color + (int(255 * alpha),))
        y += h

    if newest == n_beats - 1 and sized:
        fade = sized[-1][3]
        bar_w = 280 * fade
        if bar_w > 2:
            draw.rounded_rectangle(
                (W / 2 - bar_w / 2, y + 8, W / 2 + bar_w / 2, y + 15),
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


async def build_one(slug: str, cfg: dict) -> Path:
    work = BUILD / slug
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    beats = cfg["beats"]
    n_beats = len(beats)

    parts: list[Path] = []
    scene_durs: list[float] = []
    for i, (spoken, _vis, hold) in enumerate(beats):
        mp3 = work / f"line_{i}.mp3"
        wav = work / f"line_{i}.wav"
        await speak(spoken, mp3)
        ff("-i", str(mp3), "-ac", "1", "-ar", "44100", str(wav))
        pad = work / f"line_{i}_pad.wav"
        ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{hold:.3f}", str(pad))
        d = duration(wav) + hold
        scene_durs.append(d)
        parts.extend([wav, pad])
        print(f"[{slug}] {i}: «{spoken}» {d:.2f}s")

    brand_tail = cfg["brand_tail"]
    brand_pad = work / "brand_pad.wav"
    ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{brand_tail:.3f}", str(brand_pad))
    parts.append(brand_pad)

    lst = work / "vo_join.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    vo_wav = work / "vo.wav"
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(vo_wav))

    story_dur = sum(scene_durs)
    brand_start = story_dur
    total = story_dur + brand_tail
    print(f"[{slug}] total {total:.2f}s")

    frames = work / "frames"
    frames.mkdir(parents=True)
    idx = 0
    xfade = 0.36
    for i, seconds in enumerate(scene_durs):
        n = int(round(seconds * FPS))
        for j in range(n):
            local = j / FPS
            t = idx / FPS
            visible = beats[i][1]
            base = story_frame(t, local, visible, i, n_beats)
            remaining = seconds - local
            if remaining < xfade and i < n_beats - 1:
                k = ease(1.0 - remaining / xfade)
                nxt = story_frame(t, 0.0, beats[i + 1][1], i + 1, n_beats)
                base = blend(base, nxt, k * 0.85)
            elif remaining < xfade and i == n_beats - 1:
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

    out = cfg["out"]
    tmp = work / "tmp.mp4"
    mix(silent, audio, tmp)
    ff(
        "-i", str(tmp),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high",
        "-preset", "medium", "-crf", "17",
        "-fps_mode", "cfr", "-r", str(FPS),
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
        "-movflags", "+faststart", str(out),
    )

    ART.mkdir(parents=True, exist_ok=True)
    (ART / "downloads").mkdir(parents=True, exist_ok=True)
    data = out.read_bytes()
    (ART / cfg["art"]).write_bytes(data)
    (ART / "downloads" / cfg["art"]).write_bytes(data)
    shutil.rmtree(frames, ignore_errors=True)
    print("Wrote", out.name, round(duration(out), 2), "s")
    return out


async def main() -> None:
    only = sys.argv[1:] if len(sys.argv) > 1 else list(SPOTS)
    for slug in only:
        if slug not in SPOTS:
            raise SystemExit(f"unknown spot: {slug}")
        await build_one(slug, SPOTS[slug])


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()) and 0)
