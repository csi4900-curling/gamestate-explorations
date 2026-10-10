# Canada–Estonia 2024, second source-first window

The SHA-selected 3000–3300 s window contains six deliveries in the one-second source-only left/right review. The reference and sheet-manifest hashes were frozen in `REFERENCE-FREEZE.json` before the saved full-match timeline was inspected for this interval. The timeline emitted six events in the window; all six matched distinct frozen delivery windows with the correct colour. The unchanged scorer reports **6 TP / 0 FP / 0 FN**, precision 1.00, recall 1.00, F1 1.00, with zero extra timing tolerance beyond each reference interval.

This is a source-first **development** check of five minutes, not independent or full-recording F1. The same agent reviewed source and develops the detector; one-second stills cannot certify that every short/occluded delivery was seen. The saved full timeline covers this window inside its `split_2024` supported run, but has gaps elsewhere. The timestamps are observed passage times within broad travel windows, not measured release times.

Inputs: `PLAN.md`, `source-first-reference.json`, `REFERENCE-FREEZE.json`, `frozen-predictions.json`; output: `source-first-score.json`.
