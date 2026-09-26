#!/usr/bin/env python3
"""Original audio for the short spots: a logo sting and a second music bed."""

from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np

SR = 44100


def write_wav(path: Path, audio: np.ndarray) -> None:
    pcm = (np.clip(audio, -0.97, 0.97) * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path)) as wf:
        raw = wf.readframes(wf.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32767.0


def logo_sting(seconds: float, hit: float, dst: Path) -> None:
    """Warm bell that lands with the logo, with a short breath of air before it."""
    n = int(SR * seconds)
    out = np.zeros(n)

    # Rising air just ahead of the logo.
    rise = 0.42
    i0 = max(int((hit - rise) * SR), 0)
    leng = min(int(rise * SR), n - i0)
    if leng > 0:
        tt = np.linspace(0, 1, leng, False)
        noise = np.random.default_rng(7).normal(0, 1, leng)
        smooth = np.convolve(noise, np.ones(90) / 90, mode="same")
        out[i0 : i0 + leng] += 0.16 * smooth * (tt ** 2.2)

    # D major bell: D5, F#5, A5, with the octave on top.
    for freq, amp, delay, decay in (
        (587.33, 0.30, 0.00, 2.2),
        (739.99, 0.20, 0.045, 2.4),
        (880.00, 0.16, 0.090, 2.6),
        (1174.66, 0.08, 0.135, 3.2),
    ):
        j0 = int((hit + delay) * SR)
        if j0 >= n:
            continue
        leng = min(int(2.6 * SR), n - j0)
        tt = np.linspace(0, leng / SR, leng, False)
        tone = amp * np.sin(2 * math.pi * freq * tt) * np.exp(-decay * tt)
        tone += 0.28 * amp * np.sin(2 * math.pi * freq * 2.004 * tt) * np.exp(-decay * 1.8 * tt)
        out[j0 : j0 + leng] += tone

    # Soft low body so the bell has weight on a phone speaker.
    j0 = int(hit * SR)
    leng = min(int(0.7 * SR), n - j0)
    if leng > 0:
        tt = np.linspace(0, leng / SR, leng, False)
        out[j0 : j0 + leng] += 0.22 * np.sin(2 * math.pi * 110.0 * tt) * np.exp(-5.0 * tt)

    write_wav(dst, out)


def plain_music(seconds: float, dst: Path) -> None:
    """Brighter plucked bed for the versions with no voice. Not a known song."""
    n = int(SR * seconds)
    t = np.linspace(0, seconds, n, False)
    out = np.zeros(n)

    # Gentle plucked arpeggio in A major.
    arp = [220.00, 277.18, 329.63, 440.00, 329.63, 277.18]
    step = 0.32
    for i in range(int(seconds / step) + 1):
        t0 = i * step
        if t0 >= seconds - 0.1:
            break
        f0 = arp[i % len(arp)]
        j0 = int(t0 * SR)
        leng = min(int(0.85 * SR), n - j0)
        if leng <= 0:
            continue
        tt = np.linspace(0, leng / SR, leng, False)
        pluck = (
            0.085 * np.sin(2 * math.pi * f0 * tt)
            + 0.034 * np.sin(2 * math.pi * f0 * 2 * tt)
            + 0.016 * np.sin(2 * math.pi * f0 * 3 * tt)
        ) * np.exp(-3.4 * tt)
        out[j0 : j0 + leng] += pluck

    # Low sustain underneath so it never sounds thin.
    out += (
        0.055 * np.sin(2 * math.pi * 110.0 * t)
        + 0.030 * np.sin(2 * math.pi * 164.81 * t)
        + 0.018 * np.sin(2 * math.pi * 220.0 * t)
    ) * (0.9 + 0.1 * np.sin(2 * math.pi * 0.16 * t))

    env = np.minimum(np.minimum(t / 0.9, 1.0), np.minimum((seconds - t) / 1.6, 1.0))
    write_wav(dst, out * np.clip(env, 0, 1) * 0.9)
