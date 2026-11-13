# Shot-scoped release-cue audit

The [machine-readable ledger](pwg2022-shot-scoped-release-cues-development.json) checks every provisional event's release cue against the declared camera-shot interval. It keeps the original source-only held-to-motion scan for visual-origin and held-origin candidates whose windows fit inside one shot. For travel-only candidates, it uses a separately rescanned attached held-origin shot if one exists; otherwise it abstains. The rescan uses the same cue rule and source video.

| Recording | Provisional candidates | Original unique cues | Shot-scoped unique cues | Travel candidates without origin shot |
| --- | ---: | ---: | ---: | ---: |
| Switzerland | 117 | 46 | 45 | 2 |
| China | 123 | 31 | 32 | 8 |
| Slovakia | 116 | 34 | 34 | 0 |
| **Total** | **356** | **111** | **111** | **10** |

The unchanged aggregate of 111 hides two changed decisions. Swiss `TRAVEL-B48` loses the broad-window cue at 3121.4 s because it is in shot S243 while the event declares S244 and has no attached origin shot. China `TRAVEL-B57` gains a unique red cue at 3459.8 s when its attached held-origin shot S278 is rescanned within that shot. The broad B57 window contained two red passages across camera views and had abstained. China `TRAVEL-B56` retains its yellow cue in attached shot S274. No passage in the 111 accepted cases crosses the declared shot boundary.

This is a scope and provenance correction to **candidate cue coverage**, not a physical throw-event F1 measurement. The event windows were selected by the provisional system, and most source views still lack a unique release cue. A cue in an origin shot does not prove that the same stone appears after a broadcast cut or in a later board. The [release-to-board audit](PWG2022-RELEASE-BOARD-COVERAGE.md) keeps that distinction explicit.

Run `python prototype/scripts/audit_pwg2022_shot_scoped_release.py` from the project root to reproduce the ledger from hashed inputs. The three selection-rule tests are in `prototype/tests/test_shot_scoped_release.py`.
