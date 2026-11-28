"""Sync test: the Mac's speakers alone play chirps, and a Voxt meeting's
microphone hears them back. How much later each chirp is in mic.wav than in
system.wav is how far the two recordings are apart.

    uv run --no-project --with numpy python -I sync_test.py make      # sync/chirps.wav
    afplay sync/chirps.wav                                            # during a meeting
    uv run --no-project --with numpy python -I sync_test.py measure <meeting dir>

The chirps (100 ms, 500 Hz to 4 kHz) are unlike any shift of themselves, and
come at uneven gaps, so the whole recording lines up at one lag (found first,
however large); each chirp is then measured near it.
"""

import sys
import wave
from pathlib import Path

import numpy as np

SR = 48000
OUT = Path(__file__).parent / "sync"
CHIRP_S, F0, F1 = 0.1, 500, 4000
GAPS = [1.0, 1.3, 0.8, 1.1, 0.9, 1.4, 0.7, 1.2]  # between chirp starts, repeated
COUNT = 40
REFINE = 0.05  # s searched either way around the whole-file lag


def chirp(sr):
    t = np.arange(int(CHIRP_S * sr)) / sr
    k = (F1 - F0) / CHIRP_S
    ramp = np.minimum(1, np.minimum(t, CHIRP_S - t) / 0.005)
    return 0.5 * ramp * np.sin(2 * np.pi * (F0 * t + k * t * t / 2))


def starts():
    t, out = 1.0, []
    for i in range(COUNT):
        out.append(t)
        t += GAPS[i % len(GAPS)]
    return out, t + 1.0


def make():
    OUT.mkdir(exist_ok=True)
    at, total = starts()
    x = np.zeros(int(total * SR))
    c = chirp(SR)
    for a in at:
        i = int(a * SR)
        x[i:i + len(c)] += c
    with wave.open(str(OUT / "chirps.wav"), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    print(f"{OUT / 'chirps.wav'}: {COUNT} chirps, {total:.1f} s")


def load(path):
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), "<i2") / 32768, w.getframerate()


def peak(r):
    """Index of r's largest value, refined by a parabola through its neighbours."""
    k = int(np.argmax(r))
    if 0 < k < len(r) - 1:
        a, b, c = r[k - 1], r[k], r[k + 1]
        if a - 2 * b + c != 0:
            return k + 0.5 * (a - c) / (a - 2 * b + c)
    return float(k)


def coarse_lag(a, b):
    """Samples b lags a by, from the whole files (GCC-PHAT)."""
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    r = np.fft.rfft(b, n) * np.conj(np.fft.rfft(a, n))
    x = np.fft.irfft(r / (np.abs(r) + 1e-12), n)
    k = int(np.argmax(x))
    return k if k < n // 2 else k - n


def measure(meeting):
    meeting = Path(meeting)
    sysx, sr = load(meeting / "system.wav")
    mic, _ = load(meeting / "mic.wav")
    print(f"system.wav {len(sysx) / sr:.2f} s, mic.wav {len(mic) / sr:.2f} s")
    c = chirp(sr)
    # The chirps in system.wav: matched filter, peaks at least 0.5 s apart.
    m = np.abs(np.correlate(sysx, c, "valid"))
    found, i = [], 0
    floor = 0.3 * m.max()
    while i < len(m):
        if m[i] > floor:
            j = i + int(0.05 * sr)
            k = i + int(np.argmax(m[i:j]))
            found.append(k)
            i = k + int(0.5 * sr)
        else:
            i += 1
    # Speech can match a little: a chirp's window correlates with it almost wholly.
    norm = np.linalg.norm(c)
    found = [k for k in found if m[k] >= 0.5 * norm * np.linalg.norm(sysx[k:k + len(c)])]
    base = coarse_lag(sysx, mic)
    lags, quality = [], []
    span, n = int(REFINE * sr), len(c)
    for k in found:
        lo, hi = k + base - span, k + base + n + span
        if lo < 0 or hi > len(mic):
            continue
        r = np.correlate(mic[lo:hi], c, "valid")  # lag base at index span
        r = np.abs(r)
        p = peak(r)
        if not 1 <= p <= len(r) - 2:
            continue  # no match near the lag: a chirp one track cut short
        lags.append((base + p - span) / sr * 1000)
        quality.append(r.max() / (np.median(r) + 1e-12))
    keep = [q >= 0.3 * np.median(quality) for q in quality]
    lags = [v for v, k in zip(lags, keep) if k]
    quality = [q for q, k in zip(quality, keep) if k]
    if not lags:
        print(f"no chirps; the whole recording's lag: {base / sr * 1000:.1f} ms")
        return
    lags = np.array(lags)
    print(f"{len(lags)} chirps; mic later than system by (ms):")
    print("  " + " ".join(f"{v:.1f}" for v in lags))
    print(f"  median {np.median(lags):.1f}, min {lags.min():.1f}, max {lags.max():.1f}, "
          f"spread {lags.max() - lags.min():.1f}; peak/median {np.median(quality):.0f}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["make"]:
        make()
    elif sys.argv[1:2] == ["measure"] and len(sys.argv) == 3:
        measure(sys.argv[2])
    else:
        sys.exit(__doc__)
