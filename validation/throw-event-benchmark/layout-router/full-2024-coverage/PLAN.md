# Whole-recording 2024 layout-coverage audit

Before inspecting any new full-video preflight output, apply the existing
layout router unchanged to all three on-disk 2024 transfer recordings:
Canada–China (`Y_U6gzqORUs`, 0–8177 s), Canada–Italy (`Vp3TIdOAlrc`,
0–8340 s) and Canada–Estonia (`PXGfMeiTKMA`, 0–8433 s). Use the already
development-selected 90-second chunks from the Canada–USA full pass.
Record supported-run coverage, unknown spans, and the distribution of
frame-level split signatures within each type of span. No event detector
or reference labels are used in this audit.

These are exposed development recordings. The purpose is to determine
whether the current router covers continuous live play across multiple
2024 matches and to locate repeatable coverage failures before changing
the classifier. Supported layout is not proof of throw recall.
