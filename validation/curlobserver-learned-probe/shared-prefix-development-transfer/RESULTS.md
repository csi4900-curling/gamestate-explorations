# Shared-prefix development transfer result

The unchanged [frozen rule and input plan](PLAN.md) produced **zero additional partial review proposals** on all three exposed development/control recordings. It did not change any frozen screen decision. The output files preserve code and input hashes: [Italy](italy-prefix-proposals.json), [Estonia](estonia-prefix-proposals.json), [Scotland](scotland-prefix-proposals.json).

| Recording | Screened candidates | Frozen accepted | Abstained | Abstention motion status | New shared-prefix proposals |
| --- | ---: | ---: | ---: | --- | ---: |
| Latvia, rule-development case | 19 | 14 | 5 | 4 no path; 1 ambiguous path (S21) | 1 (S21) |
| Italy, development transfer | 24 | 14 | 10 | 10 no path | 0 |
| Estonia, development transfer | 22 | 17 | 5 | 4 no path; 1 unique path filtered later | 0 |
| Scotland, already exposed control | 26 | 18 | 8 | 7 no path; 1 unique path filtered later | 0 |

The fallback requires `ambiguous_far_entry_motion_paths`. Only Latvia's S21 has that status among these abstentions. A zero result on the other recordings is therefore expected from the rule, not evidence that they have no missed throws. It shows this rescue has **narrow failure-mode coverage** and cannot by itself deliver high recall across recordings. These triples are **earlier screens**: a separate [conditional cap-dropout rescue](../CANDIDATE-DROPOUT-RESCUE-DEVELOPMENT.md) was already developed for no-supported-path cases and fits the exposed Italy/Estonia coarse windows. The [Slovakia transfer](../CANADA-SLOVAKIA-2024-DROPOUT-TRANSFER-RESULTS.md) ran that later stage without an exhaustive reference. Thus the next validation step is to test a frozen *combined* rule on a new recording with independent labels, not to mistake this earlier-screen no-op for the performance of the best available pipeline.

These recordings and their coarse references were previously inspected by the same agent. The table is proposal accounting, not independent physical-event precision, recall or F1. The reserved Canada–USA end was not used.
