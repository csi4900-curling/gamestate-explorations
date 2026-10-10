# Norway unlinked motion: five adjacent-origin review proposals

The [source-wide catalog](norway-global-shot-scoped-cap-motion-first.json)
contains 35 cap tracks with no link to the frozen 141 Norway event candidates.
The [reproducible review rule](norway-unlinked-motion-rescue-proposals-first.json)
selects an unlinked track when it begins within one second of a camera cut,
the immediately preceding shot lasts at least five seconds and has an origin
model score of at least 0.9, and that origin shot is either absent from the
candidate ledger or carries a conflicting provisional colour. These
thresholds were chosen **after inspecting this recording**; this is a
development search, not a recall or precision estimate.

| Origin → receiving track | Candidate-ledger issue | Source review |
|---|---|---|
| S86 → S87-Y01, 1203–1215 s | No candidate | Yellow stone is held at the delivery end, then travels toward the house. |
| S243 → S244-Y01, 3350–3361 s | Candidate says red | The delivery view shows a Norway shooter and a yellow stone; the receiving view shows yellow travel. |
| S443 → S444-Y01, 6235–6242 s | No candidate | Yellow stone is present at the delivery end, then yellow travel appears. |
| S561 → S562-Y01, 7773–7777 s | No candidate | Yellow stone is present at the delivery end, then yellow travel appears; the origin model's original binary decision was negative despite its 0.962 score. |
| S647 → S648-Y01, 8613–8621 s | Candidate says red | Yellow stone is present at the delivery end, then yellow travel appears. |

The [source-frame sheet](norway-unlinked-motion-rescue-source-frames.jpg)
shows four timestamped frames for each proposal. These are agent-reviewed
source observations, **not independent throw labels**. They support
investigating three omitted event proposals and two colour conflicts, but
do not prove stone identity through the camera cut or exact release/settle
times. The main 141-event ledger remains unchanged. A yellow stone moving
after a red delivery can also be an old stone moved by a collision, so even
the colour conflicts require temporal review before correction.

S86 is especially consistent with a missed final delivery of end one: the
[official Norway shot ledger](pwg2022-canada-norway-official-ledger.json)
records shot 16 of end one by Norway (yellow), while the broadcast counter
shows one yellow stone remaining before S86 and becomes unreadable through
the end reset. The official ledger gives shot order, **not** a video timestamp
or an independent label for S86.

Reproduce the proposal list and frame sheet with:

```sh
feasibility/scripts/python.sh prototype/scripts/audit_norway_unlinked_motion_rescues.py
feasibility/scripts/python.sh prototype/scripts/render_norway_unlinked_motion_rescue_frames.py
```

Both outputs preserve source/code hashes and refuse to overwrite their first
runs. The same rule was then applied unchanged to the full Canada–China
recording; its [transfer review](CHINA-UNLINKED-MOTION-TRANSFER.md) found six
proposals, including a receiving-stone colour mismatch that rules out
automatic promotion. Independent full-match event labels remain necessary
for F1.

The [release-side colour audit](UNLINKED-MOTION-RELEASE-COLOUR.md) finds a
unique yellow held-to-motion cue for S647 but abstains on the other four
Norway proposals. This supports reviewing S647's provisional red colour;
it does not justify rejecting the others.

The [first-end sequence hypothesis](NORWAY-END1-SEQUENCE-AND-BOARD-REFERENCE.md)
places S86 after the 15 counter-backed windows and links it to the official
16th shot as a provisional video event. It keeps the official PDF board
states as a separate reference rather than video-derived game state.
