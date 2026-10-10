# Frozen two-shot transfer on a second Swiss live interval

Select the continuous Sweden–Switzerland 2022 interval **3300–3600 s**.
Thirty ten-second source samples showed the compact live overlay in 30/30
frames. This interval has not been used for shot-origin fitting or the
two-shot motion rule, although the source match is otherwise exposed.

- Source SHA-256: `49429abdd3796e8240e66c201d37e94e71a7bb6225890b2492bea26d2f70d560`
- Frozen origin model: `shot-origin-pair-v1/model-excluding-swiss-dev.npz`
- Origin model SHA-256: `9586973ae7cbc632c65e3b757015f30d1d2fcf38190d50c39bb43c4ed827661a`
- Learned-box model SHA-256: `81421342467a0ab8d93f4e08829e5928eefbf98c655b2f3a436493ec002feb63`
- Two-shot rule SHA-256: `4ed5732d5140e5bc972898c794b1e89388a31243a7bdda0a21e48845663df129`

Freeze the source-only shot review labels after scanning hard cuts and before
reading either model's predictions. The predeclared decision is: an origin
probability ≥0.5, live overlay in at least two of three frames in the current
or following shot, and a sustained same-colour motion track in both shots
from either the cap or learned-box channel. Ambiguous colour remains unknown.
Score the resolved shot labels at zero extra tolerance. Retain any unresolved
boundary labels and report them separately.

This is a same-match development transfer, not independent event F1. Shot
labels are agent-authored, cap/box channels share frames and colour
segmentation, and even adjacent same-colour tracks are not proven to be the
same physical delivered stone.
