#!/usr/bin/env python3
"""Add a soft original music bed under existing ad videos."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from build_video import duration, ff

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
SR = 44100

VIDEOS = [
    (ROOT / "taxi-and-fly-athens-to-airport-el.mp4", Path("/opt/cursor/artifacts/taxi_and_fly_athina_aerodromio.mp4")),
    (ROOT / "taxi-and-fly-athens-to-airport-en.mp4", Path("/opt/cursor/artifacts/taxi_and_fly_athens_to_airport_en.mp4")),
    (ROOT / "taxi-and-fly-google-ads-9x16.mp4", Path("/opt/cursor/artifacts/taxi_and_fly_google_ads.mp4")),
    (ROOT / "taxi-and-fly-google-ads-9x16-en.mp4", Path("/opt/cursor/artifacts/taxi_and_fly_english.mp4")),
]


def pretty_music(seconds: float, dst: Path) -> None:
    """Warm, slow original pad + soft melody. Not a known song."""
    n = int(SR * seconds)
    t = np.linspace(0, seconds, n, False)
    # D major-ish: D A Bm G
    roots = [293.66, 440.00, 246.94, 392.00]
    bar = 3.2
    pad = np.zeros(n)
    for i, r in enumerate(roots):
        for k in range(int(seconds / (bar * 4)) + 1):
            t0 = (k * 4 + i) * bar
            if t0 >= seconds:
                break
            env = np.zeros(n)
            mask = (t >= t0) & (t < t0 + bar + 0.8)
            tt = t[mask] - t0
            env[mask] = np.minimum(tt / 0.35, 1.0) * np.minimum((bar + 0.6 - tt) / 0.7, 1.0)
            env = np.clip(env, 0, 1)
            chord = (
                0.11 * np.sin(2 * math.pi * r * t)
                + 0.08 * np.sin(2 * math.pi * r * 1.25 * t)
                + 0.07 * np.sin(2 * math.pi * r * 1.5 * t)
                + 0.045 * np.sin(2 * math.pi * r * 2.0 * t)
            )
            pad += chord * env
    # soft high melody
    notes = [587.33, 659.25, 739.99, 659.25, 587.33, 493.88, 440.00, 493.88]
    step = 1.6
    mel = np.zeros(n)
    for i, f0 in enumerate(notes * (int(seconds / (step * len(notes))) + 1)):
        t0 = 0.8 + i * step
        if t0 >= seconds - 0.4:
            break
        leng = int(0.9 * SR)
        i0 = int(t0 * SR)
        tt = np.linspace(0, 0.9, leng, False)
        tone = 0.028 * np.sin(2 * math.pi * f0 * tt) * np.exp(-1.6 * tt)
        sl = slice(i0, min(i0 + leng, n))
        mel[sl] += tone[: sl.stop - sl.start]
    env = np.minimum(np.minimum(t / 1.4, 1.0), np.minimum((seconds - t) / 2.2, 1.0))
    audio = np.clip((pad + mel) * env * 0.85, -0.95, 0.95)
    pcm = (audio * 32767).astype(np.int16)
    import wave

    with wave.open(str(dst), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def remix(src: Path, dst: Path, art: Path) -> None:
    sec = duration(src)
    bed = BUILD / f"pretty_{src.stem}.wav"
    pretty_music(sec + 0.4, bed)
    fade_out = max(sec - 2.0, 1.0)
    tmp = BUILD / f"pretty_{src.stem}.mp4"
    ff(
        "-i", str(src), "-i", str(bed),
        "-filter_complex",
        f"[1:a]volume=0.20,afade=t=in:st=0:d=1.3,afade=t=out:st={fade_out:.2f}:d=1.8,"
        f"aformat=sample_rates=44100:channel_layouts=stereo[m];"
        f"[0:a][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k",
        "-shortest", "-movflags", "+faststart", str(tmp),
    )
    tmp.replace(dst)
    art.parent.mkdir(parents=True, exist_ok=True)
    art.write_bytes(dst.read_bytes())
    print("music", dst, round(sec, 2))


def main() -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    for src, art in VIDEOS:
        if src.exists():
            remix(src, src, art)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
