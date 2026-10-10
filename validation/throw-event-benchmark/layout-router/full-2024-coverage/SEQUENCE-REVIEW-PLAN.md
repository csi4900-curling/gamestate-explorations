# Targeted chronology review selected from frozen full-run timelines

The official [World Curling overview](https://worldcurling.org/about/curling/)
states that opponents alternate deliveries within an end; the
[2024 rules](https://worldcurling.org/wp-content/uploads/2024/08/Rules-2024.pdf)
allow exceptional re-deliveries. End boundaries are not known from these
event timelines, so same-colour adjacency is a review signal, not a
detector correction.

Before inspecting the source clips, select every adjacent same-colour
pair in a single supported run with no coverage gap and less than 40
seconds separation. The [frozen audits](new-preflight-estonia24/sequence-audit.json)
and [China audit](new-preflight-china24/sequence-audit.json) yield five
pairs: Estonia R01-S12/S14 at 667/679 s and R02-S61/S62 at
6261/6280 s; China R01-S171/S173 at 5856/5882 s, S196/S200 at
6460/6494 s and S214/S217 at 7081/7116 s. Italy has none.

Inspect source-only full-frame samples every two seconds over 655–700,
6248–6300, 5842–5905, 6445–6515 and 7065–7135 s respectively.
Record whether the two rows represent two distinct deliveries, a single
delivery seen twice, a colour error, an off-camera opponent delivery,
or unresolved evidence. These model-selected clips are **development
audits**, not independent event precision/recall labels.
