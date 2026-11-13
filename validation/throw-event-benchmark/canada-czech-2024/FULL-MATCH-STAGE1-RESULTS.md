# Full-match stage-one span sweep (postscore development)

The [predeclared sweep](FULL-MATCH-STAGE1-PLAN.md) ran the unchanged 10 Hz early-ROI span detector over **0–6683 s** of the full 360p Canada–Czechia source. It sampled **66,830 frames** in **80.4 s** of recorded processing time and emitted **147 raw motion spans**. The unchanged fixed left-panel corridor retained **116** and withheld **31**. These are **candidate counts, not detected-throw counts**. No receiving-path/patch screen was run outside the frozen 1650–2760 s interval, and no full-match precision, recall or F1 is available.

The [machine audit](full-match-stage1-audit-postscore.json) verifies source and code hashes, candidate conservation, and the corridor partition. The full run's **24 candidates** in 1650–2760 s exactly reproduce the earlier interval's crossing times, colours, horizontal positions and corridor decisions. Only the first interval candidate has four onset/velocity fields that differ because its track began just before the local clip start; full-match S42 corresponds to interval S01. The remaining 23 match in all non-ID/non-track fields. This confirms the slice result was not created by a different rule or a changed camera sample origin.

| Observed displayed-end run | First–last marker sample (s) | Raw spans | In corridor | Withheld |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 120–810 | 26 | 22 | 4 |
| 2 | 830–1940 | 21 | 19 | 2 |
| 3 | 1970–3090 | 24 | 18 | 6 |
| 4 | 3120–4040 | 21 | 16 | 5 |
| 5 | 4060–5260 | 26 | 19 | 7 |
| 6 | 5320–6330 | 16 | 16 | 0 |

The six runs contain **134 raw candidates**; **13** lie outside them in marker gaps. The gaps include two candidates in the 1940–1970 end-2-to-3 graphic transition and **seven after the last end-6 marker** (6358.5–6396.9 s). Source frames checked at 6358.5, 6374.7, 6383.6 and 6396.9 s show stones being collected, athletes leaving, and the final 4–13 scoreboard. Frames at 6500 and 6600 s show empty ice. This is a clear postscore warning that the raw detector responds to non-throw movement after play; the full-match corridor still retains two of those late candidates. It is **not** an independently labelled false-positive count.

Displayed-end runs are broadcast graphic observations. Their first and last samples are not physical end boundaries, and comparing their candidate counts to 16 nominal deliveries per completed end would not measure recall or precision. In particular, the 116 corridor candidates include player motion and stone handling, while a true throw may be absent from the raw set. The full-match receiving-camera screen requires high-resolution source access or a redesigned lower-resolution tracker, plus independent event labels for validation.

Reproduce the sweep and audit from the project root using new output paths:

```sh
feasibility/scripts/python.sh prototype/scripts/run_span_probe.py \
  --video validation/throw-event-benchmark/canada-czech-2024/source-360p.mp4 \
  --source-id yu_YoFrFd20 --start 0 --end 6683 \
  --output /tmp/czech-full-stage1-raw.json
feasibility/scripts/python.sh prototype/scripts/screen_corridor.py \
  --events /tmp/czech-full-stage1-raw.json \
  --center-x-px 160 --half-width-px 60 \
  --output /tmp/czech-full-stage1-corridor.json
feasibility/scripts/python.sh prototype/scripts/audit_full_match_stage1.py \
  --video validation/throw-event-benchmark/canada-czech-2024/source-360p.mp4 \
  --full-raw /tmp/czech-full-stage1-raw.json \
  --full-corridor /tmp/czech-full-stage1-corridor.json \
  --interval-raw validation/throw-event-benchmark/canada-czech-2024/frozen-first-span-raw.json \
  --interval-corridor validation/throw-event-benchmark/canada-czech-2024/frozen-first-span-corridor.json \
  --marker-scan validation/throw-event-benchmark/canada-czech-2024/end-marker-full-postscore.json \
  --temporal-summary validation/throw-event-benchmark/canada-czech-2024/end-marker-temporal-summary-postscore.json \
  --output /tmp/czech-full-stage1-audit.json
```
