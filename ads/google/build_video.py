#!/usr/bin/env python3
"""Build a 9:16 Google Ads video for Taxi and Fly.

This is a real MP4 (motion, app screen-recording, audio), not a photo carousel.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
STILLS = ROOT / "stills"
BUILD = ROOT / "build"
OUT = ROOT / "taxi-and-fly-google-ads-9x16.mp4"
OUT_15 = ROOT / "taxi-and-fly-google-ads-15s-9x16.mp4"
SRC_APP = Path("/home/ubuntu/.cursor/projects/workspace/uploads/TAXI-AND-FLY-mikro_eaaa.mp4")

W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"


def run(cmd: list[str], **kw) -> None:
    print("+", " ".join(str(c) for c in cmd[:8]), "..." if len(cmd) > 8 else "")
    subprocess.check_call(cmd, **kw)


def ff(*args: str) -> None:
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args])


def kenburns(src: Path, dst: Path, seconds: float, zoom_end: float = 1.14, pan: str = "center") -> None:
    """Camera move over a still → actual video frames."""
    frames = int(round(seconds * FPS))
    # zoompan d is frame count; input must be larger than output
    if pan == "up":
        y_expr = "ih/2-(ih/zoom/2)-on*0.35"
        x_expr = "iw/2-(iw/zoom/2)"
    elif pan == "down":
        y_expr = "ih/2-(ih/zoom/2)+on*0.25"
        x_expr = "iw/2-(iw/zoom/2)"
    elif pan == "left":
        y_expr = "ih/2-(ih/zoom/2)"
        x_expr = "iw/2-(iw/zoom/2)-on*0.28"
    else:
        y_expr = "ih/2-(ih/zoom/2)"
        x_expr = "iw/2-(iw/zoom/2)"
    z_expr = f"1.02+{zoom_end - 1.02}*on/{frames}"
    vf = (
        f"scale=1620:2880:force_original_aspect_ratio=increase,"
        f"crop=1620:2880,"
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={frames}:s={W}x{H}:fps={FPS},"
        f"format=yuv420p"
    )
    ff("-loop", "1", "-i", str(src), "-vf", vf, "-frames:v", str(frames),
       "-r", str(FPS), "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(dst))


def morph_pair(a: Path, b: Path, dst: Path, seconds: float, zoom: float = 1.10) -> None:
    """Crossfade two poses of the same actor so the person appears to move."""
    fade = 1.0
    half = (seconds + fade) / 2
    offset = half - fade
    tmp = dst.with_name(dst.stem + "_xfade.mp4")
    ff("-loop", "1", "-t", f"{half:.3f}", "-i", str(a),
       "-loop", "1", "-t", f"{half:.3f}", "-i", str(b),
       "-filter_complex",
       f"[0]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},format=yuv420p[a];"
       f"[1]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},format=yuv420p[b];"
       f"[a][b]xfade=transition=fade:duration={fade:.3f}:offset={offset:.3f}[v]",
       "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(tmp))
    # Slow push-in on the morph clip
    ff("-i", str(tmp),
       "-vf",
       f"scale=1215:2160,crop={W}:{H}:'(in_w-out_w)*t/{seconds}':'(in_h-out_h)*t/{max(seconds*0.7,0.1)}',"
       "format=yuv420p",
       "-t", f"{seconds:.3f}", "-r", str(FPS),
       "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(dst))
    tmp.unlink(missing_ok=True)


def caption_clip(src: Path, dst: Path, text: str, banner: bool = False) -> None:
    txt = BUILD / (dst.stem + "_cap.txt")
    txt.write_text(text, encoding="utf-8")
    if banner:
        y = "80"
        fs = 40
        box_a = "0.55"
    else:
        y = "h-280"
        fs = 52
        box_a = "0.50"
    vf = (
        f"drawtext=fontfile={FONT}:textfile={txt}:reload=0:"
        f"fontsize={fs}:fontcolor=white:line_spacing=12:"
        f"x=(w-text_w)/2:y={y}:box=1:boxcolor=black@{box_a}:boxborderw=28"
    )
    ff("-i", str(src), "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "18",
       "-an", "-r", str(FPS), str(dst))


def app_process_clip(dst: Path) -> None:
    """Real screen-recording video of the Taxi and Fly booking flow, sped up."""
    parts = [
        (4.8, 2.1),    # home
        (22.2, 12.4),  # destination + price + book
        (35.0, 11.5),  # passenger + driver accept
        (56.8, 8.5),   # ready / driver coming
    ]
    clips = []
    for i, (ss, dur) in enumerate(parts):
        p = BUILD / f"app_raw_{i}.mp4"
        ff("-ss", f"{ss}", "-i", str(SRC_APP), "-t", f"{dur}",
           "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},format=yuv420p",
           "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(p))
        clips.append(p)
    lst = BUILD / "app_concat.txt"
    lst.write_text("".join(f"file '{c}'\n" for c in clips))
    merged = BUILD / "app_merged.mp4"
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(merged))
    # ~34.5s of footage → about 11.5s
    ff("-i", str(merged),
       "-vf", f"setpts=0.33*PTS,scale={W}:{H},setsar=1,fps={FPS},format=yuv420p",
       "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(dst))


def end_card(dst: Path, seconds: float = 4.6) -> None:
    img = Image.new("RGB", (W, H), (8, 8, 8))
    draw = ImageDraw.Draw(img)
    try:
        f_brand = ImageFont.truetype(FONT, 92)
        f_sub = ImageFont.truetype(FONT_REG, 48)
        f_small = ImageFont.truetype(FONT_REG, 36)
    except OSError:
        f_brand = f_sub = f_small = ImageFont.load_default()

    def center(text: str, y: int, font, fill) -> None:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) / 2, y), text, font=font, fill=fill)

    center("Taxi and Fly", 760, f_brand, (255, 210, 40))
    center("Κλείσε ταξί πριν καν προσγειωθείς", 900, f_sub, (255, 255, 255))
    center("Τιμή με βάση το ταξίμετρο", 990, f_small, (255, 210, 40))
    center("Αναμονή οδηγού έως 1 ώρα", 1048, f_small, (255, 210, 40))
    center("Κατέβασε την εφαρμογή", 1180, f_sub, (230, 230, 230))
    png = BUILD / "endcard.png"
    img.save(png)
    frames = int(round(seconds * FPS))
    ff("-loop", "1", "-i", str(png),
       "-vf", f"fade=t=in:st=0:d=0.45,fade=t=out:st={seconds-0.4}:d=0.4,format=yuv420p",
       "-frames:v", str(frames), "-r", str(FPS),
       "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(dst))


def duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], text=True)
    return float(out.strip())


def xfade_concat(clips: list[Path], dst: Path, fade: float = 0.35) -> None:
    if len(clips) == 1:
        shutil.copy(clips[0], dst)
        return
    durs = [duration(c) for c in clips]
    args: list[str] = []
    for c in clips:
        args += ["-i", str(c)]
    parts = []
    last = "[0:v]"
    acc = durs[0]
    for i in range(1, len(clips)):
        offset = max(acc - fade, 0.05)
        out = f"[v{i}]"
        parts.append(f"{last}[{i}:v]xfade=transition=fade:duration={fade}:offset={offset:.3f}{out}")
        last = out
        acc = acc + durs[i] - fade
    fc = ";".join(parts)
    ff(*args, "-filter_complex", fc, "-map", last,
       "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-r", str(FPS), str(dst))


def burn_captions(src: Path, dst: Path, ass: Path) -> None:
    ff("-i", str(src), "-vf", f"ass={ass}",
       "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-an", str(dst))


def write_ass(path: Path) -> None:
    path.write_text(
        """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Noto Sans,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,3,8,0,2,70,70,160,1
Style: Banner,Noto Sans,42,&H0000D4FF,&H00FFFFFF,&H00000000,&HCC000000,-1,0,0,0,100,100,0,0,3,6,0,8,50,50,70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.40,0:00:03.70,Caption,,0,0,0,,Καλεί από το εξωτερικό
Dialogue: 0,0:00:03.90,0:00:07.10,Caption,,0,0,0,,Κλείνει ταξί πριν πετάξει για Αθήνα
Dialogue: 0,0:00:07.30,0:00:09.20,Caption,,0,0,0,,Μέσα από το κινητό
Dialogue: 0,0:00:09.30,0:00:20.80,Banner,,0,0,0,,Η διαδικασία στο Taxi and Fly
Dialogue: 0,0:00:21.10,0:00:24.20,Caption,,0,0,0,,Αθήνα · Αφίξεις
Dialogue: 0,0:00:24.40,0:00:27.50,Caption,,0,0,0,,Ο οδηγός σε περιμένει
Dialogue: 0,0:00:27.70,0:00:30.40,Caption,,0,0,0,,Προς τον προορισμό
Dialogue: 0,0:00:30.60,0:00:33.40,Caption,,0,0,0,,Έφτασε
""",
        encoding="utf-8",
    )


def make_audio(seconds: float, dst: Path) -> None:
    sr = 44100
    n = int(sr * seconds)
    t = np.linspace(0, seconds, n, False)
    pad = (
        0.055 * np.sin(2 * math.pi * 196.0 * t)
        + 0.040 * np.sin(2 * math.pi * 246.94 * t)
        + 0.032 * np.sin(2 * math.pi * 293.66 * t)
        + 0.022 * np.sin(2 * math.pi * 392.0 * t)
        + 0.012 * np.sin(2 * math.pi * 493.88 * t)
    )
    env = np.minimum(np.minimum(t / 1.6, 1.0), np.minimum((seconds - t) / 2.0, 1.0))
    trem = 0.88 + 0.12 * np.sin(2 * math.pi * 0.12 * t)
    audio = pad * env * trem
    # soft scene whooshes ~ every 3.5s
    for hit in (3.6, 7.2, 9.1, 20.9, 24.2, 27.4, 30.5):
        if hit >= seconds:
            continue
        i0 = int(hit * sr)
        leng = int(0.28 * sr)
        tt = np.linspace(0, 1, leng, False)
        whoosh = 0.045 * np.sin(2 * math.pi * (420 - 260 * tt) * tt) * np.exp(-3.2 * tt)
        audio[i0 : i0 + leng] += whoosh[: max(0, min(leng, n - i0))]
    audio = np.clip(audio, -0.95, 0.95)
    pcm = (audio * 32767).astype(np.int16)
    import wave

    with wave.open(str(dst), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def mix(video: Path, audio: Path, dst: Path) -> None:
    ff("-i", str(video), "-i", str(audio),
       "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
       "-shortest", "-movflags", "+faststart", str(dst))


def make_15s(full: Path, dst: Path) -> None:
    """Tighter cut for bumper / in-feed: first 11s + last 4s of the full ad."""
    a = BUILD / "cut_a.mp4"
    b = BUILD / "cut_b.mp4"
    tot = duration(full)
    ff("-i", str(full), "-t", "11.0", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
       "-c:a", "aac", "-b:a", "160k", str(a))
    ff("-ss", f"{max(tot - 4.2, 0)}", "-i", str(full), "-t", "4.2",
       "-c:v", "libx264", "-preset", "fast", "-crf", "18",
       "-c:a", "aac", "-b:a", "160k", str(b))
    ff("-i", str(a), "-i", str(b),
       "-filter_complex",
       "[0:v][1:v]xfade=transition=fade:duration=0.35:offset=10.65[v];"
       "[0:a][1:a]acrossfade=d=0.35[a]",
       "-map", "[v]", "-map", "[a]",
       "-c:v", "libx264", "-preset", "fast", "-crf", "18",
       "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(dst))


def main() -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    if not SRC_APP.exists():
        print("Missing source app video", SRC_APP, file=sys.stderr)
        return 1

    c_call = BUILD / "01_call.mp4"
    c_look = BUILD / "02_look.mp4"
    c_shoulder = BUILD / "03_shoulder.mp4"
    c_app = BUILD / "04_app.mp4"
    c_arr = BUILD / "05_arrivals.mp4"
    c_taxi = BUILD / "06_taxi.mp4"
    c_ride = BUILD / "07_ride.mp4"
    c_dest = BUILD / "08_dest.mp4"
    c_end = BUILD / "09_end.mp4"

    print("== actor motion clips ==")
    morph_pair(STILLS / "01_berlin_call.png", STILLS / "01b_speaking.png", BUILD / "01_call_raw.mp4", 3.8)
    kenburns(STILLS / "02_berlin_looking_phone.png", BUILD / "02_look_raw.mp4", 3.4, 1.18, "down")
    kenburns(STILLS / "03_over_shoulder_blank_phone.png", BUILD / "03_shoulder_raw.mp4", 2.2, 1.22, "center")
    caption_clip(BUILD / "01_call_raw.mp4", c_call, "Καλεί από το εξωτερικό")
    caption_clip(BUILD / "02_look_raw.mp4", c_look, "Κλείνει ταξί πριν πετάξει για Αθήνα")
    caption_clip(BUILD / "03_shoulder_raw.mp4", c_shoulder, "Μέσα από το κινητό")

    print("== real app process video ==")
    app_process_clip(BUILD / "04_app_raw.mp4")
    caption_clip(BUILD / "04_app_raw.mp4", c_app, "Η διαδικασία στο Taxi and Fly", banner=True)

    print("== arrival / destination motion ==")
    morph_pair(STILLS / "04_athens_arrivals.png", STILLS / "04b_arrivals_step.png", BUILD / "05_arrivals_raw.mp4", 3.4)
    morph_pair(STILLS / "05_taxi_pickup.png", STILLS / "05b_getting_in.png", BUILD / "06_taxi_raw.mp4", 3.3)
    kenburns(STILLS / "06_in_taxi_athens.png", BUILD / "07_ride_raw.mp4", 2.9, 1.12, "left")
    kenburns(STILLS / "07_destination_athens.png", BUILD / "08_dest_raw.mp4", 3.0, 1.10, "up")
    caption_clip(BUILD / "05_arrivals_raw.mp4", c_arr, "Αθήνα · Αφίξεις")
    caption_clip(BUILD / "06_taxi_raw.mp4", c_taxi, "Ο οδηγός σε περιμένει")
    caption_clip(BUILD / "07_ride_raw.mp4", c_ride, "Προς τον προορισμό")
    caption_clip(BUILD / "08_dest_raw.mp4", c_dest, "Έφτασε")
    end_card(c_end, 4.8)

    print("== assemble ==")
    silent = BUILD / "silent.mp4"
    xfade_concat(
        [c_call, c_look, c_shoulder, c_app, c_arr, c_taxi, c_ride, c_dest, c_end],
        silent,
        fade=0.32,
    )

    dur = duration(silent)
    wav = BUILD / "bed.wav"
    make_audio(dur + 0.4, wav)
    mix(silent, wav, OUT)
    print("Wrote", OUT, "duration", duration(OUT))

    try:
        make_15s(OUT, OUT_15)
        print("Wrote", OUT_15, "duration", duration(OUT_15))
    except subprocess.CalledProcessError as e:
        print("15s cut failed:", e, file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
