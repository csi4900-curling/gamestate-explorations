# Source-first development throw reference

Select the full Canada–China 2024 source by its saved SHA-256 prefix
`2a0885f2`. Select a 300-second interval from starts 3000, 3300, …,
7800 using `int(prefix, 16) % 17`; this gives 3000–3300 s, away from
the previously measured 1650–2760 s interval and inside a supported
split-screen route. This selection uses source identity, not event output.

Before reading any prediction timestamps for 3000–3300 s, inspect
source-only frames once per second from the left and right halves.
Record each distinct delivery as a coarse interval wide enough to include
the observed travel but narrow enough to separate nearby deliveries.
If colour or delivery identity is unclear, mark it uncertain and examine
the underlying video at a denser rate before freezing the reference.
Freeze reference content and its SHA-256 before extracting predictions
from the already saved full timeline. Score one-to-one point timestamps
with zero extra tolerance beyond each reference interval; report false
positives, misses and colour errors separately.

This is an agent source-first development reference. Sparse sampling and
same-team bias limit claims of exhaustiveness or independence. The
reserved Wetzikon source is excluded. The outcome cannot satisfy the
independent complete-recording 0.95 precision/recall gate.
