# Full China cap-track quality audit

The [pre-run plan](china-cap-track-quality-full-plan.json) fixes the 102 camera windows already marked cap-corroborated by the frozen full-match China pipeline, the source and model hashes, and all diagnostic thresholds. It uses no counter or official shot to select windows. The [first source-only output](china-cap-track-quality-full-first.json) was run across every planned window; 42 windows have unknown visual colour and abstain without rescanning.

The first audit used a second tracker with a looser association speed to recover raw points from the frozen short-transit summaries. Eight transits could not be linked back exactly, creating **audit-only abstentions**. We kept that result, then froze an [exact-replay v2 plan](china-cap-track-quality-full-v2-plan.json) using the same 102 windows and thresholds. The [corrected first output](china-cap-track-quality-full-v2-first.json) replays the frozen short-transit association rule and retains its actual points. All 102 transit summaries match v1 exactly; the eight artificial link abstentions disappear. Neither the original event candidates nor the frozen short-transit implementation changed.

For each of the 60 known-colour windows, the diagnostic searches accepted stone-cap patches at 5 Hz and checks its top short transit. A combined cue needs at least three track steps of 5 px, no single step above 70% of the path, and a reliable approximately one-second background registration with more than 10 px residual stone motion. A missing track link or camera registration is an abstention. These thresholds came from the earlier selected Norway/Swiss/China failure study and are **not calibrated to physical throw labels**.

| Outcome | Windows |
| --- | ---: |
| Combined cue supported | 15 |
| Weak track continuity | 9 |
| Weak camera-relative motion | 11 |
| No reliable camera pair | 16 |
| No short transit | 9 |
| Unknown visual colour | 42 |
| **Total** | **102** |

The separate [corrected postscore overlap](china-cap-track-quality-overlap-v2-postscore.json) compares these source-only categories with the existing delayed-counter associations. Of **43 known-colour windows associated with a counter**, only **12** have combined support. A hard gate would therefore remove **31** already counter-associated windows from that candidate path. Some may still be genuine throws whose delivered stone was missed by the top local transit; the audit cannot determine which. Counter association itself requires same-colour motion in adjacent shots, so this is a pipeline coverage check, **not independent event recall, precision or F1**. The [v1 overlap](china-cap-track-quality-overlap-postscore.json) remains available for the audit trail.

The result rejects promotion of the combined cue as a mandatory event filter. It may serve as positive corroboration when present, with weak and unscorable cases kept explicit. The China recording was exposed before this study, and neither the event ledger nor any frozen first-transfer output was modified. The source-only and postscore artifacts reproduce exactly from their runners and hashed inputs. Full-match physical event scoring still requires exhaustive independent labels or a trustworthy equivalent reference.
