# Preselected Swiss live-play shot-origin transfer

Select Sweden–Switzerland 2022 Paralympics source interval **1200–1500 s**.
Thirty ten-second samples in this span showed the compact live overlay in
30/30 frames before any shot-origin model output or source-shot labels were
read. This source match has been exposed in other experiments, but this
interval was not in the 3900–4200 s shot-origin training/evaluation packet.

- Source SHA-256: `49429abdd3796e8240e66c201d37e94e71a7bb6225890b2492bea26d2f70d560`
- Frozen model trained on China and Slovakia shots:
  `shot-origin-pair-v1/model-excluding-swiss-dev.npz`
- Model SHA-256: `9586973ae7cbc632c65e3b757015f30d1d2fcf38190d50c39bb43c4ed827661a`
- Feature code SHA-256: `f5b28fc761aca84a2721f971afdf62370a1d2732479eece4574bb68ba9dfd54c`
- Threshold: probability ≥0.5 and live overlay in the current or following
  shot (at least two of three frames). These rules are frozen from the
  retrospective three-match shot-role experiment.

First scan hard cuts, build source-only shot sheets, and freeze the agent's
delivery-origin shot labels **before** computing model predictions. Then
score all detected shots one-to-one as a development transfer diagnostic.
No independent event-F1 claim follows: the same source match is exposed,
labels are agent-authored, cut detection can miss edits, and shot-origin
classification does not establish a stone release or physical trajectory.
