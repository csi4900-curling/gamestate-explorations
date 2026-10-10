# Within-view release evidence at ambiguous Slovakia counters

The [reproducible source scan](slovakia-ambiguous-release-passages-development.json) applies the existing, unchanged held-to-motion cap cue to every camera shot offered by the four unlinked multi-option counters in the Slovakia full match. It samples all 13 distinct shots at 5 Hz and keeps each broadcast shot separate, so no track crosses a camera edit. This is a development diagnostic on an exposed recording, not full-match event recall.

| Camera shot | Within-view passage | Cue time | Counter-option relationship |
| --- | --- | ---: | --- |
| S287 | yellow | 4595.4 s | Conflicts with red B61 |
| S374 | red | 5817.8 s | Matches red B80; already provisionally linked to red B81 |
| S411 | yellow | 6386.8 s | Conflicts with red B86 |

The other ten shots have no qualifying within-view passage. Notably, the sustained yellow held-cap evidence in S372 lacks the required within-view motion passage, while S411 has both. The stationary red stone in S373's overhead view also fails the release cue. The passage is stronger source evidence than held colour alone, but it still does not prove that the patch is the delivered stone or that it is the same stone after a camera cut.

S374 illustrates why the delayed scoreboard cannot settle identity by itself. The raw [Slovakia counter audit](../curlobserver-learned-probe/slovakia-full-transfer/counter-audit.json) reads alternating red counts near these updates: `[3,2]` and `[4,2]` in 5825–5832 s, then `[2,2]` and `[3,2]` repeatedly during 5838–5860 s. B80 updates at 5832 s; B81 updates at 5860 s. The visual passage at 5817.8 s cannot be assigned to either counter from those timestamps alone. This local graphic instability does not justify discarding all scoreboard evidence; raw one-second readings are noisy elsewhere too. It does justify preserving the counter association as uncertain.

The [four-match raw sample audit](COUNTER-SAMPLE-SUPPORT.md) confirms that simple exact-state stability is a poor hard filter: only 58 of 400 emitted updates with visible readings on both sides reach 0.75 support on each side.

No event candidate, counter link, release timestamp, or board state is promoted by this audit. To reproduce, run `PYTHONPATH=prototype feasibility/scripts/python.sh prototype/scripts/audit_slovakia_ambiguous_release_passages.py` from the project root. The output includes source, alignment, code and runner hashes.
