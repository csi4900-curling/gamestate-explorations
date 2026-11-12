# Revolution probe — 12 November 2026 (development)

Status: research probe on one inspected development interval (NOR–CZE 0–840 s,
job `f0c81a6900b8`). Nothing here is wired into the workbench, and nothing here
is a validated physical revolution count.

## What was found

1. **The handle is resolvable in the sending view.** After normalising each
   stone crop by its box, the gooseneck handle is clearly visible for about
   4.5–6 s after release (`L00008-left-appearance-v1/zoom.jpg`). Successive
   side-on views are mirrored, so one appearance cycle is one full turn.
2. **The 30 fps stream has a 5 Hz judder** (repeated frames from a slower
   source). Unregistered crops are dominated by it. Registering every crop on
   the cap rim and granite band removes it (`appearance_phase.py`, v2 vs v3).
3. **Full-turn period from crop self-similarity** (`period_probe.py`). The mean
   correlation between crops separated by a lag shows a weak bump at the half
   turn and a strong peak at the full turn. On the ten detected throws, eight
   sending-view intervals give a clear full-turn peak (2.87–4.67 s per turn) and
   two are too short and are inferred as twice the half-turn bump. Results:
   `nor-cze-period-probe-v3.json` and `.png`.
4. **Receiving view is not supported yet.** One of eight receiving intervals
   gives a clear peak (L00009: 3.2 s against 2.87 s in the sending view). The
   rest are weak or multi-peaked and are reported as no estimate.

## What did not work (preserved)

- `handle_phase.py`: second moments of the colour mask. The cap dominates.
- `spin_estimate.py`: colour-centroid loop with a harmonic rate fit (locks onto
  harmonics with about 1.4 cycles of data) and with a bounded ellipse fit (the
  centroid path is not a stable loop). Outputs `nor-cze-spin-probe-v1..v3`.

## Limits

- Only the period over the analysed interval is measured, under a constant-rate
  assumption inside that interval. About 1.2–1.7 turns are actually observed per
  throw in the sending view.
- The sense of rotation is not determined.
- A whole-throw count would need the receiving view or an explicit, separately
  labelled extrapolation. No such count is reported.
- Checked by the developing agent against one throw's crops (L00008, about 3 s
  per turn by eye). No independent turn counts exist yet. Thresholds
  (`FULL_TURN_MINIMUM`, crop geometry, window offsets) were chosen on these ten
  throws and are development settings.

## Next

Independent by-eye turn counts from `prototype/source_label_tool.html` on these
throws, then direction and the receiving view, then a held-out recording.
