# Frozen development transfer plan: Canada–Estonia 2024

Recorded 8 October 2026 **before obtaining or inspecting a 1080p Estonia interval copy and before running the candidate-centric receiving-motion screen on it**. Estonia's 360p source, coarse reference, and earlier throw-detector outputs are already exposed; this is a cross-recording development transfer, not a new untouched or independent benchmark.

Use the existing `validation/throw-event-benchmark/canada-estonia-2024/development-span-corridor.json` candidate set (SHA-256 `ba103e076936412513b3267de8625f9e3ca4fbb0be7b4f3b3cdde77c14c78526`), with 22 postscore source-only span candidates. The coarse reference remains `blind-reference.json` (SHA-256 `d53b1a878c03134c328e83f0317c946c909e0c83d4395fb8a7d9c1433cc5c7fa`). The candidate set already scores 17 TP / 5 FP / 0 FN against that exposed reference. Preserve that baseline.

Acquire a separate 1920×1080 copy of source interval 1650–2760 s. Verify source-time alignment against the existing full-match 360p file before inference. Run the candidate-centric receiving scan with `--source-offset 1650 --lookahead-s 12 --sample-period-s 0.5 --max-corner-displacement-px 160`. It uses only each candidate's time, colour, and direction, not reference windows. Score first, middle, and last points of each selected motion path with the already frozen `model-excluding-china-dev.npz`. Accept only a unique far-entry motion path with at least one of those three patch scores above the model's fixed threshold. Preserve motion, appearance, screen, and score artifacts separately, even if the transfer fails. Do not tune these settings based on Estonia outcomes and call the result a first-pass transfer.

Input/code fingerprints before this transfer:

| Item | SHA-256 |
| --- | --- |
| Candidate-centric runner | `77f9618344b41e773121e0348215206ecb7b6989fe7239f840e120428f612714` |
| Motion selector | `a4ab39c2893d281d6a38d1a94834e380367ab9c2d861c770dddd13cc4a706d21` |
| Patch-audit runner | `38c614fda4486d5e50ca0aa02cbc1bc7783067173412ce03964a0766a09ccb20` |
| Two-cue rule | `4689d5cc657736417fe73404a4fec5faec0392cdb7cd6b28f3a12e95c560a52f` |
| Two-cue runner | `d1fd599436b33d81ffca183c82feb91f6a39512670364b92065a70bd5214b67b` |
| Frozen patch model | `10036a8b13e7e35f0be3cfd7280e9e0afaa3cf5b5da6cecc5623fb79695e0670` |

This transfer can test whether a rule developed on Canada–China behaves similarly on another exposed match from the same production. It cannot prove high F1 across camera families, exhaustive full-match segmentation, physical stone identity, or simulator-ready game states. The reserved Canada–USA unseen end remains untouched.

The frozen transfer failed on recall; see the [result and separate postscore repair stages](CANADA-ESTONIA-2024-MOTION-TRANSFER-RESULTS.md).
