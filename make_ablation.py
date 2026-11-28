"""Builds the one-take ablation: ablation/system.wav (the Mac plays it) and
ablation/mic.wav (the phone plays it), plus ablation/schedule.tsv (slot start
times and the Mac's output volume per slot) and ablation/timeline.tsv.

    uv run --no-project --with numpy python -I make_ablation.py

Slots (system / mic):
  1  silent        / speaks
  2  speaks @75%   / silent
  3  speaks @30%   / speaks
  4  speaks @50%   / speaks
  5  speaks @75%   / speaks
Slot k starts with k 1 kHz beeps on the system track; the mic track starts
with a 2 kHz double beep at 0 (sync marker in the raw mic). The system speech
starts before and ends after the mic speech, so the near end is all double talk.
Each track says the same line in every slot after the slot's number, so the slots
differ only in the system volume. Apart from the numbers the two voices share no
words, so the transcript's echo check cannot confuse them.
"""

import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 48000
LEVEL = 10 ** (-20 / 20)  # speech RMS, both voices
# A phone's speaker at full volume is still quieter than a voice, so the mic
# track is louder, its peaks limited to CEILING.
MIC_GAIN_DB = 12
CEILING = 10 ** (-1 / 20)
HERE = Path(__file__).parent
OUT = HERE / "ablation"

MIC_TEXT = "麦克风在说话。今天上午我把季度报告的初稿发给了财务部，他们答应下周二之前给反馈。"
SYSTEM_TEXT = "这里是对方的声音。昨晚的暴雨让城东好几条道路积水，地铁二号线也临时停运了一个多小时，很多人上班都迟到了。"
MIC_SLOTS, SYSTEM_SLOTS = {1, 3, 4, 5}, {2, 3, 4, 5}
# Each clip starts with its slot's number: Voxt's final pass drops a chunk whose text
# is the same as the chunk before it, which would cost every other slot's line.
SLOT_NAMES = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五"}


def labelled(k, text):
    return f"第{SLOT_NAMES[k]}段。{text}"

VOLUME = {1: 50, 2: 75, 3: 30, 4: 50, 5: 75}  # slot 1: only its beep plays
MIC_VOICE, SYSTEM_VOICE = "Tingting", "Meijia"


def tts(voice, text, tmp):
    aiff, wav = Path(tmp) / "t.aiff", Path(tmp) / "t.wav"
    subprocess.run(["say", "-v", voice, "-o", str(aiff), text], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", f"LEI16@{SR}", "-c", "1", str(aiff), str(wav)], check=True)
    with wave.open(str(wav)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float64) / 32768
    nz = np.flatnonzero(np.abs(x) > 1e-3)
    x = x[nz[0]:nz[-1] + 1]
    return x * LEVEL / np.sqrt(np.mean(x ** 2))


def limit(x, ceiling=CEILING, hold=0.04):
    """Peak limiter: the gain is the lowest one needed within ±hold, smoothed over hold."""
    need = np.minimum(1, ceiling / np.maximum(np.abs(x), 1e-9))
    w = int(hold * SR) | 1
    padded = np.pad(need, w, constant_values=1)
    gain = np.lib.stride_tricks.sliding_window_view(padded, 2 * w + 1).min(axis=1)[:len(x)]
    kernel = np.ones(w) / w
    gain = np.convolve(np.pad(gain, w, mode="edge"), kernel, mode="same")[w:-w]
    return x * gain


def beep(freq, dur=0.25, level=-14):
    t = np.arange(int(dur * SR)) / SR
    ramp = np.minimum(1, np.minimum(t, dur - t) / 0.01)
    return 10 ** (level / 20) * ramp * np.sin(2 * np.pi * freq * t)


def put(track, x, at):
    i = int(at * SR)
    if len(track) < i + len(x):
        track.resize(i + len(x), refcheck=False)
    track[i:i + len(x)] += x


def save(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main():
    OUT.mkdir(exist_ok=True)
    system, mic = np.zeros(0), np.zeros(0)
    with tempfile.TemporaryDirectory() as tmp:
        mic_clips = {k: limit(tts(MIC_VOICE, labelled(k, MIC_TEXT), tmp) * 10 ** (MIC_GAIN_DB / 20)) for k in MIC_SLOTS}
        system_clips = {k: tts(SYSTEM_VOICE, labelled(k, SYSTEM_TEXT), tmp) for k in SYSTEM_SLOTS}
    put(mic, beep(2000, 0.1), 0.0)
    put(mic, beep(2000, 0.1), 0.2)
    t = 2.0
    schedule, timeline = [], []
    for k in range(1, 6):
        for i in range(k):
            put(system, beep(1000, 0.12), t + 0.2 * i)
        schedule.append((t - 0.3, VOLUME[k]))
        t += 0.2 * (k - 1)
        end = t
        s = system_clips.get(k)
        if s is not None:
            put(system, s, t + 1.0)
            timeline.append((k, "system", t + 1.0, t + 1.0 + len(s) / SR, labelled(k, SYSTEM_TEXT)))
            end = max(end, t + 1.0 + len(s) / SR)
        m = mic_clips.get(k)
        if m is not None:
            start = t + (1.8 if s is not None else 1.0)
            put(mic, m, start)
            timeline.append((k, "mic", start, start + len(m) / SR, labelled(k, MIC_TEXT)))
            end = max(end, start + len(m) / SR)
        t = end + 1.5
    n = int((t + 1.0) * SR)
    system.resize(n, refcheck=False)
    mic.resize(n, refcheck=False)
    save(OUT / "system.wav", system)
    save(OUT / "mic.wav", mic)
    (OUT / "schedule.tsv").write_text("".join(f"{a:.2f}\t{v}\n" for a, v in schedule))
    (OUT / "timeline.tsv").write_text("".join(f"{k}\t{w}\t{a:.2f}\t{b:.2f}\t{txt}\n" for k, w, a, b, txt in timeline))
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(OUT / "mic.wav"), str(OUT / "mic.m4a")], check=True)
    print(f"{n / SR:.1f} s")
    print((OUT / "timeline.tsv").read_text())


if __name__ == "__main__":
    main()
