# Fixed global-assignment right-view development transfer

Before running the Estonia-E11-developed global colour-track assignment on Italy, freeze the full 640×360 source `source.mp4` SHA-256 `aff12e78edeb5e108d142aed3e19b61c3956b4fddc8b2fd8b202713746771739`, source interval 1650–2760 s, `right_global_area_tracks.py` SHA-256 `fd57618be239344c6d5e7795a3b0e97720fc7ccd5944791210a200b2cd848b9e`, and runner `probe_right_global_area_interval.py` SHA-256 `8279127b59c0b5ce32c77f07a9f112a93712b0cb86b1db41b97ee9301eaecea9`.

Keep 1 Hz sampling, the existing 2024 colour ROI, 40 px/s step bound, area-change weight 15, two-second observation gap, three-point/two-second raw support, later valid seed and 60-pixel bidirectional span. Render every proposed path and save source-pixel classes, including uncertain identity and person paths, **before** applying the unchanged 0.25 ring-or-underpoint context review tier. Report conditional overlap with the earlier 17-window coarse reference, any lost prior stone path and all context failures. Do not retune after this run.

This is a development transfer on a previously exposed recording, not independent physical throw validation or an accepted game-state output.
