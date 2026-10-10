# Norway camera-shot orientation from source motion

The [source-only motion audit](norway-motion-approach-orientation-cues-first.json) checks whether an exclusive motion track can identify the direction from which a stone approaches a detected house. It examines the 101 camera-shot groups with stable image-relative stones from the [full-match image board scan](norway-full-candidate-post-window-image-boards-v2.json). It uses no official diagrams to select a direction.

A track is eligible only when the candidate has a source-resolved colour, exactly one exclusive track of that colour falls in the same camera shot, its vertical travel exceeds 15 pixels, its endpoint is at least 15 pixels closer to the later detected house centre, and it ends by the start of repeated stable-board observations (with a two-second tolerance). The house centre comes from the source frame at the start of the board group. Camera motion and track identity still make this a **proposal**, not a verified physical throw direction.

| Audit outcome | Camera-shot groups |
|---|---:|
| Stable image-board groups examined | 101 |
| Source colour unknown | 27 |
| No unique exclusive same-colour track | 28 |
| Track fails approach/temporal rule | 39 |
| Approach-direction proposal | 7 |

Of seven proposals, four agree with the existing layout-side reading, none conflict, and three have no layout-side reading. The three newly constrained cases are **S33→S34**, **S281→S282**, and **S353→S354**, all proposing approach from image top. The S281 case is also supported by direct [source-frame review](norway-e04-s12-source-contact-sheet.jpg). In the S33 post-counter board, three observed source stones match three official E01-S04 symbols within the existing diagram threshold, while a fourth official symbol is not observed; that is retrospective corroboration, not independent validation.

The abstention is important. Among the 20 source-colour/unique-track groups whose layout reader says `top`, raw track endpoints travel at least 15 pixels down in only four, at least 15 pixels up in eight, and have weak vertical travel in eight. Merely using the sign of any linked track would frequently disagree with the view layout, likely because tracks can represent displaced or other stones and the camera can move. The strict rule has only four known-layout agreements, too little evidence to claim general accuracy or transfer across recordings.

Run `feasibility/scripts/python.sh prototype/scripts/audit_norway_motion_approach_orientation.py` after moving the frozen output aside. The artifact records source video, motion catalog, candidate links, image-board scan, detector, cue rule and runner hashes.
