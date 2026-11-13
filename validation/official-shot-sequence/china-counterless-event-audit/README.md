# Nine China event proposals without a readable counter update

The [source-only manifest](manifest.json) joins the preserved provisional
event windows to release and receiving-view cues from the same Canada–China
video. It renders three sampled frames per event across
[sheet 1](sheet-01.png), [sheet 2](sheet-02.png), and
[sheet 3](sheet-03.png). No official shot diagram or shot count was used to
select these events or frames.

| Event | Evidence tier | Next action |
| --- | --- | --- |
| VISUAL-S52 | Visual window only | Review continuously around the first-end preparation and next counter. |
| VISUAL-S142 | Release and receiving colour agree | Keep as a counterless throw candidate; verify physical identity if needed. |
| SOURCE-S216 | Release and receiving colour agree | Keep as a counterless throw candidate; verify physical identity if needed. |
| VISUAL-S360 | Visual window only | Review continuously for an actual delivery after the static board view. |
| VISUAL-S403 | Visual window only | Check whether it duplicates nearby B86 or is only camera context. |
| VISUAL-S411 | Visual window only | Review the long window for an observed stone departure. |
| VISUAL-S427 | Release and receiving colour agree | Keep as a counterless throw candidate; verify physical identity if needed. |
| VISUAL-S529 | Release and receiving colour agree | Source cues fill its missing colour as yellow. |
| VISUAL-S593 | Release and receiving colour agree | Source cues correct its provisional colour from red to yellow. |

The five events with two-view evidence remain provisional: matching colour
across a broadcast cut does not prove physical stone identity. The other
four remain in the high-recall candidate set but are displayed as
**unconfirmed visual windows**. Three sparse frames cannot establish that
any of those four is a false throw. The equal totals of 125 proposals and
125 official shots do not resolve these ambiguities or measure F1.

## Denser video and frozen motion probe

The four weak windows have [three-second source timelines](../china-weak-event-timelines/README.md).
These show a yellow stone travelling just after S52's broad window, a red
stone during/after S360, and a yellow stone just after S411. S403 contains
camera/context changes near the later B86 event; the sampled frames do not
show a new stone departing within S403's window. This is a development
interpretation of sampled video, not an independent event label.

The existing, unchanged 1 Hz cap tracker was run over all nine counterless
windows with a fixed search of five seconds before to 15 seconds after each
delivery-window edge. Its [frozen output](../china-all-counterless-motion-probe-first.json)
has supported motion tracks in seven: S52 (yellow), S142 (yellow), S216
(red), S360 (red), S411 (yellow and later red tracks), S427 (red), and S529
(yellow). It finds none for S403 **or S593**. S593 has an independently
observed yellow release and receiving cue, so the absent track demonstrates
that this motion test cannot be a hard reject filter. S360's red motion
conflicts with its provisional yellow event colour and needs direct
source-identity resolution. None of these motion findings changes the
evidence tier or claims physical stone identity.
