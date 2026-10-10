# Tracked-object appearance transfer, 2024 development probe

The [selection](identity-patch-selection.json) uses 15 source-reviewed real
deliveries and three likely false events from the exposed Canada–China and
Canada–Estonia recordings. The [packet builder](../../prototype/scripts/build_2024_identity_patch_packet.py)
replays the unchanged raw cap tracker on separately downloaded 360p variants,
requires the selected crossing to reappear within 0.15 s, and saves three
48×48 source-linked crops from each emitted track. The
[manifest](identity-patches-v1/manifest.json) records the source, timeline,
selection, runner and crop hashes. Its [China contact sheet](identity-patches-v1/Y_U6gzqORUs-contact.jpg)
and [Estonia contact sheet](identity-patches-v1/PXGfMeiTKMA-contact.jpg)
show the actual tracked objects rather than unrelated frame content.

Before scoring Estonia, the [transfer runner](../../prototype/scripts/score_2024_identity_patch_transfer.py)
fixed a balanced linear SVM with standardized HOG/HSV patch features,
`C=0.1`, a zero decision threshold and the mean of three sample scores per
event. It trained on eight real and two likely false China tracks (30 crops),
then scored seven real and one likely false Estonia tracks (24 crops) without
refitting. The saved [model and results](identity-transfer-v1/results.json)
agree with source review for **6/8 Estonia tracks**: five real stones and the
one broom false event. It marks two real stones, R01-S79 and R02-S61, as
non-stone. This is **5/7 real-track retention** and **1/1 reviewed false-track
rejection** on a tiny same-production development transfer. The training
agreement is 10/10, which is in-sample and uninformative about transfer.

The misses are decisive for the intended high-recall detector: this model
cannot be used as a hard veto. A score may still be useful as graded evidence
in an identity ledger, but absent or negative appearance evidence must not
erase a moving-stone candidate without independent corroboration. The result
does not measure full-match throw precision, recall, release timing or
cross-camera physical identity. The user-reserved unseen source remains unused.

A third-match recall check was then fixed from the older
[Italy agent-blind coarse reference](../throw-event-benchmark/canada-italy/blind-reference.json)
and its preserved [17 matched events](../throw-event-benchmark/canada-italy/development-span-confirmed-score-v2.json),
before running the frozen China-trained patch model on Italy. The
[Italy selection](identity-patch-italy-selection.json) maps those events to
their exact full-timeline IDs. The [Italy patch manifest](identity-patches-italy-v1/manifest.json)
and [contact sheet](identity-patches-italy-v1/Vp3TIdOAlrc-contact.jpg)
preserve three tracked-object crops per event. Unlike the China and Estonia
downloads, the Italy 360p file has **the exact SHA-256 of the saved Italy
timeline source**. The unchanged [first score](italy-identity-first-score.json)
marks only **2/17** source-window-matched tracks as stone-like. This is a
selected coarse-reference retention check, not exhaustive full-match recall;
it decisively rules out the appearance model as a hard event gate. Neither
threshold nor weights were adjusted after seeing this result.

The later [China catalog](CHINA-CATALOG-REVIEW.md) exposed a track-identity
merge: R01-S211 starts on a person or wheelchair and switches to a moving
red stone near its event crossing. This explains a weakness of sampling early,
middle and late points from the entire track. A separate
[crossing-local packet builder](../../prototype/scripts/build_2024_crossing_patch_packet.py)
therefore takes tracked points nearest to 0.2 s before, at, and 0.2 s after
each crossing. This was designed **after** seeing the first Italy failure; it
is a postscore development comparison, not a new holdout. With the same fixed
linear SVM recipe, the [Estonia score](identity-crossing-transfer-v1/results.json)
retains only 4/7 reviewed real stones and rejects the one reviewed broom;
the repeated [Italy score](italy-crossing-identity-first-score.json) retains
11/17 coarse-window-matched tracks. R01-S211's
[crossing-local crops](identity-crossing-patches-s211-v1/Y_U6gzqORUs-contact.jpg)
show the stone, yet its [frozen score](s211-crossing-identity-score.json) is
still negative. Sampling near the event helps some appearances but does not
make the model safe as a hard gate.

Reproduction requires the three cached recordings with the hashes in their
packet manifests. The packet builder and transfer runners refuse to overwrite
existing results. Their outputs and the initial 54 crop hashes were checked
after creation; none changes the frozen detector or timelines.

A later [Latvia/Italy source-pixel probe](LATVIA-ITALY-CROSSING-PATCH-SOURCE-CLASS-PROBE.md)
applies the same frozen crossing-patch model to 14 additional postproposal
source-reviewed crossings. It separates the selected person S45 from most
stone-shaped paths but still scores two visible stones negative, reinforcing
the decision to keep its score as graded evidence rather than a hard veto.
