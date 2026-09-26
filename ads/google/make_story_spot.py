#!/usr/bin/env python3
"""Longer story spot: a traveller takes a Taxi and Fly to the airport.

Real faces, reggae bed, and the same logo landing as the short spots.
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
STORY = ROOT / "story"
ART = Path("/opt/cursor/artifacts")
OUT = ROOT / "taxi-and-fly-istoria-aerodromio.mp4"

sys.path.insert(0, str(ROOT))
from build_video import FONT, FONT_REG, duration, ff, mix, xfade_concat  # noqa: E402
from make_tagline_spots import VOICE_FX, background, badge_image, speak, trim_edges  # noqa: E402
from spot_audio import logo_sting, reggae_music  # noqa: E402

W, H, FPS = 1080, 1920, 30
GOLD = (255, 210, 40)
WHITE = (245, 245, 245)
GREY = (185, 185, 185)
SHOT = 2.7
FADE = 0.45
END_SEC = 2.7

SHOTS = [
    ("story_01_door.png", "Σήμερα ταξιδεύεις", "Today you travel", "up", 1.10),
    ("story_02_curb.png", "Το ταξί σου είναι ήδη καθ' οδόν", "Your taxi is already on its way", "left", 1.09),
    ("story_03_driver.png", "Ο οδηγός σε περιμένει στην ώρα του", "Your driver is there, on time", "center", 1.12),
    ("story_04_backseat.png", "Κάθεσαι και χαλαρώνεις", "You sit back and relax", "down", 1.10),
    ("story_05_highway.png", "Ο δρόμος για το αεροδρόμιο", "The road to the airport", "left", 1.08),
    ("story_06b_terminal.png", "Φτάνεις με άνεση", "You arrive with time to spare", "center", 1.11),
    ("story_07b_wave.png", "Καλό ταξίδι", "Have a good trip", "up", 1.10),
    ("story_08_walking_in.png", "Χωρίς login. Χωρίς άγχος.", "No login. No stress.", "center", 1.12),
]


def wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    lines: list[str] = []
    cur = ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def caption_png(el: str, en: str, dst: Path) -> None:
    """Transparent overlay: dark gradient foot plus the two lines of copy."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grad_h = 820
    grad = Image.new("RGBA", (1, grad_h))
    grad.putdata([(0, 0, 0, int(228 * (y / grad_h) ** 1.05)) for y in range(grad_h)])
    layer.alpha_composite(grad.resize((W, grad_h), Image.Resampling.BILINEAR), (0, H - grad_h))

    draw = ImageDraw.Draw(layer)
    f_el = ImageFont.truetype(FONT, 62)
    f_en = ImageFont.truetype(FONT_REG, 34)
    lines = wrap(draw, el, f_el, 900)
    y = H - 420 - (len(lines) - 1) * 76
    for line in lines:
        w = draw.textlength(line, font=f_el)
        draw.text(((W - w) / 2, y), line, font=f_el, fill=WHITE + (255,),
                  stroke_width=3, stroke_fill=(0, 0, 0, 190))
        y += 76
    w = draw.textlength(en, font=f_en)
    draw.text(((W - w) / 2, y + 12), en, font=f_en, fill=GREY + (240,),
              stroke_width=2, stroke_fill=(0, 0, 0, 170))

    bar_w = 150
    draw.rounded_rectangle(
        ((W - bar_w) / 2, y + 74, (W + bar_w) / 2, y + 80), radius=3, fill=GOLD + (220,)
    )
    layer.save(dst)


def kenburns(src: Path, dst: Path, seconds: float, zoom_end: float, pan: str) -> None:
    """Upscale with lanczos first — the stills are smaller than the canvas."""
    big = BUILD / f"big_{src.stem}.png"
    if not big.exists():
        Image.open(src).convert("RGB").resize((1620, 2880), Image.Resampling.LANCZOS).save(big)
    frames = int(round(seconds * FPS))
    if pan == "up":
        x_expr, y_expr = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)-on*0.30"
    elif pan == "down":
        x_expr, y_expr = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)+on*0.30"
    elif pan == "left":
        x_expr, y_expr = "iw/2-(iw/zoom/2)-on*0.26", "ih/2-(ih/zoom/2)"
    else:
        x_expr, y_expr = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    z_expr = f"1.02+{zoom_end - 1.02}*on/{frames}"
    vf = (
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={frames}:s={W}x{H}:fps={FPS},"
        f"format=yuv420p,setsar=1"
    )
    ff("-loop", "1", "-i", str(big), "-vf", vf, "-frames:v", str(frames),
       "-r", str(FPS), "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(dst))


def captioned(src: Path, cap: Path, dst: Path, seconds: float) -> None:
    ff(
        "-i", str(src), "-loop", "1", "-i", str(cap),
        "-filter_complex",
        f"[1:v]format=rgba,fade=t=in:st=0.30:d=0.45:alpha=1,"
        f"fade=t=out:st={seconds - 0.55:.2f}:d=0.4:alpha=1[c];"
        f"[0:v][c]overlay=0:0:format=auto,format=yuv420p[v]",
        "-map", "[v]", "-t", f"{seconds:.3f}", "-r", str(FPS),
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(dst),
    )


def end_card(dst: Path, seconds: float) -> None:
    """Same logo landing as the short spots."""
    cfg = {
        "f_brand": ImageFont.truetype(FONT, 84),
        "f_url": ImageFont.truetype(FONT_REG, 33),
    }
    frames = BUILD / "story_end_frames"
    shutil.rmtree(frames, ignore_errors=True)
    frames.mkdir(parents=True)
    n = int(round(seconds * FPS))
    for i in range(n):
        t = i / FPS
        img = background(t)
        brand = _brand(t, cfg)
        k = min(t / 0.35, 1.0)
        Image.blend(img, brand, k).convert("RGB").save(frames / f"{i:05d}.png")
    ff("-framerate", str(FPS), "-i", str(frames / "%05d.png"),
       "-vf", "format=yuv420p,setsar=1", "-r", str(FPS),
       "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(dst))
    shutil.rmtree(frames, ignore_errors=True)


def _brand(t: float, cfg: dict) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    grow = 1 - (1 - min(t / 0.8, 1.0)) ** 3
    scale = 0.92 + 0.08 * grow + 0.014 * min(t, 3.0)
    mark = badge_image()
    size = int(mark.width * scale)
    mark = mark.resize((size, size), Image.Resampling.LANCZOS)
    img.alpha_composite(mark, ((W - size) // 2, 620 - size // 2))
    bw = draw.textlength("Taxi and Fly", font=cfg["f_brand"])
    draw.text(((W - bw) / 2, 1080 + (1 - grow) * 18), "Taxi and Fly", font=cfg["f_brand"], fill=GOLD + (255,))
    url = "taxiapp2026.github.io/taxi-client-app"
    uw = draw.textlength(url, font=cfg["f_url"])
    fade = min(max((t - 0.5) / 0.5, 0.0), 1.0)
    draw.text(((W - uw) / 2, 1230), url, font=cfg["f_url"], fill=GREY + (int(230 * fade),))
    return img


VOICE_LEAD = 0.45


async def narration() -> list[Path]:
    """One take per shot, plus the brand line for the end card."""
    lines = [el for _, el, _, _, _ in SHOTS] + ["Taxi and Fly."]
    out: list[Path] = []
    for i, line in enumerate(lines):
        mp3 = BUILD / f"story_vo_{i:02d}.mp3"
        wav = BUILD / f"story_vo_{i:02d}.wav"
        print("TTS", line)
        await speak(line, mp3)
        trim_edges(mp3, wav)
        out.append(wav)
    return out


async def main() -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    vo = await narration()
    # Let every shot run as long as its line needs, never shorter than SHOT.
    durs = [max(SHOT, duration(v) + VOICE_LEAD + 0.75) for v in vo[:-1]]
    end_sec = max(END_SEC, duration(vo[-1]) + 1.8)

    clips: list[Path] = []
    for i, (name, el, en, pan, zoom) in enumerate(SHOTS):
        src = STORY / name
        if not src.exists():
            raise SystemExit(f"missing still {src}")
        raw = BUILD / f"story_{i:02d}_raw.mp4"
        cap = BUILD / f"story_{i:02d}_cap.png"
        clip = BUILD / f"story_{i:02d}.mp4"
        kenburns(src, raw, durs[i], zoom, pan)
        caption_png(el, en, cap)
        captioned(raw, cap, clip, durs[i])
        clips.append(clip)

    end = BUILD / "story_end.mp4"
    end_card(end, end_sec)
    clips.append(end)

    silent = BUILD / "story_silent.mp4"
    xfade_concat(clips, silent, fade=FADE)
    total = duration(silent)

    starts = []
    acc = 0.0
    for d in durs:
        starts.append(acc)
        acc += d - FADE
    end_start = acc

    bed = BUILD / "story_reggae.wav"
    reggae_music(total + 0.4, bed)
    sting = BUILD / "story_sting.wav"
    logo_sting(total + 0.4, end_start + 0.3, sting)

    delays = [int((s + VOICE_LEAD) * 1000) for s in starts] + [int((end_start + 0.7) * 1000)]
    args: list[str] = ["-i", str(bed), "-i", str(sting)]
    for v in vo:
        args += ["-i", str(v)]

    # The reggae stops dead as the logo lands; only the sting and the name remain.
    parts = [
        f"[0:a]volume=0.62,afade=t=out:st={end_start - 0.15:.3f}:d=0.35,"
        "aformat=sample_rates=44100:channel_layouts=stereo[m]",
        "[1:a]volume=0.55,aformat=sample_rates=44100:channel_layouts=stereo[s]",
    ]
    labels = []
    for k, d in enumerate(delays):
        lbl = f"v{k}"
        parts.append(f"[{k + 2}:a]adelay={d}|{d},aformat=sample_rates=44100:channel_layouts=stereo[{lbl}]")
        labels.append(f"[{lbl}]")
    parts.append(
        "".join(labels) + f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0:normalize=0,"
        f"{VOICE_FX},asplit=2[vv][vk]"
    )
    # Duck the music whenever the narrator speaks.
    parts.append("[m][vk]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[md]")
    parts.append(
        "[md][s][vv]amix=inputs=3:duration=longest:dropout_transition=0:normalize=0,"
        "loudnorm=I=-16:TP=-1.5:LRA=11,"
        f"alimiter=limit=0.95,atrim=0:{total:.3f},asetpts=PTS-STARTPTS[a]"
    )

    audio = BUILD / "story_mix.m4a"
    ff(*args, "-filter_complex", ";".join(parts), "-map", "[a]", "-t", f"{total:.3f}",
       "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k", str(audio))

    tmp = BUILD / "story_tmp.mp4"
    mix(silent, audio, tmp)
    ff(
        "-i", str(tmp),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
        "-preset", "medium", "-crf", "20",
        "-fps_mode", "cfr", "-r", str(FPS),
        "-g", str(FPS * 2), "-keyint_min", str(FPS), "-sc_threshold", "0",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k",
        "-movflags", "+faststart", str(OUT),
    )
    tmp.unlink(missing_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "taxi_and_fly_istoria_aerodromio.mp4").write_bytes(OUT.read_bytes())
    print("Wrote", OUT, round(duration(OUT), 2), "s")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
