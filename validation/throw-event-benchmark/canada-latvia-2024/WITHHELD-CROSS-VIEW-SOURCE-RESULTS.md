# Withheld left motions paired to right-camera proposals

The full Latvia area-aware join pairs at least one right proposal with **eight of the 47 withheld left motions**, grouped into **four** ambiguous cross-view episodes. Their source pixels are now preserved in a [marked source review packet](withheld-cross-view-source-audit/manifest.json). Each of the 13 candidate positions has a full 360p source frame and enlarged marked crop; the manifest records the source-video, input-artifact, runner and image hashes. This review was selected **after** seeing the proposals and performed by the detector developer, so it is diagnostic rather than independent event validation.

| Episode | Left ↔ right proposal | Source-pixel finding |
| --- | --- | --- |
| E023 | S22/S23 ↔ A046 | Jacket logo, face and sleeve/clothing at the marked positions |
| E078 | [S76](withheld-cross-view-source-audit/S76.jpg) ↔ [A235](withheld-cross-view-source-audit/A235.jpg) | The **only one-to-one withheld pair** follows person/wheelchair pixels in both views during stone rearrangement |
| E101 | S99/S100 ↔ A332/A333 | A face and small red/gray pixels under wheelchairs; the low pixels are visually ambiguous |
| E146 | S116/S117/S118 ↔ A483 | Faces/head and small red/gray pixels near a wheelchair; the low pixels are visually ambiguous |

At the marked positions, **nine pixels are clearly person, clothing or wheelchair material**; **four low red/gray positions remain ambiguous**. The exact S76/A235 pairing is especially instructive: temporal order, colour and direction produce a unique cross-camera match, yet both marked objects are nonstone. Thus a one-to-one time/colour join is a **review cue**, not sufficient evidence to rescue a withheld motion as a physical throw. The three grouped episodes also cannot be counted as one throw each: multiple candidate IDs map to the same right path, or two right paths occur nearly together.

The previously frozen [ring-plus-underpoint context screen](full-right-area-context-pair-first-transfer.json) placed **all five** paired right proposals (A046, A235, A332, A333 and A483) in its cluttered review tier. That supports prioritizing this entire subset for skepticism. The same screen also flagged the source-visible moving stone A444 as cluttered, so a cluttered result cannot be used as an unconditional veto on other events.

The packet does not prove that no physical delivery happened anywhere in these broad source intervals. It only checks the saved candidate pixels and nearby source frames. No withheld candidate is promoted, no event F1 is revised, and the [full-match candidate union](FULL-MATCH-AREA-CANDIDATE-UNION.md) still preserves all 47 abstentions. A reliable rescue would need same-stone evidence through more consecutive frames, separation from people/equipment, and a later independent event reference.

Reproduce with [`audit_latvia_withheld_cross_view_source.py`](../../../prototype/scripts/audit_latvia_withheld_cross_view_source.py), using the saved area-aware episode join, raw left event screen, right proposal scan and full 360p source. The script refuses to overwrite the packet.
