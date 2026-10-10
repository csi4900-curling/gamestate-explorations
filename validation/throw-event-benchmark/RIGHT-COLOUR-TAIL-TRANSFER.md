# One-frame right-cap continuation transfer

The Latvia [field-of-view audit](canada-latvia-2024/END6-FIELD-OF-VIEW-RESULTS.md) found source-visible colour pixels after short right-camera paths ended. To check whether a simple continuation cue transfers, a fixed one-frame HSV screen was applied to the saved 360p right-cap paths on Canada–Italy and Canada–Estonia 2024, using their synchronized 1080p excerpts. The 360p cap centers were scaled by three; the last one-second image step predicted the next cap center. The screen retained exactly one component within 30 high-resolution pixels and 200–3500 coloured pixels, otherwise abstaining. This is a **cap-seeded transfer**, not an unchanged replay of Latvia's body-centered seed.

| Recording | Reviewed moving-stone paths with a unique next-frame colour component | Identity-uncertain stone-pixel paths | Reviewed person/wheelchair paths with a unique component |
| --- | ---: | ---: | ---: |
| [Italy](canada-italy/right-colour-tail-screen-transfer.json) | 13/13 | 2/2 | 1/2 |
| [Estonia](canada-estonia-2024/right-colour-tail-screen-transfer.json) | 12/12 | 4/4 | 1/1 |

The four fixed source-time pairs used to align each 1080p excerpt with its 360p recording have resized-frame correlations of **0.9959–0.9987**. Both outputs record the video, proposal, source-review, rule-code and runner hashes, per-path predicted centers and candidate pixels. The source classes were assigned by the detector developer on exposed recordings; these fractions are **not** independent event recall or precision.

The result is useful for observed-pixel continuity: the next frame contains an apparently compatible same-colour component for all 25 reviewed moving-stone paths. It also reveals a sharp limit: **two of three person/wheelchair paths pass the same screen**. The accepted Italy A007 and Estonia A045 examples are person-associated red-pixel paths in the source frames. A one-frame colour continuation must therefore remain supporting evidence; it cannot confirm a physical throw or resolve a long track's same-stone identity. None of these screens supplies the trajectory after a camera exit, settle time, complete board, or simulation input.

The previously saved paired ice-context screens flag both A007 and A045 as cluttered, illustrating why that separate cue is still useful. It is not a safe universal hard veto either: Estonia A003 and A040 have identity-uncertain stone pixels and also score cluttered. Combining these cues as review evidence is more honest than treating either as a verified stone/throw classifier.

Reproduce with [`transfer_right_colour_tail_screen.py`](../../prototype/scripts/transfer_right_colour_tail_screen.py), passing the recording's frozen area-aware probe, matching source-review JSON, full 360p source and synchronized `source-1080p-1650-2760.mp4` excerpt. The runner refuses overwrite and checks all 34 reviewed proposal IDs across the two outputs through each recording's saved probe/review pair.
