# Customer footage audit

Open [report.html](report.html) for the visual audit. Source: first tab (`gid=0`) of the user-provided video catalogue, retrieved 2026-09-23. The spreadsheet was not modified.

## What was done

- Preserved 317 catalogue rows in `../sources/provided-video-catalogue.csv` with original sheet row numbers.
- Audited catalogue identities, repeated targets, playlist references and inconsistent metadata labels.
- Retrieved metadata for eight purposively selected YouTube recordings, spanning 18.25 hours of recording duration. This is **not** 18.25 hours of watched footage.
- Extracted eight fixed-fraction frames from each recording (64 total): 8%, 20%, 32%, 44%, 56%, 68%, 80%, 92%.
- Inspected four additional 12-second windows sampled every two seconds (24 frames).
- Visually assessed all 88 frames and wrote qualitative observations. No model benchmark or full-match reconstruction was performed.
- Probed one Google Drive file (HTTP 401 without authentication) and one Rock Channel page (HTTP 200; playable media not verified).

## Key conclusions

Seven of eight sampled recordings use composite camera layouts. Multiple sheets and multiple matches appear in some files. Four sources offer only 480p in the retrieved metadata. A GSOC recording has a conflict between title/catalogue team pairings and on-screen pairings. Treat this as unresolved, not as permission to silently correct the team mapping.

Prioritise the 1080p 2024 Canada–Korea recording for the first customer-style workflow, use Beijing overhead footage as a geometry control, and add Leduc insets as another source family. The eight inspected videos are development examples, not an untouched final test set. Reserve different recordings/events and keep all aliases and panels of a recording in one partition.

## Files

- `catalogue-summary.json`: catalogue counts and repeated-target groups; playlists not expanded.
- `catalogue-sample.json`: selected metadata and original catalogue rows.
- `frame-manifest.json`: systematic sample provenance and requested timestamps.
- `temporal-manifest.json`: temporal windows and frame files.
- `observations.json`: AI visual assessments, explicitly not independently labelled ground truth.
- `frames/`: decoded source-resolution JPEGs (sampling capped at 1080p).
- `contact-sheets/`: systematic and temporal sheets.
- `source-access.json`: limited access probes.
- `metadata/*.raw.json`: yt-dlp extraction output; includes temporary media URLs. These expire and are not intended as permanent citations.
- `sampling.log`, `sampling-retry.log`: acquisition progress. One transient timeout was successfully retried.
- `browser-check.json`: report verification results once generated.

## Reproduce

From the project root, use the existing feasibility environment (yt-dlp, Pillow and ffmpeg required):

```sh
feasibility/scripts/python.sh research/footage-audit/scripts/audit.py --refresh
feasibility/scripts/python.sh research/footage-audit/scripts/sample_frames.py
feasibility/scripts/python.sh research/footage-audit/scripts/temporal_samples.py
feasibility/scripts/python.sh research/footage-audit/scripts/build_report.py
```

`--refresh` refreshes metadata/temporary media URLs. Systematic sampling reuses existing frame files. Temporal sampling overwrites its small windows. Visual observations are reviewed records and are not regenerated automatically. Public source availability and formats may change.

The report builder reuses inline styling from `../curling-landscape.html`; the generated report itself needs only the local evidence files, with no external font/script dependencies.

## Limits

Sparse, purposive sampling cannot estimate catalogue-wide success rates or establish per-shot coverage. Requested timestamps are not independently verified exact frame indices. Temporal fps sampling labels use two-second bins. Camera synchronisation, exact calibration, stone ground truth, rules/score accuracy and commercial media permissions have not been established. Source rights remain with their owners. No external publication occurred.
