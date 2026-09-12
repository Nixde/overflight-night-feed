# Overflight tools and integrations

Reviewed 2026-09-12 from builder source, requirements and scheduled workflow. These instructions describe development prerequisites, not installed software or verified current automation health.

## Local toolchain

Use Git, Python 3.11 or a tested compatible version, dependencies from `requirements.txt`, and ffmpeg/ffprobe for media work. The inspected requirements include requests, Pillow, NumPy, tqdm and urllib3; pytest is a separate development prerequisite. Use an isolated environment and avoid upgrading runtime dependencies implicitly.

```sh
python -m pytest tests/test_classifier.py -q
```

Use synthetic frames and local fixtures before network/media integration runs. Check ffmpeg and ffprobe availability explicitly when the task needs real decoding. Metrics and reports should be attributable to the input data and classifier configuration. Save development outputs outside production feed paths.

`build_night_json.py` can create report files even during module setup and generation can fetch media. Do not call it as a harmless syntax test. The inspected builder consumes a local `videos.json`, while the workflow publishes generated `night.json` and reports. Preserve that distinction and review broader test scripts for side effects before execution.

## MCP

Only an optional GitHub integration is configured, disabled and requesting server-side read-only repository/issue/PR/Actions tools. Use a repository-scoped `GITHUB_MCP_TOKEN` outside source control or reuse the global connection. Git/gh can inspect workflow runs and artifacts. The inspected support-file paths do not match the generator workflow's push filters.

No browser, Blender, image-generation or generic filesystem MCP is required to calculate darkness metrics or run classifier tests. Native Pillow/NumPy and ffmpeg remain the testable implementation path. Reuse the global OpenAI documentation MCP for Codex questions without adding unnecessary servers.

Trust the checkout and restart Codex to verify `night_feed_*` agent and skill discovery. Model, effort and execution permissions remain inherited. No MCP installation or live feed publication is performed by these files.

References: https://developers.openai.com/codex/skills ; https://developers.openai.com/codex/multi-agent ; https://developers.openai.com/codex/mcp ; https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md .
