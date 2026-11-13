# Release-side colour audit for unlinked-motion proposals

The [shot-scoped audit](unlinked-motion-release-colour-audit-first.json)
applies the existing frozen held-to-motion cue rule to the exact origin
camera shot of all **11** unlinked-motion review proposals across Norway and
China. It does not search across cuts. A *single* qualifying passage gives
source-local release-colour evidence; zero or multiple passages require
abstention.

| Result | Proposals | Source evidence |
|---|---:|---|
| Unique release-colour cue | 2 | China S216 has a red cue at 2665.4 s, agreeing with its red receiving track. Norway S647 has a yellow cue at 8607.8 s, agreeing with its yellow receiving track and conflicting with the provisional red candidate colour. |
| No unique cue | 9 | The rule abstains. It cannot reject the visually plausible deliveries or resolve China S377's yellow-delivery/red-receiving mismatch. |

The [Norway source frames](norway-unlinked-motion-rescue-source-frames.jpg)
and [China transfer frames](china-unlinked-motion-transfer-source-frames-2.jpg)
make the S647 and S377 colour issues visible. Even a unique release-side cue
does not prove that the same stone appears after the camera cut. It is a
useful conservative *evidence channel*, but a hard cue-presence filter
would discard nine of these 11 review proposals without establishing that
they are false.

Reproduce with:

```sh
feasibility/scripts/python.sh prototype/scripts/audit_unlinked_rescue_release_colours.py
```

The saved output records both source hashes, shot manifests, proposal files,
detector code and decision code. It refuses overwrite. These are
agent-developed source diagnostics, not independent event F1 measurements.
