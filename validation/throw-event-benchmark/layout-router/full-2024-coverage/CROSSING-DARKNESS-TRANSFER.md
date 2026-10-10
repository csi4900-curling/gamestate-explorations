# Crossing darkness: a failed source-view transfer

The Latvia source-pixel review suggested a cheap way to distinguish a small
stone from a player at a tracked left-view crossing: count grayscale pixels
below 140 in a 32×50 px patch extending downward from the crossing point in
the 640×360 source. The four reviewed Latvia stone pixels score 0.042–0.047;
the three reviewed player pixels score 0.366–0.606. A cut at 0.20 would
separate these **selected** cases. The cut was then held fixed for the existing
Scotland bridge source review.

| Selected source crossings | Below 0.20 (would keep) | At least 0.20 (would veto) |
| --- | ---: | ---: |
| Latvia visible stone body | 4 | 0 |
| Latvia person/head | 0 | 3 |
| Scotland visible stone body | **1** | **4** |
| Scotland visible non-stone object | **1** | **3** |
| Scotland identity uncertain | 0 | 1 |

This is a **negative transfer result**. The seemingly clean Latvia split does
not survive another broadcast: a hard cut would veto four of Scotland's five
reviewed visible stones and still keep one reviewed wheelchair-hardware
crossing. The exact per-case scores, coordinates, timestamps, source/input
hashes and method are in
[`CROSSING-DARKNESS-TRANSFER.json`](CROSSING-DARKNESS-TRANSFER.json), generated
by [`audit_crossing_darkness_transfer.py`](../../../../prototype/scripts/audit_crossing_darkness_transfer.py).

The cases were selected from detector output and reviewed by the development
agent. A visible stone at the crossing does not prove a physical delivery,
and these cases cannot yield event precision or recall. Darkness measures
background, occlusion and camera appearance as well as the object. The cue is
**not** added to the throw filter. A later verifier needs an appearance or
motion feature that transfers across source views, evaluated on independent,
complete-interval labels before it can veto events.
