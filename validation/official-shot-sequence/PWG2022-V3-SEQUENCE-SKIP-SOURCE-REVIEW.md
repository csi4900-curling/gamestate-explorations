# Source review of four sequence-skipped release cues

The [v3 review queue](pwg2022-v3-sequence-review-queue-development.json) has 15
candidates skipped in every lowest-cost official-sequence alignment. Four of
those candidates have a unique source-video release passage. The stills below
show a stone separating from the delivery setup and moving away in each case.
This is an **internal development observation**, not an independent physical
throw label or an event-F1 measurement.

| Recording / candidate | Source observation | Frames |
| --- | --- | --- |
| Switzerland, `VISUAL-S243` | Red stone leaves the delivery setup at about 3122 s. The candidate has counter link B47. | [Contact sheet](PREL000101-VISUAL-S243-sequence-skip-source-review.jpg) |
| China, `VISUAL-S593` | Yellow stone leaves the delivery setup at about 7951–7952 s; the v3 ledger says red. A yellow stone appears in the receiving view, but its identity across the cut is unverified. | [Contact sheet](PREL000102-VISUAL-S593-sequence-skip-source-review.jpg) |
| Slovakia, `VISUAL-S60` | Red stone moves away from the delivery setup at about 1024–1026 s. | [Contact sheet](PREL000103-VISUAL-S60-sequence-skip-source-review.jpg) |
| Slovakia, `VISUAL-S282` | Red stone leaves the delivery setup at about 4463–4465 s. The candidate has counter link B58. | [Contact sheet](PREL000103-VISUAL-S282-sequence-skip-source-review.jpg) |

The sequence optimizer's skip decision therefore cannot be used as an
automatic false-positive label or a reason to suppress these four candidates.
The discrepancy may reflect an extra candidate elsewhere in the end, an
incorrect colour, end partitioning, a delayed or flickering counter, or the
alignment cost. The stills do not resolve which official shot each delivery
represents or establish persistent physical stone identity.

Rebuild the stills from the source videos and frozen queue with:

```sh
feasibility/scripts/python.sh prototype/scripts/render_v3_sequence_skip_release_contact_sheets.py
```

The [S593 colour sensitivity](china-s593-sequence-colour-sensitivity-development.json)
is an offline postscore check: changing only the v3 candidate colour from red
to source-yellow reduces China end-eight minimum edit cost from 8 to 4 and
matches it to official shot E08-S13 in the unique optimum. This supports a
source-colour correction proposal; it is not independent validation, and the
frozen v3 union is unchanged.
