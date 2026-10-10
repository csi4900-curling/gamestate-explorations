# Public tracking clip stone-box experiment

This is a **component development result**, not throw-event F1. The source is
[CurlObserver's public tracking dataset](https://github.com/CurlObserver/dataset)
at commit `2cfe61efede3c446957ee94aefa8df1345fc4684`. The deterministic
clip split used 77 clips for fitting, 15 for threshold choice, and 20 for a
single test. Clip 0 had already been inspected and was placed in the fit set.
The public clip IDs do not identify source matches, so this is not a
match-independent test. The earlier frozen model used public detection images
from the same dataset family, another potential source of correlation.

At five-frame sampling, 985 of 986 possible test frames had annotation files.
Same-colour boxes were matched one-to-one at intersection-over-union ≥ 0.5.
The frozen model scored 2,067 matches, 1,704 extras and 236 misses: precision
0.5481, recall 0.8975, F1 0.6806. The revised model scored 2,027 matches,
388 extras and 276 misses: precision 0.8393, recall 0.8802, F1 0.8593.
Per-clip F1 improved on 18 of 20 clips. Adjacent frames are correlated; these
are box totals, not independent trial counts. Neither persistent stone
identity nor cross-camera handoffs were scored.

`results.json` records clip IDs, source-video hashes, sample coverage, model
hashes, training counts, validation threshold selection and per-clip scores.
`model.npz` is a research candidate. It has **not** replaced the frozen
full-match detector; any event improvement needs a new, pre-specified
full-recording transfer test.

## Exposed broadcast transfer check

The [targeted Canada–Norway audit](norway-end2-targeted-transfer.json) ran both
models at approximately 5 Hz in four prior end-2 colour-conflict windows and
four agreement controls. Selection used the exposed first transfer, so this
is diagnosis, not a held-out score. The revised model removed the supported
red track in one of four yellow-counter conflict windows (`S139`), but still
formed red tracks in two (`S95`, `S99`) and found no supported yellow track in
any of the four. In the yellow agreement control `S156`, it found a yellow
track where the frozen model instead formed a red track. Two red agreement
controls retained red tracks; the third had no supported track under either
model. These observations are mixed and do not justify replacing the frozen
event model.

At `S95`, source time 1399 s, a yellow stone is visible near the bottom edge.
The revised detector generated yellow proposals near it, but the highest of
those local scores was about -2.29 against its 1.34 acceptance threshold; it
accepted three red boxes on other image content. This points to patch
recognition and broadcast side-view transfer as current bottlenecks. The
counter-to-window pairing itself is also provisional, so colour disagreement
cannot independently identify which visual track is the delivery.

The run can be reproduced with:

```sh
LD_LIBRARY_PATH=/nix/store/k3r7ixfmwrzsww883knj3zhxh9hg0ljz-gcc-14.2.0-lib/lib:/nix/store/b6mjyiadysqlh7nps52faznnqmp32604-zlib-1.3.1/lib \
  .venv/bin/python prototype/scripts/train_tracking_patch_v2.py \
  --dataset /path/to/dataset/curling_dataset/curling_tracking_dataset \
  --baseline-model validation/curlobserver-learned-probe/model-v1/model.npz \
  --output /path/to/new-output
```

The script refuses an existing output directory to preserve the first score.
