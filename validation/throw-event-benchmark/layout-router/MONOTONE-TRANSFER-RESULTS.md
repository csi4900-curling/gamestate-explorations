# Full-match counter transfer after the one-row-rise guard

The [plan](MONOTONE-TRANSFER-PLAN.md) fixed Slovakia–USA and
Sweden–Switzerland 2022 before replay. Both are previously exposed
development matches, but neither full counter stream was used to choose
the one-row-rise guard. The model and observations were unchanged during
this comparison.

| Broadcast | Prior reset-blink counter events | Monotone replay | Removed keys | Added keys |
| --- | ---: | ---: | --- | --- |
| Slovakia–USA | 98 | [94](slovakia22-monotone-counter-transfer.json) | red 395, 4428, 4458, 5832, 6421; yellow 6458 | yellow 1280, 6421 |
| Sweden–Switzerland | 103 | [98](swiss22-monotone-counter-transfer.json) | red 3093, 3118, 6077, 6089, 6155; yellow 5268 | red 3357 |

The one-row-rise guard changed more than the original Canada–China match,
so the short 1650–2760 s regression intervals did not cover the relevant
failure modes. In both transfers, several prior rows form clear counter
cycles: Switzerland's yellow 5254 and 5268 s both claimed `[8,8]` →
`[8,7]`; the new replay retains the first. Switzerland's red 3093 and
3118 s both claimed `[8,6]` → `[7,6]` after earlier lower red counts;
neither remains. Slovakia's red 4428 and 4458 s both claimed `[8,7]` →
`[7,7]`, while the later monotone red 4465 s remains. These counter
relationships support removing duplicates. They are not themselves proof
of which video frames contain true deliveries.

Three-second source-only sheets cover the changed areas:
[Slovakia 370–415](monotone-transfer-review/slovakia-370/sheet-01.jpg),
[4400–4480](monotone-transfer-review/slovakia-4400/sheet-01.jpg),
[6390–6480](monotone-transfer-review/slovakia-6390/sheet-01.jpg),
[1230–1310](monotone-transfer-review/slovakia-1230/sheet-01.jpg),
[5800–5880](monotone-transfer-review/slovakia-5800/sheet-01.jpg),
[Switzerland 3070–3140](monotone-transfer-review/swiss-3070/sheet-01.jpg),
[5240–5290](monotone-transfer-review/swiss-5240/sheet-01.jpg),
[6060–6170](monotone-transfer-review/swiss-6060/sheet-01.jpg) and
[3320–3390](monotone-transfer-review/swiss-3320/sheet-01.jpg).
They show active play and visible moving stones in several changed windows,
including near Slovakia 1280 and Switzerland 3357 s. They do not provide
frame-rate release identities or an exhaustive reference. The new model's
event counts and apparent duplicate reduction are therefore development
evidence, **not measured precision, recall or F1**. No transfer-specific
threshold was fitted after this comparison.

The next decisive test is a source-independent, exhaustive delivery
reference over continuous recordings, including counter unreadability and
the known layout gaps. Counter consistency can screen candidates but cannot
stand in for the throw truth needed for the 0.95 precision/recall gate.
