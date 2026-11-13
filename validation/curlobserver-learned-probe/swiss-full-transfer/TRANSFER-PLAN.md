# Frozen full-recording Sweden–Switzerland 2022 development transfer

Source: exposed 0–7734-second recording `ZJAMdkERdpE`, SHA-256
`49429abdd3796e8240e66c201d37e94e71a7bb6225890b2492bea26d2f70d560`.
Earlier 1200–1500-second Swiss shot labels and another partial throw review
exist, so this is **not** an untouched or independent match-level test.

Before this full-match run, freeze the existing 19-stage China/Slovakia
pipeline, with shot-origin model
`shot-origin-pair-v1/model-excluding-swiss-dev.npz` SHA-256
`9586973ae7cbc632c65e3b757015f30d1d2fcf38190d50c39bb43c4ed827661a`,
and CurlObserver learned stone model `model-v1/model.npz` SHA-256
`81421342467a0ab8d93f4e08829e5928eefbf98c655b2f3a436493ec002feb63`.
Run the unchanged event-ledger pipeline, then the separate identity audit
(`prototype/event_identity_audit.py` SHA-256
`967b7f3840ae1a33a5f088732995ec6b245e48262db2654868624d7fe3760745`).
The audit only records possible colour and delayed-counter links; it does
not change candidate events.

The audit's exploratory earliest-following-motion colour hypothesis was
developed after source review on Slovakia and China. It requires a sustained
learned track of at least 20 points starting 0–3 seconds after a visual
candidate's shot window, and a lead of at least 3 seconds over any other
colour. Any Swiss result is transfer evidence for this hypothesis, not
independent proof of throw-event F1.

For a separate source-only check, use the first three eight-hex-digit
words of the source SHA-256, modulo 25 and multiplied by 300 seconds.
This preselects 2100–2400, 6600–6900 and 2700–3000 seconds. Review
five-second full-frame samples and freeze coarse event windows before
inspecting full-transfer candidate rows in those intervals. Preserve
uncertain/off-camera deliveries separately. Temporal and colour-aware
one-to-one scores remain agent-authored development diagnostics.
