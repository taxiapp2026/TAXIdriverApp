#!/usr/bin/env python3
"""Four very short brand spots — one tagline each, ending on Taxi and Fly.

Frames are drawn one by one so the words land on the voice instead of just
sliding a still around.
"""

from __future__ import annotations

import asyncio
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
ART = Path("/opt/cursor/artifacts")

sys.path.insert(0, str(ROOT))
from add_pretty_music import pretty_music  # noqa: E402
from build_video import FONT, FONT_REG, duration, ff, mix  # noqa: E402
from rebuild_brand_process import icon_lettering  # noqa: E402
from spot_audio import logo_sting, plain_music, reggae_music  # noqa: E402

W, H, FPS = 1080, 1920, 30
GOLD = (255, 210, 40)
WHITE = (242, 242, 242)
GREY = (168, 168, 168)
BG = (8, 8, 8, 255)
APP_URL = "taxiapp2026.github.io/taxi-client-app"

VOICE = "el-GR-NestorasNeural"
RATE = "-8%"
TICKS = 10_000_000.0

SPOTS = [
    {
        "slug": "pata-kleise-peta",
        "el": "Πάτα. Κλείσε. Πέτα.",
        "en": "Tap. Book. Fly.",
    },
    {
        "slug": "porta-pyli",
        "el": "Από την πόρτα σου μέχρι την πύλη σου",
        "en": "From your door to your gate",
    },
    {
        "slug": "xoris-agxos",
        "el": "Χωρίς εγγραφή. Χωρίς άγχος.",
        "en": "No sign-up. No stress.",
    },
    {
        "slug": "ptisi-porta",
        "el": "Η πτήση σου ξεκινάει από την πόρτα σου",
        "en": "Your flight starts at your front door",
    },
    {
        "slug": "gigantas-diamanti",
        "el": "Μην ψάχνεις τον γίγαντα.\nΒρες το διαμάντι.",
        "spoken": "Μην ψάχνεις τον γίγαντα. Βρες το διαμάντι.",
        "en": "Don't chase the giant. Find the diamond.",
        # Different bed under the VO than the logo sting (keep sting the same).
        "speech_bed": "reggae",
    },
    {
        "slug": "odigoi-taxi",
        "el": "Επαγγελματίες πιστοποιημένοι\nοδηγοί ταξί.\nΣε συνδέουμε μαζί τους.",
        "spoken": "Επαγγελματίες πιστοποιημένοι οδηγοί ταξί. Σε συνδέουμε μαζί τους.",
        "en": "Certified taxi drivers. We connect you.",
        "speech_bed": "reggae",
    },
]


def glow_layer() -> Image.Image:
    """Soft gold halo behind everything, so the black never looks flat."""
    h = H + 160
    yy, xx = np.mgrid[0:h, 0:W]
    d = np.sqrt(((xx - W / 2) / 620.0) ** 2 + ((yy - h / 2) / 760.0) ** 2)
    a = np.clip(1.0 - d, 0.0, 1.0) ** 2.4 * 78.0
    rgba = np.zeros((h, W, 4), dtype=np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = GOLD
    rgba[..., 3] = a.astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


GLOW = glow_layer()
BADGE_SRC: Image.Image | None = None


def badge_image() -> Image.Image:
    global BADGE_SRC
    if BADGE_SRC is None:
        size = 620
        mark = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(mark)
        draw.ellipse((14, 14, size - 14, size - 14), outline=GOLD + (255,), width=18)
        letters = icon_lettering()
        inner = int(size * 0.60)
        scale = min(inner / letters.width, inner / letters.height)
        letters = letters.resize(
            (max(1, int(letters.width * scale)), max(1, int(letters.height * scale))),
            Image.Resampling.LANCZOS,
        )
        mark.alpha_composite(letters, ((size - letters.width) // 2, (size - letters.height) // 2))
        BADGE_SRC = mark
    return BADGE_SRC


def layout_words(draw: ImageDraw.ImageDraw, text: str, font, max_w: int, line_h: int):
    """Place every word, so each one can fade in on its own."""
    lines: list[list[str]] = []
    # Honor explicit newlines so short punch lines land as written.
    for raw_line in text.split("\n"):
        cur: list[str] = []
        for word in raw_line.split():
            trial = " ".join(cur + [word])
            if draw.textlength(trial, font=font) <= max_w or not cur:
                cur.append(word)
            else:
                lines.append(cur)
                cur = [word]
        if cur:
            lines.append(cur)

    placed = []
    idx = 0
    for row, words in enumerate(lines):
        line_w = draw.textlength(" ".join(words), font=font)
        x = (W - line_w) / 2
        for word in words:
            placed.append({"text": word, "x": x, "y": row * line_h, "i": idx})
            x += draw.textlength(word + " ", font=font)
            idx += 1
    return placed, len(lines) * line_h


def background(t: float) -> Image.Image:
    base = Image.new("RGBA", (W, H), BG)
    drift = int(26 * math.sin(t * 0.55))
    base.alpha_composite(GLOW, (0, -80 + drift))
    return base


def wrap_centered(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for word in words:
        trial = " ".join(cur + [word])
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur.append(word)
        else:
            lines.append(" ".join(cur))
            cur = [word]
    if cur:
        lines.append(" ".join(cur))
    return lines or [text]


def tagline_frame(t: float, cfg: dict) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    f_el = cfg["f_el"]
    f_en = cfg["f_en"]
    placed = cfg["placed"]
    block_h = cfg["block_h"]
    # Keep the block centered with room above so the rise-in never feels clipped.
    top = 920 - block_h / 2

    last_word_end = cfg["word_times"][-1] + 0.35
    for item in placed:
        start = cfg["word_times"][min(item["i"], len(cfg["word_times"]) - 1)]
        k = max(0.0, min((t - start) / 0.32, 1.0))
        if k <= 0:
            continue
        ease = 1 - (1 - k) ** 3
        y = top + item["y"] + (1 - ease) * 36
        draw.text((item["x"], y), item["text"], font=f_el, fill=WHITE + (int(255 * ease),))

    bar_k = max(0.0, min((t - cfg["word_times"][0]) / max(last_word_end - cfg["word_times"][0], 0.4), 1.0))
    bar_w = 260 * bar_k
    bar_y = top + block_h + 46
    if bar_w > 2:
        draw.rounded_rectangle(
            (W / 2 - bar_w / 2, bar_y, W / 2 + bar_w / 2, bar_y + 7), radius=4, fill=GOLD + (230,)
        )

    en_k = max(0.0, min((t - cfg["en_at"]) / 0.4, 1.0))
    if en_k > 0:
        en_lines = wrap_centered(draw, cfg["en"], f_en, 900)
        for i, line in enumerate(en_lines):
            en_w = draw.textlength(line, font=f_en)
            draw.text(
                ((W - en_w) / 2, bar_y + 46 + i * 48 + (1 - en_k) * 14),
                line,
                font=f_en,
                fill=GREY + (int(235 * en_k),),
            )
    return img


def brand_frame(t: float, switch: float, cfg: dict) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    since = max(t - switch, 0.0)
    grow = 1 - (1 - min(since / 0.7, 1.0)) ** 3
    scale = 0.90 + 0.10 * grow + 0.016 * min(since, 3.0)
    mark = badge_image()
    size = int(mark.width * scale)
    mark = mark.resize((size, size), Image.Resampling.LANCZOS)
    img.alpha_composite(mark, ((W - size) // 2, 620 - size // 2))

    f_brand = cfg["f_brand"]
    f_url = cfg["f_url"]
    rise = (1 - grow) * 18
    bw = draw.textlength("Taxi and Fly", font=f_brand)
    draw.text(((W - bw) / 2, 1080 + rise), "Taxi and Fly", font=f_brand, fill=GOLD + (255,))
    uw = draw.textlength(APP_URL, font=f_url)
    fade = min(max((since - 0.35) / 0.5, 0.0), 1.0)
    draw.text(((W - uw) / 2, 1230), APP_URL, font=f_url, fill=GREY + (int(230 * fade),))
    return img


async def speak(text: str, dst: Path) -> list[dict]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    last: Exception | None = None
    for attempt in range(8):
        try:
            comm = edge_tts.Communicate(text, VOICE, rate=RATE, pitch="+0Hz", boundary="WordBoundary")
            audio = bytearray()
            marks: list[dict] = []
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    audio.extend(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    marks.append({"t": chunk["offset"] / TICKS, "text": chunk["text"]})
            if len(audio) < 2000:
                raise RuntimeError("empty audio")
            dst.write_bytes(bytes(audio))
            return marks
        except Exception as exc:  # noqa: BLE001
            last = exc
            print("retry", dst.name, exc)
            time.sleep(1.1 + attempt * 0.5)
    raise RuntimeError(last)


def to_wav(src: Path, dst: Path) -> Path:
    ff("-i", str(src), "-ac", "1", "-ar", "44100", str(dst))
    return dst


def lead_silence(path: Path) -> float:
    out = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path), "-af", "silencedetect=noise=-50dB:d=0.05", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    starts = [l for l in out.splitlines() if "silence_start" in l]
    ends = [l for l in out.splitlines() if "silence_end" in l]
    if not starts or not ends or float(starts[0].split("silence_start:")[1]) > 0.02:
        return 0.0
    return float(ends[0].split("silence_end:")[1].split("|")[0])


def trim_edges(src: Path, dst: Path) -> float:
    """Strip the dead air the TTS leaves at both ends; return the lead it cut."""
    lead = lead_silence(src)
    ff(
        "-i", str(src),
        "-af",
        "silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB,"
        "areverse,"
        "silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB,"
        "areverse",
        "-ac", "1", "-ar", "44100", str(dst),
    )
    return lead


GAP = 0.95
TAIL = 1.2
# Empty beat before the first word, so the open isn't clipped on entry.
INTRO = 0.45

VOICE_FX = (
    "highpass=f=80,equalizer=f=160:t=q:w=1:g=1.8,equalizer=f=2600:t=q:w=1:g=1.2,"
    "acompressor=threshold=-18dB:ratio=1.8:attack=15:release=140,"
    "aformat=sample_rates=44100:channel_layouts=stereo,volume=1.18"
)


def mix_voiced(
    vo: Path, bed: Path, sting: Path, total: float, dst: Path, bed_vol: float = 0.15
) -> None:
    ff(
        "-i", str(bed), "-i", str(sting), "-i", str(vo),
        "-filter_complex",
        f"[0:a]volume={bed_vol:.3f},aformat=sample_rates=44100:channel_layouts=stereo[m];"
        "[1:a]volume=0.50,aformat=sample_rates=44100:channel_layouts=stereo[s];"
        f"[2:a]{VOICE_FX}[v];"
        "[m][s][v]amix=inputs=3:duration=longest:dropout_transition=0:normalize=0,"
        "loudnorm=I=-16:TP=-1.5:LRA=11,"
        f"alimiter=limit=0.95,atrim=0:{total:.3f},asetpts=PTS-STARTPTS[a]",
        "-map", "[a]", "-t", f"{total:.3f}",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k", str(dst),
    )


def mix_plain(
    bed: Path, sting: Path, total: float, dst: Path, bed_vol: float = 0.34
) -> None:
    ff(
        "-i", str(bed), "-i", str(sting),
        "-filter_complex",
        f"[0:a]volume={bed_vol:.3f},aformat=sample_rates=44100:channel_layouts=stereo[m];"
        "[1:a]volume=0.55,aformat=sample_rates=44100:channel_layouts=stereo[s];"
        "[m][s]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
        "loudnorm=I=-17:TP=-1.5:LRA=11,"
        f"alimiter=limit=0.95,atrim=0:{total:.3f},asetpts=PTS-STARTPTS[a]",
        "-map", "[a]", "-t", f"{total:.3f}",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k", str(dst),
    )


def encode(silent: Path, audio: Path, out: Path) -> None:
    tmp = silent.with_name(silent.stem + "_" + out.stem + "_tmp.mp4")
    mix(silent, audio, tmp)
    ff(
        "-i", str(tmp),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
        "-preset", "medium", "-crf", "19",
        "-fps_mode", "cfr", "-r", str(FPS),
        "-g", str(FPS * 2), "-keyint_min", str(FPS), "-sc_threshold", "0",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k",
        "-movflags", "+faststart", str(out),
    )
    tmp.unlink(missing_ok=True)


async def build(spot: dict) -> Path:
    slug = spot["slug"]
    spoken = spot.get("spoken") or spot["el"].replace("\n", " ")
    print("TTS", spoken)
    tag_mp3 = BUILD / f"spot_{slug}_tag.mp3"
    marks = await speak(spoken, tag_mp3)
    brand_mp3 = BUILD / f"spot_{slug}_brand.mp3"
    await speak("Taxi and Fly.", brand_mp3)

    lead = trim_edges(tag_mp3, BUILD / f"spot_{slug}_tag.wav")
    tag_wav = BUILD / f"spot_{slug}_tag.wav"
    brand_wav = BUILD / f"spot_{slug}_brand.wav"
    trim_edges(brand_mp3, brand_wav)
    intro = BUILD / f"spot_{slug}_intro.wav"
    pause = BUILD / f"spot_{slug}_pause.wav"
    ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{INTRO:.3f}", str(intro))
    ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{GAP:.3f}", str(pause))
    lst = BUILD / f"spot_{slug}_join.txt"
    lst.write_text(
        "".join(f"file '{p.resolve()}'\n" for p in (intro, tag_wav, pause, brand_wav))
    )
    vo = BUILD / f"spot_{slug}_vo.wav"
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(vo))

    word_times = [max(m["t"] - lead, 0.06) + INTRO for m in marks] or [INTRO + 0.3]
    t1 = duration(tag_wav)
    # Hold the finished line for a beat, then land on the logo with the words.
    switch = INTRO + t1 + 0.8
    total = INTRO + t1 + GAP + duration(brand_wav) + TAIL

    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    # Slightly larger type for short two-beat lines.
    el_size = 82 if "\n" in spot["el"] else 78
    line_h = 112 if "\n" in spot["el"] else 104
    f_el = ImageFont.truetype(FONT, el_size)
    placed, block_h = layout_words(probe, spot["el"], f_el, 920, line_h)
    cfg = {
        "f_el": f_el,
        "f_en": ImageFont.truetype(FONT_REG, 40),
        "f_brand": ImageFont.truetype(FONT, 84),
        "f_url": ImageFont.truetype(FONT_REG, 33),
        "placed": placed,
        "block_h": block_h,
        "line_h": line_h,
        "word_times": word_times,
        "en_at": word_times[min(1, len(word_times) - 1)] + 0.2,
        "en": spot["en"],
    }

    frames = BUILD / f"frames_{slug}"
    shutil.rmtree(frames, ignore_errors=True)
    frames.mkdir(parents=True)
    n = int(round(total * FPS))
    out_d, in_d = 0.22, 0.30
    brand_at = switch + out_d
    for i in range(n):
        t = i / FPS
        # Dip through the background instead of cross-dissolving the two layers,
        # otherwise the tagline ghosts behind the logo.
        k_out = max(0.0, min((t - switch) / out_d, 1.0))
        k_in = max(0.0, min((t - brand_at) / in_d, 1.0))
        if k_out >= 1 and k_in >= 1:
            img = brand_frame(t, brand_at, cfg)
        elif k_out <= 0:
            img = tagline_frame(t, cfg)
        else:
            img = background(t)
            if k_out < 1:
                img = Image.blend(img, tagline_frame(t, cfg), 1 - k_out)
            if k_in > 0:
                img = Image.blend(img, brand_frame(t, brand_at, cfg), k_in)
        img.convert("RGB").save(frames / f"{i:05d}.png")

    silent = BUILD / f"spot_{slug}_silent.mp4"
    ff(
        "-framerate", str(FPS), "-i", str(frames / "%05d.png"),
        "-vf", "format=yuv420p,setsar=1",
        "-fps_mode", "cfr", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-profile:v", "high", "-level", "4.0",
        "-g", str(FPS * 2), "-keyint_min", str(FPS), "-sc_threshold", "0",
        "-an", str(silent),
    )

    vlen = duration(silent)
    total_a = vlen + 0.05
    sting = BUILD / f"spot_{slug}_sting.wav"
    logo_sting(vlen + 0.4, brand_at + 0.12, sting)

    voiced_bed = BUILD / f"spot_{slug}_bed.wav"
    bed_kind = spot.get("speech_bed", "pretty")
    if bed_kind == "reggae":
        # Punchier groove under the line — not the soft pad, not the logo bell.
        reggae_music(vlen + 0.4, voiced_bed)
        bed_vol = 0.22
    else:
        pretty_music(vlen + 0.4, voiced_bed)
        bed_vol = 0.15
    voiced_a = BUILD / f"spot_{slug}_mix.m4a"
    mix_voiced(vo, voiced_bed, sting, total_a, voiced_a, bed_vol=bed_vol)
    out = ROOT / f"taxi-and-fly-spot-{slug}.mp4"
    encode(silent, voiced_a, out)

    plain_bed = BUILD / f"spot_{slug}_plainbed.wav"
    if bed_kind == "reggae":
        reggae_music(vlen + 0.4, plain_bed)
        plain_vol = 0.42
    else:
        plain_music(vlen + 0.4, plain_bed)
        plain_vol = 0.34
    plain_a = BUILD / f"spot_{slug}_plain.m4a"
    mix_plain(plain_bed, sting, total_a, plain_a, bed_vol=plain_vol)
    out_plain = ROOT / f"taxi-and-fly-spot-{slug}-mousiki.mp4"
    encode(silent, plain_a, out_plain)

    shutil.rmtree(frames, ignore_errors=True)
    ART.mkdir(parents=True, exist_ok=True)
    stem = slug.replace("-", "_")
    (ART / f"taxi_and_fly_spot_{stem}.mp4").write_bytes(out.read_bytes())
    (ART / f"taxi_and_fly_spot_{stem}_mousiki.mp4").write_bytes(out_plain.read_bytes())
    print("Wrote", out.name, "and", out_plain.name, round(duration(out), 2), "s")
    return out


async def main(argv: list[str] | None = None) -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    args = list(sys.argv[1:] if argv is None else argv)
    wanted = set(args)
    spots = [s for s in SPOTS if not wanted or s["slug"] in wanted]
    if not spots:
        print("No matching spots. Known:", ", ".join(s["slug"] for s in SPOTS))
        return 1
    for spot in spots:
        await build(spot)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
