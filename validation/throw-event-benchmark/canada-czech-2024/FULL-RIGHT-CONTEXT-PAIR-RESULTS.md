# Full right-camera context diagnostic

The [prerun plan](FULL-RIGHT-CONTEXT-PAIR-PLAN.json) fixed the previously implemented ice-ring and underpoint features, the 0.25 review threshold, and the 131-proposal full-match right inventory. The [source-scored output](full-right-context-pair-postscan.json) covers every proposal in that inventory and retains its cross-view episode link. This is a **same-source diagnostic**: Czechia contributed to earlier feature development, and the two highest-scoring right-only appearance tracks were visually inspected before this run. The tiers are not independent stone, delivery, or non-delivery labels.

| Cross-view proposal category | Clear context | Cluttered context | Insufficient samples | Total |
| --- | ---: | ---: | ---: | ---: |
| One-to-one temporal candidate | 90 | 1 | 0 | 91 |
| Multiple-right ambiguous group | 2 | 13 | 0 | 15 |
| Shared-one-right ambiguous group | 2 | 0 | 0 | 2 |
| Right-only proposal | 0 | 22 | 1 | 23 |
| **Total** | **94** | **36** | **1** | **131** |

The [targeted source review](full-corridor-right-only-top-patch-review/source-review.json) identified right-only tracks R01:A035 and R01:A100 as a player's head and hat/clothing even though all three isolated appearance patches scored positive. Both are cluttered by the unchanged context pair: A035 has median non-ice ring/underpoint fractions **0.2929/0.7941**; A100 has **0.4772/0.9158**. This adds a physically relevant explanation for those two errors: material continues below the tracked colour cap where an isolated stone would usually have ice.

The single cluttered one-to-one match is R01:A376 linked to S144 at the postgame tail; the existing provisional screen had already withheld S144 as a duplicate of S143. Right-only R01:A235 has only two distinct tracked frames and remains explicitly unscored. Clear-context ambiguous tracks R01:A029 and R01:A030 remain ambiguous cross-view matches; a clean-looking background does not choose one physical identity.

The result supports using the two cues to **prioritize review**, while preserving all 131 proposals and all 133 episodes. It does not justify deleting the 22 cluttered right-only proposals: a real stone can pass close to a player, broom, painted house or camera crop. The only available source classes are limited same-agent reviews, and no exhaustive independent physical-throw reference exists for this full match. Event precision, recall and F1, complete boards, and simulation-ready state remain unmeasured.
