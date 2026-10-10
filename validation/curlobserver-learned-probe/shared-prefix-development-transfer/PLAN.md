# Shared-prefix proposal: fixed-rule development transfer

This protocol was recorded before applying the Latvia S21 shared-prefix rule to the Italy and Estonia artifact triples below. Both recordings have already been used by this project, so this is a **development transfer check**, not untouched match validation or an independent physical-throw benchmark. Scotland is an already exposed reproduction control. The reserved Canada–USA end is excluded.

Apply `prototype/scripts/propose_candidate_shared_prefix.py` unchanged to each complete motion/patch/screen triple. Only screen abstentions can produce a partial review proposal. Fixed thresholds: at least five shared samples, prefix fraction ≥0.7, conditional endpoint displacement ≥2 m, at least three scored prefix patches and two accepted patches. Preserve candidate IDs and frozen screen decisions. Record proposal IDs, source-time intervals, candidate colours and artifact hashes. Do not tune thresholds after seeing these outputs. A proposal is neither a verified delivery nor an accepted complete trajectory.

The model SHA-256 is `6e6e2d3342b0227702dd2fa301e8dbbf07d8149487a05086dbac7d7e787c492e`; the runner SHA-256 is `6f892d54e0e7179bd20b34ed39136233d4314730093f8a3691d6a36d9a80597c`.

All paths below are under `validation/curlobserver-learned-probe/`, in motion / patch / screen order:

| Recording | Artifact names | SHA-256 in the same order |
| --- | --- | --- |
| Canada–Italy 2024 | `canada-italy-2024-candidate-motion-with-gaps-frozen-repair-transfer.json` / `canada-italy-2024-candidate-motion-patch-frozen-repair-transfer.json` / `canada-italy-2024-candidate-motion-patch-screen-frozen-repair-transfer.json` | `f5f7cd2d3cb0d26ad2bdf9eabce9ea8aa1e2a5bac327be828561ce2e8a5c6813` / `e1f5f0e344d51936596ce09dabb9d230a3d333e1ed097fe0583b9a77cd9abbc0` / `0cc71c8a1f5b7c9eb4c24588bb3802bf9bee443d1a08b936eae060a235c9129a` |
| Canada–Estonia 2024 | `canada-estonia-2024-candidate-motion-with-gaps-v2-development.json` / `canada-estonia-2024-candidate-motion-patch-after-hold-development.json` / `canada-estonia-2024-candidate-motion-patch-after-hold-screen-development.json` | `1910127868d243b738b7b159beeabdbc01fcee72013debcc76606b0ec1d8f743` / `a4b16f8d014b70cf6b7620909d1afcc4d3338d870f3560f9b940c5929844aa3b` / `461b2b413e9f954b8586008d68752e61fcc28f9f844d9c63800f39eea942c8d8` |
| Canada–Scotland 2024 control | `canada-scotland-2024-fixed-grid-gaps-development.json` / `canada-scotland-2024-fixed-grid-gap-patch-development.json` / `canada-scotland-2024-fixed-grid-gap-screen-development.json` | `5fd4dbfbb643738de1304616cf4d0bf1d88aa891f10e36f125f77af565927597` / `fbf70bb457a265954f9df8c115186591d095b047d88a00666974d378f7a0a7b8` / `a646b8f6d12f96d510f9ed0d7a51d1076c6b0d27b3499e27b9d551d501f80346` |

Report the full screened candidate denominator and abstention count for each artifact, but do not compute precision, recall or F1 from these same-agent artifacts. A zero-proposal result means this *specific* fallback did not add a bounded path; it does not mean the detector had no missed throws.
