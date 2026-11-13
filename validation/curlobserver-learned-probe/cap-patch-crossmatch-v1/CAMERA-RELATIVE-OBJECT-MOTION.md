# Stone appearance versus motion relative to the ice

The [non-origin fallback](NONORIGIN-CONTINUITY.md) emitted four candidates in the Sweden–Switzerland recording. To diagnose whether those were stone objects or colour motion from people and camera pans, we rescanned those four camera shots and the Norway `S465` miss at 5 Hz with the frozen broadcast cap-patch model. This was a **selected, postscore diagnostic**, not a transfer or event validation.

The [cap-object audit](nonorigin-cap-object-audit-development.json) shows why patch appearance alone is insufficient. Norway `S465` has a six-point red cap transit over 91 px, and Swiss `S171` a 51-point red transit over 140 px. Swiss `S404`, which shows the house during a camera move, also has a convincing 17-point yellow cap transit over 118 px with median patch score 0.875. An old stone can look real while appearing to move in image coordinates because the camera moves.

We linked the accepted cap samples into local tracks and compared each approximately one-second movement with a robust image registration of the background. The reproducible [camera-relative audit](nonorigin-camera-relative-audit-development.json) reports:

| Camera shot | Reliable registered pairs | Pairs with residual motion >10 px | Largest reliable residual | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Norway `S465`, red | 1/1 | 1 | 87.0 px | Strong stone-like movement relative to the image background. |
| Swiss `S171`, red | 23/23 | 1 | 84.2 px | Long hold followed by a brief moving phase. |
| Swiss `S322`, red | 0/3 | 0 measurable | Unknown | Registration failed; must abstain. |
| Swiss `S404`, yellow | 6/6 | 0 | 7.3 px | Apparent stone travel is explained largely by camera motion. |
| Swiss `S566`, yellow | 0 pairs | 0 measurable | Unknown | Track too short for this one-second comparison. |

This is useful physical evidence but not a throw detector. A stationary old stone is separated from a moving stone in the selected `S404` comparison, while `S322` and `S566` remain unresolved. The analysis does not prove `S465` and `S171` are new deliveries, nor does it link a stone across cuts. Registration may fail on fast pans or cut frames. A general decision rule needs a broader, source-separated test with event labels and explicit abstention before promotion. The reserved independent source was not inspected.
