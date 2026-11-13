# Faster bidirectional right-view proposal probe

An Italy source check found a missed red stone moving **toward larger right-image y**, from about y=211 to y=322 in four seconds. The prior right-entry rule required smaller y, and the frozen 1 Hz track linker permitted at most 25 pixels per second between observations. At 25 px/s the source window emits no sustained red track; at 40 px/s with consecutive samples it yields a moving path. The [source review sheet](right-entry-transfer/italy-bidirectional-fast-source-review/sheet-01.jpg) includes this case as B001.

The separate [bidirectional probe](../../../../prototype/scripts/probe_right_bidirectional_spans.py) keeps the same 360p colour proposals, samples every second, links consecutive same-colour detections up to 40 px apart, and creates a review proposal after ≥60 px vertical motion in either image direction. The reported time is the observed halfway span, not release or a fixed rink line. The 40 px limit and two-direction rule were chosen **after** inspecting Italy, so all results below are exposed development evidence, not a frozen transfer score. The old y=235 outputs are unchanged.

| 1650–2760 s recording | Bidirectional raw tracks | Review paths, negative/positive y | New same-colour coarse windows | Coarse windows still without old or new path |
| --- | ---: | ---: | --- | ---: |
| [Italy](right-entry-transfer/italy-bidirectional-fast-development.json) | 33 | 13: 12/1 | I01, I09, I11, I13 | 3/17 |
| [Estonia](right-entry-transfer/estonia-bidirectional-fast-development.json) | 31 | 12: 10/2 | E04, E11, E14, E16 | 4/17 |
| [China](right-entry-transfer/china-bidirectional-fast-development.json) | 50 | 16: 14/2 | C03, C10, C11, C12, C17 | 3/18 |

The [source-strip manifests](right-entry-transfer/italy-bidirectional-fast-source-review/manifest.json), [Estonia](right-entry-transfer/estonia-bidirectional-fast-source-review/manifest.json) and [China](right-entry-transfer/china-bidirectional-fast-source-review/manifest.json) select **every** proposal in a newly covered window and every proposal outside all same-colour windows. The [source-class audit](right-entry-transfer/bidirectional-fast-source-audit.json) verifies the probe and strip hashes and records the same-agent visual result:

| Selected proposals | Short moving-stone paths | People / wheelchairs / clothing |
| --- | ---: | ---: |
| In 13 newly covered coarse windows | 12 | 1 (China C03, B014) |
| Outside all coarse windows | 0 | 2 (Estonia B031; China B015) |

Thus the new tier surfaces 12 additional source-visible moving-stone paths, including Italy's downward-moving I01 and Estonia's E04, but its China C03 time/colour match is a **nonstone**. Two other person paths show why the high-recall tier requires a later object-identity filter. Existing 29 variant-covered windows plus these 12 stone-path windows give **41 of 52 coarse windows with a short right-view stone path** in sampled source evidence; 11 have no such path demonstrated here. This is not event recall: the broad windows came from five-second stills, source review was performed by the detector developer, some visible stones may not be the delivered stone, and no physical-delivery denominator is certified.

No newly found path is promoted to an accepted throw. The next filter must distinguish a moving cap on ice from clothing, wheelchair parts and player motion while preserving one-view review candidates during left-camera gaps. An independent complete-end score remains necessary for precision, recall and F1.
