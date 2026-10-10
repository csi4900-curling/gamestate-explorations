# T11 handle visibility, not a revolution count

The [contact sheet](t11-handle-contact-sheet.png) samples the receiving camera
at 0.5-second intervals from clip time 54–57 s. Crops are centered on the
existing T11 cap predictions and enlarged with nearest-neighbour pixels.
The handle orientation visibly changes in several unobstructed frames, while
nearby stones and motion blur obscure it in others. Seven sparse frames cannot
establish an unaliased rotation count, and the center trajectory alone cannot
recover angular motion.

The [denser source-frame sheet](t11-handle-dense-contact-sheet.png) samples
54.0–57.0 s every 0.1 s (every third frame of the 30 fps clip). Its
[provenance](dense-provenance.json) records the decoded frame indices and the
crop centers interpolated from existing half-second stone predictions. It
confirms visible handle changes through the approach, but the top feature is
blurred near 55 s and overlaps a red stone and players later in the sequence.
This remains a visibility check, not an annotated orientation track or a
defensible revolution count. The requested sample spacing is also too sparse
to rule out phase aliasing without an angular-speed bound.

A measurement stage would need dense source frames, image registration,
stone/handle segmentation, an asymmetric orientation feature, temporal angle
unwrapping, occlusion handling, and uncertainty or abstention where the
orientation is ambiguous. Any revolution estimate should be measured from
orientation over time, not fitted from lateral curl. See the primary
[precision kinematic study](https://arxiv.org/abs/2203.00347), which used two
marks on the stone to measure center position and rotation separately.

Reproduce with `feasibility/scripts/python.sh
prototype/scripts/build_t11_spin_feasibility_sheet.py` and
`feasibility/scripts/python.sh prototype/scripts/build_t11_dense_spin_sheet.py`.
The provenance files record exact input hashes and sample times.
