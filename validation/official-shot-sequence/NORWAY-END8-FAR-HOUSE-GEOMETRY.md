# Norway end eight: far-house coordinate discrepancy

The [source-frame review](norway-end8-far-house-source-frames.jpg) shows visually stable boards in the earliest scoreable views for official shots E08-S10 through E08-S13. These are the four candidates that introduced six unmatched observed stones in the 90-second board-window sensitivity pass. The [frozen residual audit](norway-end8-far-house-residual-audit-first.json) pairs same-colour source observations with PDF diagram symbols for those four development cases, without changing the source-only detector or choosing a different window.

| Diagram-symbol range | Paired observations | Mean absolute longitudinal discrepancy | Mean signed video-minus-PDF discrepancy |
|---|---:|---:|---:|
| More than 1.5 house radii above the house centre | 9 | 0.2258 house radii | −0.2258 house radii |
| Within 1.25 house radii of the centre | 10 | 0.0419 house radii | +0.0258 house radii |

The far stones repeatedly appear farther toward image top in the video coordinates than in the independent PDF diagrams, while stones near the house are closer. Several far residuals exceed the comparator's 0.25-house-radius match gate. Thus the six unmatched entries do **not** by themselves show that the longer window contains a later throw or that the detector missed those stones: the source frames visibly contain the expected colours and the mismatch is concentrated by range. A one-radius image normalization, perspective, cap-height parallax, diagram quantization, and imperfect event association are possible contributors; this audit does not isolate their effects or establish centimetre accuracy.

This is **localized, not a general far-range failure** in the comparable Norway boards. A separate [22-candidate countercheck](norway-all-range-residual-countercheck-first.json) selected each candidate's earliest camera group by source time and retained cases with equal per-colour video/PDF stone counts. Its 40 far pairs average `0.0773` house radii absolute longitudinal difference, versus `0.0735` for 58 near pairs. Within that selected set, the 10 eighth-end far pairs average `0.2228`; the other 30 far pairs average `0.0288`. This favourable-count subset is not an accuracy evaluation, but it argues against applying a global far-distance correction learned from the four eighth-end cases.

The four diagrams reuse some of the same stones across consecutive shots, so 9 far pairs are **not nine independent physical accuracy measurements**. The cases were selected after seeing the mismatches, not as a blind validation set. Before using these positions for a 3D replay, the project needs a source-calibrated rink mapping and ground-contact localization validated at multiple distances, independent of the PDF positions used here for diagnosis.

Reproduce after moving the frozen JSON and image aside with `feasibility/scripts/python.sh prototype/scripts/audit_norway_end8_far_geometry.py`; run `feasibility/scripts/python.sh prototype/scripts/audit_norway_all_range_residuals.py` for the broader countercheck. The artifacts record hashes of their source video, board scan, PDF diagrams, runners, and contact sheet.
