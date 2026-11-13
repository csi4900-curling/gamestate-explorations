# Source review of Czech surrounding-motion rejections

The [contact-sheet manifest](manifest.json) pins 54 sampled source frames,
three at the first, middle, and last raw-track points for each of the 18
`large_surrounding_motion` rejections. Yellow boxes show **the raw detector's
tracked pixels**, not a verified physical stone center. The review below
classifies those tracked pixels from the marked sheets. It does not label
every physical throw in the surrounding video, and it is not independent
validation.

| Candidate | Tracked feature in sampled source frames |
| --- | --- |
| [S04](s04-source-track.jpg) | Moving red stone |
| [S08](s08-source-track.jpg) | White player's upper body |
| [S11](s11-source-track.jpg) | White player's upper body |
| [S13](s13-source-track.jpg) | Moving red stone |
| [S16](s16-source-track.jpg) | Staff member's upper body |
| [S17](s17-source-track.jpg) | White player's upper body |
| [S22](s22-source-track.jpg) | Red player's hat |
| [S25](s25-source-track.jpg) | White player's upper body |
| [S27](s27-source-track.jpg) | White player's hat |
| [S45](s45-source-track.jpg) | Wheelchair/player feature during end reset |
| [S46](s46-source-track.jpg) | White player's upper body during end reset |
| [S47](s47-source-track.jpg) | White player's upper body during end reset |
| [S54](s54-source-track.jpg) | Staff member's upper body |
| [S70](s70-source-track.jpg) | White player's upper body |
| [S71](s71-source-track.jpg) | White player's upper body |
| [S96](s96-source-track.jpg) | Player/wheelchair attached feature |
| [S98](s98-source-track.jpg) | Staff member's upper body |
| [S144](s144-source-track.jpg) | Wheelchair/player feature after play |

Thus the sampled raw tracks show **2 moving stones and 16 non-stone
features**. A different real stone can be elsewhere in the frame at the same
time; the classification applies only to the boxed track. The unmarked
[S04](../s04-raw-source-review/manifest.json) and
[S13](../s13-raw-source-review/manifest.json) source packets preserve fuller
motion context for the two stone cases.

The motion threshold is 1,250 changed pixels. S13 and S04 scored 1,253 and
1,257; the lowest remaining rejection in this set scored 1,329. This
development sample illustrates a brittle boundary but does **not** justify
retuning the threshold: the contact sheets were selected by that same gate,
and their labels are neither independent nor cross-recording validation.
