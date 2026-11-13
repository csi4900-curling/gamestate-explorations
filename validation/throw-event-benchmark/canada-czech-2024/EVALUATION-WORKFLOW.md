# Independent throw-only evaluation workflow

The frozen detector output for this interval predates the [blind packet](blind-throw-review/README.md). The packet contains only an aligned 18.5-minute video, instructions and a throw-interval annotation page. Give **only that directory** to a teammate who has not seen the candidate list or this report. A prior-exposure note is required if they have seen the clip. The page asks them to watch every minute and mark broad intentional-delivery intervals; it does not require board labels, exact release frames or curling strategy judgements.

This is the smallest complete-coverage review for the fixed interval. Candidate-only checks could estimate precision but would miss unproposed throws, so they cannot support recall or F1. The reviewer can use 2× playback and resume later. Mark unclear possible deliveries as uncertain; the scorer will withhold full-interval F1 if any remain uncertain rather than guessing.

After the reviewer exports `blind-throw-labels-draft.json`, preserve it unchanged and run:

```sh
feasibility/scripts/python.sh prototype/scripts/score_blind_throw_interval.py seal \
  --draft /path/to/blind-throw-labels-draft.json \
  --packet validation/throw-event-benchmark/canada-czech-2024/blind-throw-review/packet.json \
  --video validation/throw-event-benchmark/canada-czech-2024/blind-throw-review/video.mp4 \
  --output /path/to/blind-throw-labels-v1.sealed.json
feasibility/scripts/python.sh prototype/scripts/score_blind_throw_interval.py score \
  --seal /path/to/blind-throw-labels-v1.sealed.json \
  --draft /path/to/blind-throw-labels-draft.json \
  --packet validation/throw-event-benchmark/canada-czech-2024/blind-throw-review/packet.json \
  --screen validation/throw-event-benchmark/canada-czech-2024/conditional-dropout-screen-frozen-first.json \
  --alignment validation/throw-event-benchmark/canada-czech-2024/highres-alignment-frozen-first.json \
  --verification validation/throw-event-benchmark/canada-czech-2024/verification-frozen-first.json \
  --output /path/to/throw-event-score-v1.json
```

The scorer requires every minute marked reviewed, valid nonoverlapping intervals, the exact video fingerprint, the six-checkpoint source alignment, and the frozen screen fingerprint. It matches proposals one-to-one when their passage timestamp lies **inside** a human delivery interval, with no extra tolerance. Unmatched certain deliveries are false negatives; extra proposals are false positives. Colour is scored only where the reviewer identifies it. Uncertain deliveries quarantine predictions in their interval and suppress full-interval precision, recall and F1. Broad interval matching assesses event detection, not release or settle timing.

This packet is a **single same-production interval**. Even a complete independent score would be a pilot, not evidence of robustness across different broadcast layouts or complete matches. No labels have been supplied or scored yet.
