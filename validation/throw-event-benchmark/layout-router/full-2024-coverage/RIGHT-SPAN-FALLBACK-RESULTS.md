# Line-free right-view motion-span development probe

The entry tier's y=235 line can miss a stone whose colour track first appears farther up the receiving image. A separate [line-free fallback](../../../../prototype/right_view_span_fallback.py) therefore replays the **preserved 1 Hz raw tracks** without changing either earlier entry rule: a new track must start with the same minimum cap area and width/height check, then move upward at least 60 image pixels within 20 seconds. Its reported passage is the observed halfway point of that span, **not** a fixed rink gate or release time. This is a postreview development rule.

| Exposed 1650–2760 s recording | Existing y=235 prefixes | New line-free prefixes | Newly covered same-colour coarse windows | Coarse windows still without either right prefix |
| --- | ---: | ---: | --- | ---: |
| [Italy](right-entry-transfer/italy-span-fallback-development.json) | 10 | 0 | None | 7/17 |
| [Estonia](right-entry-transfer/estonia-span-fallback-development.json) | 9 | 0 | None | 8/17 |
| [China](right-entry-transfer/china-span-fallback-development.json) | 10 | 1 | C17 | 7/18 |

The one addition, China's **R048**, begins at y=218, beyond the line-based first-observation gate. Its [source-hashed four-frame sheet](right-entry-transfer/china-span-fallback-source-review/r048-span.jpg) shows the marked yellow stone moving toward the house from 2668–2671 s; the [development review record](right-entry-transfer/china-span-fallback-source-class-development.json) keeps physical delivery and cross-camera identity unverified. The [probe runner](../../../../prototype/scripts/probe_right_span_fallback.py) checks transfer, variant and coarse-reference hashes before reporting window coverage. The [render manifest](right-entry-transfer/china-span-fallback-source-review/manifest.json) ties the source crop to the exact video and probe.

The fallback adds **one** short stone path but leaves **22 of 52** coarse source-only windows without either right prefix across these recordings. Those windows are five-second-still, same-agent references, not certified exhaustive event truth; their coverage is not detector recall. The small gain means removing the virtual line alone does not solve the right-view proposal bottleneck. Many missing windows need better initial colour-cap proposals, shorter-track recovery, or a separate motion cue. Promoting this fallback or requiring right corroboration would be unjustified without source-checking newly admitted people/equipment paths and an independent end-level test. No accepted timeline or F1 changes here.
