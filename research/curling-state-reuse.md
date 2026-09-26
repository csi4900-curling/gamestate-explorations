# Curling state representation: reuse investigation

Investigated 2026-09-23. This is an architecture recommendation based on source and specification inspection, not an integration benchmark.

## Follow-up findings

The [HTML field guide](curling-landscape.html) extends this investigation with robustness and Rust-port assessments. It adds **[PCN — Portable Curling Notation](https://github.com/shinagaki/pcn)**, an unofficial draft with a grammar, JSON schema, tee-centred metre coordinates and mixed-doubles examples. Evaluate it as a match archive/export alongside DC4, while keeping incomplete camera observations separate. Inspected commit: `04511910a5e705d2f4931a66fd5e10027d4451bf`; specification by Shintaro Inagaki, CC BY 4.0; code MIT.

DC4's physics boundary calls **[FCV1](https://github.com/kr-work/FCV1-Simulator)**, a native C++/Box2D module exposed through pybind11. Inspected commit: `b70f6b4982ea38fbe3fa91289ad4061b267d863e`. A Rust rewrite of the Python server does not automatically speed up this physics loop. A narrow state/rules/adapter library is the preferred initial Rust scope, subject to differential and independent correctness checks.

Executed DC4's `test_match_rules.py`, `test_scoring_rules.py`, and `test_simulation.py`: **18 passed**, using Python 3.11, NumPy 1.26.4, pytest 9.0.2 and Pydantic 2.10.3. These cover pure rules and spin conventions; they do not establish real-world physics fidelity or production-service robustness. [Test output](evidence/dc4-focused-tests.txt).

## Decision

Reuse existing curling concepts and target Digital Curling 4 (DC4) for simulator interoperability. Add a small video-observation model for evidence, incomplete visibility, and uncertain identity. Do not force every video frame into a complete simulator state, and do not invent a new curling rules engine.

The existing playbook's literal `GAMESTATE {ShotNum, CurEnd, LastEnd, Score[10], WhiteToMove, body[16][2]}` should be treated as a legacy representation, not the current DC3/DC4 contract. Pin the chosen implementation and write an explicit adapter.

## Existing work

| Project/specification | What exists | Recommended use |
| --- | --- | --- |
| [Digital Curling 4 server](https://github.com/digitalcurling/DigitalCurling4-Server) | Python/Pydantic match and state models; team coordinates, end/shot counters, scores, next team, mixed-doubles settings; standard and mixed-doubles rules | Main interoperability target; reuse established semantics and inspect reusable rule functions |
| [DC4 Python client](https://github.com/kr-work/DC4-Python) | Typed received-state schemas and coordinate accessors | Reference for adapter validation; no need to run the full server merely to define observations |
| [Digital Curling 3](https://github.com/digitalcurling/DigitalCurling3) | C++ JSON-serializable game state, hammer, scores, shot/end, optional stone slots | Useful predecessor, but do not mix its schema with DC4 or the older playbook example |
| [Curlovision](https://github.com/jdumm/curlovision) | Broadcast footage to `MatchResult → EndResult → StoneLayout → Stone`; ring/stone detection, scoreboard reading, scoring, rendering | Closest existing pipeline baseline and object-model precedent |
| [CurlR](https://github.com/ritchi12/CurlR) | Results-book shot metadata and wide per-colour coordinate tables, including mixed-doubles pre-positioned stones | Existing reference-data importer; retain original diagram coordinates and provenance |
| [Olympic Data Feed curling dictionary](https://odf.olympictech.org/2026-MiCo/OG/PDF/OWG2026_CUR_Data_Dictionary.pdf) | Formal match, end, shot/action, task, turn, score, team/player vocabulary; shot board supplied as image data | Reuse metadata semantics; it does not supply a metric stone-position array in the inspected play-by-play specification |
| [IPTC SportsML 3 curling schema](https://www.iptc.org/std/SportsML/3.0/documentation/sportsml-specific-curling_xsd.html) | Curling statistics and events, stone colour/number, hammer and throw information | Vocabulary reference, not a complete spatial observation format |
| [CurlObserver dataset](https://github.com/CurlObserver/dataset) | Detection boxes, segmentation/OBB labels and tracking IDs | Perception training/evaluation data; not a complete game-state schema |

### Digital Curling details that affect compatibility

Inspected DC4 server commit `ec06aae5b4f78d9037af645244b0f062ded94c51`, DC4 Python client `06e9517fa80d818e5afa9e4bad26fdb072172d8e`, and DC3 commit `bc62fe3d0b0fae3672f8a53aff8458fdfd391c22`. DC4 server and Python client carry MIT licences.

- [DC4 models](https://github.com/digitalcurling/DigitalCurling4-Server/blob/ec06aae5b4f78d9037af645244b0f062ded94c51/src/models/dc_models.py) separate match metadata from state. State includes end and shot counters, next team, scores, stone coordinates, timing fields, last move, and optional mixed-doubles settings. It does not attach visibility, uncertainty, or video evidence to individual stones.
- `team0` is the first attacking team in the first end, not a colour and not necessarily the first team in every end. Preserve team identity and colour as separate concepts.
- [DC4 rule code](https://github.com/digitalcurling/DigitalCurling4-Server/blob/ec06aae5b4f78d9037af645244b0f062ded94c51/src/domain/match_rules.py) uses metres, with the target tee at `(0, 38.405)`. It uses `(0, 0)` for unused/absent slots. Never interpret that sentinel as a stone on the button.
- Standard curling has 16 delivered stones per end; mixed doubles has 10 plus two pre-positioned stones. Mixed-doubles arrays may be padded for simulator compatibility; avoid assuming every returned list has exactly six entries.
- The inspected mixed-doubles placement code includes 2026–27 rules. Our 2018 footage needs an explicit historical rules version rather than silently adopting those placements.
- DC3 uses optional stone slots, where absence from the board is different from a video observation that cannot see the stone.

### Curlovision is direct prior art

Inspected commit `8965fb3c7380e39234c5b26ff45b981aac063c80`. Its `Stone` holds `x`, `y`, radius and colour; coordinates are tee-centred feet. Layouts are grouped into ends and matches, and scoreboard state supplies contextual information. This is already a video-to-intermediate-state architecture.

It is an older, tournament-dependent implementation, originally targeting Python 3.6. Its layout ordering can be sorted by distance to the button, so list position is not a persistent stone identity. Detection and scoreboard failures remain relevant. We have not reproduced its accuracy claims. The repository states BSD licensing but does not provide a full standard BSD licence text; inspect that before substantial code incorporation.

### Official diagrams are still observations

The 2026 Olympic dictionary's play-by-play section (2.3.7) provides stone number, task, turn, points and participants, with a base64 PNG board image. It is useful structured metadata, but diagram-to-coordinate extraction remains necessary. CurlR coordinates likewise come from diagrams and must not be relabelled as surveyed physical ground truth.

[Jordan Myslik's curling analytics project](https://jordanmyslik.com/portfolio/curling-analytics) also uses an events/games/ends/shots/stone-positions hierarchy; its positions are diagram pixels. [NWNHT's curling work](https://nwnht.ca/projects/curling/curling.html) distinguishes throws from position snapshots, which is useful for pre-positioned stones and multiple observations of the same board.

## Minimal project-specific extension

Use three concepts:

1. **Board observation:** video/frame/time, calibration reference, coordinate convention, visible stone observations, visibility/completeness and measured uncertainty where available. Observation IDs can be frame-local. Team and delivery identity can remain unknown.
2. **Game snapshot:** a reconciled board plus supported match/end/shot/score/hammer context. Multiple camera frames can describe the same snapshot; the pre-positioned mixed-doubles board exists before a throw.
3. **Adapters:** CurlR/result-book import and DC4 export. A simulator-ready export requires enough information to populate the relevant contract; missing clocks or identities must not be invented.

Use tee-centred metres for calibrated CV observations with explicit axes. If positive observation y points toward the throwing hack and x matches DC4, the adapter is `x_dc4 = x_obs`, `y_dc4 = 38.405 - y_obs`. Check orientation rather than assuming a shared axis direction.

Keep these distinctions explicit:

- Not visible versus known out of play versus not yet delivered.
- A detected stone versus a confidently identified delivery/track.
- Measured uncertainty versus an uncalibrated detector score; leave uncertainty unknown when not estimated.
- Observed position versus inferred position, with source evidence for both.
- Complete board versus a house-only crop that may exclude guards.
- Physical coordinates versus diagram pixels, with each transformation recorded.

## Recommended next implementation

Convert the existing feasibility annotations into this small observation format first. Add a renderer and coordinate adapter, and round-trip one sufficiently known mixed-doubles snapshot through the pinned DC4 coordinate/state conventions. Check that colours, stone counts, pre-positioned stones, position and scoring agree. Explicitly reject or preserve incompleteness for partial views rather than filling in invisible stones.

Then evaluate the same representation on another match before building broad automatic extraction. The research contribution should be reliable extraction, uncertainty handling and validation across broadcasts; the general video-to-curling-state idea already has prior art.
