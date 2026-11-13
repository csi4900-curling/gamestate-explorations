# Full-recording provisional event review windows

The [segment export](pwg2022-full-match-event-review-segments-development.json) and [offline viewer](../../prototype/full-match-event-review/index.html) make every event in the [provisional union](PROVISIONAL-EVENT-EVIDENCE-UNION.md) inspectable against its source video. They cover **117 Swiss, 123 China and 116 Slovakia candidates**. Each evidence core spans the camera shots that supplied its event cues; a review window adds two seconds before and five seconds after that core. For a travel-only candidate with no held-origin cue, the immediately preceding shot is included only when no other candidate already owns it. This gives the reviewer context without assigning one shot to two events.

| Recording | Review windows | Windows containing proposed internal edits | Travel-only windows with an unoccupied preceding shot |
| --- | ---: | ---: | ---: |
| Sweden–Switzerland | 117 | 1 | 1 |
| Canada–China | 123 | 36 | 8 |
| Slovakia–USA | 116 | 7 | 0 |

For China B26, the review window is **1600.8–1634.4 s** and the evidence core is **1602.8–1629.4 s** (`S123` and `S124`). Proposed edits at 1606.0 and 1624.6 s are marked, while the yellow observed travel interval is 1611.8–1624.4 s. The actual release and physical settle times remain `null`. The clip is a useful 34-second meeting example: switch the viewer to Canada–China, search `B26`, and press **Play review window**. B57 spans `S278` and `S279`, carrying held and travel cues without a verified identity bridge.

The clips are **review windows, not validated throw segments**. They may include waiting, players, graphics or more than one physical action; neighboring review windows may overlap because of padding. Proposed internal edits are diagnostic candidates, not confirmed camera cuts. No physical release time, full trajectory, complete settled board, simulation-ready state or independent complete-match throw F1 is established by opening a clip.

Run `python prototype/scripts/export_2022_full_match_review_segments.py`, then `python prototype/scripts/build_full_match_event_review.py` from the repository root to verify the artifacts exactly against their recorded inputs. The HTML works locally with the source MP4 files in their existing project paths.
