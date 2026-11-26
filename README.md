# voxt-echo-test

A one-take echo test for meetings in [Voxt](https://github.com/sgl-project/sglang-omni/tree/main/Voxt). The Mac's speakers play the other side (the system track) and a phone plays you (the microphone track), in sync. The take shows how well echo cancellation works at several speaker volumes, and how much of your own voice it costs.

| Slot | System track (Mac) | Microphone track (phone) |
|---|---|---|
| 1 | silent | speaks |
| 2 | speaks, volume 75% | silent |
| 3 | speaks, volume 30% | speaks |
| 4 | speaks, volume 50% | speaks |
| 5 | speaks, volume 75% | speaks |

- Each track plays the same clip in every slot, so the slots differ only in the Mac's volume.
- Slot k starts with k beeps.
- The two tracks are Mandarin speech from the macOS voices Tingting and Meijia. They share no words, so Voxt's transcript echo check cannot confuse them.
- The microphone track is 12 dB louder with its peaks limited, because a phone's speaker at full volume is still quieter than a voice.

## Use

You need macOS (for `say`, `afconvert` and `osascript`), Python 3 and [uv](https://docs.astral.sh/uv/).

```sh
uv run --no-project --with numpy python -I make_ablation.py   # makes the audio in ablation/
python3 server.py                                              # port 8766, or set PORT
```

1. **Mac:** open http://localhost:8766/ and press "Ready".
2. **Phone:** on the same Wi-Fi, open the address the Mac page shows (or scan its code) in Safari and tap "Ready".
3. **Match the levels:** on the Mac page, press "Measure my voice" and read the line shown. Then press "Measure the phone" and set the phone's volume with its side buttons until the page says they match.
4. **Test:** start a meeting in Voxt, then press "Start test" on the Mac page. Both devices start together. The server sets the Mac's output volume for each slot and puts it back at the end.

The pages are in English and Chinese: use the switch at the top, or add `?lang=zh` or `?lang=en` to the address.

Without the pages, `./ablation.sh` plays the system track on the Mac. Start `ablation/mic.m4a` on the phone by hand when the script says "go".
