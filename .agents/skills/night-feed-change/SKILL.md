---
name: night-feed-change
description: Develop Overflight darkness classification, media probing, feed generation or workflow checks using controlled fixtures. Not a request to regenerate or publish the live feed.
---

# Night-feed change

Read the changed classifier or builder path, `tests/test_classifier.py`, `pytest.ini` and the relevant workflow. Establish input identity and the intended change in metric or output behavior before editing.

Use synthetic images and saved frame fixtures to cover daylight veto, border/letterbox handling, percentile metrics, mixed-brightness frames and decode failures. Keep thresholds explicit and compare classifications before and after the change. Do not optimize only for a larger accepted-item count.

Use `python -m pytest tests/test_classifier.py -q` with the runtime dependencies and pytest available. Inspect broader `test_pipeline.py` before running it; a pipeline test may need media and create output. Full generation is separate from unit testing and must use reviewed input and temporary output for a development run.

The inspected builder reads local `videos.json`; verify source freshness explicitly instead of assuming the URL constant fetches it. Preserve IDs, output structure and historical files. Review failure handling before replacing `night.json`; an empty or partial result is not automatically a valid publication.

Use native image/video tooling from `.codex/TOOLS.md`. Report exact tests, inputs, threshold changes and sampled visual evidence. Do not claim published-feed or scheduled-workflow success without observing it.
