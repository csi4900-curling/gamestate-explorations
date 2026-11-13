# Latvia 1080p stone-body transfer across an earlier match excerpt

The end-6 [body/handle experiment](LATVIA-END6-HIGHRES-RESOLUTION.md)
used one visibly moving yellow stone at source time 2310 s as a template.
To test transfer beyond that one shot, the same frozen template, handle-colour
screen and path rules were run at **1 Hz over every second from 1650 to
2760 s** of the earlier 1080p Latvia excerpt. The
[merged ledger](latvia24-full-v1/early-highres-body-handle-transfer-development.json)
checks 15 source-hashed, nonoverlapping sequential-decoding shards for complete
1,110-second coverage. A 50-second shard matched the slower random-seek
implementation proposal-for-proposal. The existing full-match event detector
and its thresholds were not changed.

The frozen yellow-derived cue produced **144 grey-body proposals**, of which
**88** passed the coloured-handle screen. Greedy temporal linking retained
five upward and two downward image paths. The
[source sheet](latvia24-full-v1/early-highres-body-upward-source-review.jpg)
and [manifest](latvia24-full-v1/early-highres-body-upward-source-review.json)
show that all five upward paths visibly follow moving **yellow stones**.
They start at 2037, 2129, 2309, 2421 and 2603 s and each falls within
25 seconds of a different provisional yellow left-camera candidate. The
2309-s path is the same shot used to select the template, so it cannot count
as independent transfer evidence. Of the 16 provisional left candidates in
this excerpt, five have such an associated upward path: **five of seven
yellow candidates and zero of nine red candidates**. Candidate association is
temporal evidence only; neither the candidates nor these paths are independent
full-match throw labels.

The missing red paths are a **detector failure**, not proof the shots were
absent from the right view. The
[red source sequence](latvia24-full-v1/early-highres-red-moving-source-review.jpg)
shows one red stone moving toward the house over 1989–1993 s and another over
2364–2368 s. Neither produced an upward path under the yellow-derived
template. A postfailure [selected-frame red-template probe](latvia24-full-v1/early-highres-red-template-selected-development.json)
uses an 80×37-pixel grey-body crop from the first red stone at 1991 s. It
matches the moving red body in all five sampled 1989–1993 frames and four
sampled 2364–2367 frames, with red handle-colour support. At 2368 s the
moving red body is no longer the top matched red proposal; parked stones also
match. This second template is an exploratory fix, not a validated combined
detector. It was chosen after seeing the red misses, so even its subsequent
full-excerpt result remains same-recording development evidence.

### Red candidate-window transfer

The red template was then frozen and run with a **red** handle-colour check
over 26-second windows after *all nine* provisional red crossing candidates.
The [coverage summary](latvia24-full-v1/early-highres-red-candidate-window-summary-development.json)
pins the nine individual source-hashed window ledgers and the
[runner](../../../../prototype/scripts/scan_latvia_red_candidate_window.py).
Six windows have an upward image path. The
[source sheet](latvia24-full-v1/early-highres-red-upward-source-review.jpg)
and [review manifest](latvia24-full-v1/early-highres-red-upward-source-review.json)
show a moving red stone at the start of all six paths. One of the six is the
1991-s event used to choose the red template; **five other red candidate
windows** provide same-match development transfer evidence. Three red
windows (S40, S42 and S45) have no supported upward path.

This is not six verified complete red trajectories. In the longer S49 path,
the tracker may continue on a parked stone; the late identities of S59 and
S65 are also unverified. Nearest-neighbour linkage
cannot yet establish when the delivered stone settled or which physical stone
occupies the board afterward. This window-only pass was restricted to
prediction-selected windows, so it cannot measure false positives over the
whole recording or independent event F1. A combined red/yellow proposal lane
still needs cross-recording testing.

### Full red-excerpt scan and motion-only windows

The frozen red lane was subsequently run at 1 Hz over **all 1110 seconds** of
the earlier excerpt, including time outside the selected windows. Its
[full-transfer ledger](latvia24-full-v1/early-highres-red-full-transfer-development.json)
verifies 15 nonoverlapping source-hashed shards. A shard/window overlap was
checked proposal-for-proposal. The scan produces **2228 grey-body proposals**,
of which **1278** pass the red-handle check. Temporal linking retains six
upward and two downward image paths. All six upward starts fall within
25 seconds of distinct provisional red candidates; there is no additional
upward start outside those candidate windows under this frozen rule. Their
moving prefixes are the same six source-reviewed red stones above. This
same-recording, postfailure development result is not a false-positive rate
or event F1; the three unassociated red candidate windows remain unverified.

Raw path endpoints can badly overstate a throw's duration: one linked red
path runs from 1988 to **2087 s**, another from 2363 to **2503 s**, and a
third from 2688 to **2759 s** because still image boxes continue to match.
The [motion-only sidecar](latvia24-full-v1/early-highres-red-motion-windows-development.json)
therefore records the observed moving prefix separately. Three paths have
tentative one-second *image-stillness* brackets at **2000–2001**, **2369–2370**
and **2693–2694 s**, each confirmed by three subsequent one-second steps of
at most 4 px. The other three paths are explicitly right-censored before any
visual stop is observed. These brackets are not physical stop times: a
nearest-neighbour link may have switched to a parked stone, so the same-stone
identity and post-throw board remain unverified. The
[rule](../../../../prototype/red_motion_window.py) has targeted tests for
stillness, resumed motion and sampling gaps.

Two provisional yellow candidates (1661 and 1799 s) also lack an associated
upward body/handle path under the frozen rule. Single-frame source examples
cannot distinguish a detector miss from a camera/occlusion or candidate-timing
problem. The next transfer test should merge the two colour-conditioned
proposal lanes with identity-aware tracking, examine their behaviour on the
later blind interval, then test an untouched recording with independent
throw labels.
No throw F1, physical board reconstruction or simulation-ready state is
claimed from this development excerpt.

The source-reviewed moving prefixes are attached, without changing any
physical game-state claim, in the [full-match receiving-motion handoff](LATVIA-RECEIVING-MOTION-HANDOFF.md).
