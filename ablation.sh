#!/usr/bin/env bash
# The one-take ablation (make_ablation.py) without the phone page, run during a
# meeting in Voxt: plays ablation/system.wav on the Mac, setting the output volume per slot
# (ablation/schedule.tsv), after a 3 s count-down; start the phone's
# ablation/mic.m4a at "go". The Mac's volume is put back afterwards.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
old=$(osascript -e 'output volume of (get volume settings)')
trap 'kill $(jobs -p) 2>/dev/null; osascript -e "set volume output volume $old"' EXIT
for i in 3 2 1; do echo "$i…"; sleep 1; done
echo "go: start the phone now"
while IFS=$'\t' read -r at vol; do
  (sleep "$at"; osascript -e "set volume output volume $vol"; echo "volume $vol") &
done < "$here/ablation/schedule.tsv"
afplay "$here/ablation/system.wav"
sleep 2
echo "done: end the meeting"
