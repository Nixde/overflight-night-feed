# Overflight Night Feed engineering

Maintain a reproducible night-only video feed with explainable classification. Use the `night-feed-change` skill and `.codex/TOOLS.md`; inherit general working preferences from user-level Astra guidance.

Inspect `scripts/media_probe.py`, `scripts/build_night_json.py`, relevant tests and workflow before changing classification or publishing behavior. Preserve daylight veto, multi-frame evaluation, border handling, source identifiers and consumer-compatible output. A dark thumbnail, keyword or old generated feed does not establish every frame as suitable.

Use synthetic images, local fixtures and temporary output for development. Full generation can fetch media, create reports and replace feed files. Do not regenerate or publish production feeds, dispatch scheduled jobs or change thresholds merely to make a test pass. Keep source input, classifier settings and output evidence tied together.

Preserve existing feed data, reports and historical source references. Respect media redistribution rights and source access limits. Report actual classifier tests, input provenance and visual spot checks separately; generated output or a workflow definition is not proof of a successful current run.
