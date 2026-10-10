# Postscore full-match stage-one sweep

This plan was written **after** the frozen 1650–2760 s transfer and source review. It is a separate development sweep, not a new unseen or independently labelled test. Run the unchanged 10 Hz span detector over the complete 360p recording, source seconds **0–6683**, and apply the unchanged x = 160 ± 60 px fixed-left-panel corridor. Preserve every raw and withheld candidate. Do not adjust thresholds or clip the source by the known interval result.

| Component | SHA-256 before this sweep |
| --- | --- |
| Full 360p video | `e63c9b063b5b11ad5173083dffe974d909c78e5d01312740b87bccc006402013` |
| `run_span_probe.py` | `35f3062165aac099e9b9337fbd7614f98e865c248774872ef89c2034b03b8653` |
| `span_passage_detection.py` | `45a14f710e6523f1036f939b90fb196c0c6e7a636c47ab443000eb20340d42e4` |
| `throw_detection.py` | `40678c23b117f527c80375ff7d7fbe3a1119fb94c4650b05698cd2c76be9628f` |
| `screen_corridor.py` | `d73c529bd32a8e68b45cc05021be2d0d68e50fed22bd8305c2fc29032b5f1002` |
| `passage_corridor.py` | `3f8829d965d8a62312d9016e6955d1cc2c8546ad4e19c47b2d3c7a934f5bd036` |

After the sweep, verify that the previously frozen interval candidates can be reconciled with the full-match run, allowing for track-ID reset and a candidate crossing the interval boundary. Compare counts and candidate times within the six **displayed-end** runs from the separate marker scan, with any uncovered gaps explicit. These displays are not physical end boundaries. The full-match source has no full-length 1080p copy in this workspace, so this run stops at stage-one span/corridor proposals; it must not present them as screened throws or claim full-match F1.
