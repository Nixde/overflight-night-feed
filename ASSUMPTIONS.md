# What I Assumed - Implementation Notes

This document outlines the assumptions and decisions made during implementation.

## Upstream JSON Format Assumptions

Since the exact schema of the upstream `videos.json` wasn't provided, I made these assumptions:

1. **JSON Structure**: Array of objects at root level OR object with `videos`/`items` key
   ```json
   [
     {
       "location": "City, Country",
       "title": "Descriptive Title",
       "url_1080p": "https://...",
       "url_4k": "https://...",
       "url_img": "https://..."
     }
   ]
   ```

2. **Required Fields**: 
   - `location` and `title` are always present (used for metadata classification)
   - At least one video URL field exists (e.g., `url_1080p`, `url_720p`, `url_4k`)

3. **Optional Fields**:
   - Thumbnail/image URL may be in any of: `url_img`, `image`, `thumbnail`, `thumb`, `poster`
   - Multiple video quality options may exist with keys like `url_720p`, `url_1080p`, `url_4k`, `url_2160p`

4. **Fallback Strategy**: 
   - Script searches for any `url_*` field as video source if standard keys missing
   - Prioritizes 1080p over 4K for frame extraction (faster download/processing)

## Darkness Classification Assumptions

### Luminance Calculation
- Used ITU-R BT.709 standard for luminance: `Y = 0.2126R + 0.7152G + 0.0722B`
- Assumed sRGB color space for inputs (standard for web/video)
- Proper gamma correction applied (sRGB → linear conversion)

### Threshold Selection
Based on typical luminance values:
- **0.18**: Standard "middle gray" in photography (50% reflectance)
- **0.22**: Median threshold for night scenes (allows some moonlit scenes)
- **0.28**: Upper limit for dark-ish sunsets (rejects bright golden sunsets)

These values were chosen to be:
- **Conservative**: Better to exclude borderline cases than include bright videos
- **Testable**: Can be tuned based on analysis reports
- **Explainable**: Based on photography/cinematography standards

### Metadata Keywords
- **Assumed** that location/title text is in English (or contains English keywords)
- Keywords chosen based on common Overflight video naming conventions
- Priority given to explicit time-of-day indicators

## Frame Extraction Assumptions

### FFmpeg Availability
- Assumed FFmpeg is installable on all target platforms
- GitHub Actions uses Ubuntu (ffmpeg readily available)
- Local users must install manually (documented in README)

### Frame Selection Strategy
- Extract at 4 seconds to avoid black intro frames (common in video files)
- Single frame sufficient for representative analysis (vs multi-frame averaging)
- Tradeoff: Speed vs accuracy (single frame = faster, less bandwidth)

### Video Download Optimization
- Used FFmpeg's ability to seek before downloading when possible
- Some servers don't support range requests - fallback to full download
- 60-second timeout balances patience with avoiding hangs

## Concurrency Assumptions

### Worker Count
- Default 8 workers balances throughput with resource usage
- Assumed modern multi-core CPU (4+ cores)
- Network I/O bound (not CPU bound), so higher concurrency acceptable

### Rate Limiting
- Assumed no aggressive rate limiting on upstream server
- Added retries with exponential backoff as safety measure
- Session reuse for connection pooling

## Caching Strategy

### Cache Key Generation
- SHA256 hash of URL ensures unique keys
- Assumed URLs are stable (same URL = same content)
- 7-day cache expiry balances storage with freshness

### Cache Location
- Default to system temp directory (cross-platform)
- User can override with `--cache-dir`
- Cache persists across runs for efficiency

## Error Handling Philosophy

### Fail-Closed Approach
- When in doubt, **reject** (exclude from feed)
- Better to have fewer high-quality night videos than include uncertain ones
- Only exception: Explicit "night" keyword + strong evidence

### Graceful Degradation
- Individual item failures don't stop entire pipeline
- Log errors but continue processing
- Final output includes only successfully analyzed items

## GitHub Actions Assumptions

### Repository Permissions
- Assumed user has admin access to enable Actions
- Workflow needs write permissions to commit changes
- Bot commits excluded from triggering workflow (prevents loops)

### Artifact Storage
- 30-day retention for analysis reports (GitHub default)
- Reports not committed to repo (would bloat history)
- Users can download from Actions tab if needed

## Output Format Assumptions

### JSON Schema Preservation
- Output `night.json` maintains exact same schema as input
- All fields preserved (location, title, all URL fields)
- Only filtering applied, no transformation

### Ordering
- Deterministic ordering by (location, title) for stable diffs
- Git can track changes cleanly
- Easier to review what changed between runs

## Performance Targets

Estimated for typical 100-item feed:
- **With thumbnails**: ~2-3 minutes (mostly network I/O)
- **Without thumbnails**: ~5-10 minutes (video frame extraction)
- **Cache hits**: ~1 minute (only luminance calculation)

Scales linearly with item count (concurrent processing).

## Known Limitations & Future Improvements

### Current Limitations
1. **Single-frame analysis**: Could be fooled by brief bright moments
2. **Keyword language**: Only English keywords supported
3. **No scene detection**: Doesn't detect scene changes in video
4. **Binary classification**: No confidence scores or ranking

### Potential Improvements
1. **Multi-frame sampling**: Analyze 3-5 frames and average/median
2. **ML classification**: Train CNN on labeled night/day aerial videos
3. **Scene detection**: Use FFmpeg scene detection to find representative frame
4. **Adaptive thresholds**: Adjust based on location metadata (e.g., polar regions)
5. **Temporal analysis**: Consider time of year + location for realistic sunset times
6. **Quality scoring**: Rank videos by "darkness quality" not just binary accept/reject

## Design Decisions Rationale

### Why Not Use ML/AI Models?
- **Simplicity**: Traditional CV + thresholds are explainable and debuggable
- **No training data**: Would need labeled dataset of night/day aerial videos
- **Computational cost**: Current approach works on any machine without GPU
- **Deterministic**: Same input always produces same output (testable)

### Why FFmpeg Instead of OpenCV?
- **Ubiquitous**: FFmpeg available on all platforms
- **Efficient**: Optimized for video processing
- **Network-aware**: Can handle streaming URLs
- **Minimal dependencies**: Reduces Python package bloat

### Why Concurrent Processing?
- **I/O bound**: Network requests and disk I/O are bottlenecks
- **Parallelizable**: Items are independent
- **Faster results**: 8x speedup with 8 workers (approximately)

### Why GitHub Actions?
- **Free**: Unlimited for public repos
- **Integrated**: Built into GitHub platform
- **Reliable**: Managed infrastructure
- **Transparent**: Logs publicly visible

## Testing Strategy

### Manual Testing
- Tested with sample data containing known night/day videos
- Verified thresholds match human perception
- Checked edge cases (twilight, aurora, neon cities)

### Automated Testing
- GitHub Actions workflow serves as integration test
- Dry-run mode for safe testing
- Analysis reports provide validation data

### User Testing
- README includes test instructions
- `test_pipeline.py` for quick verification
- Reports enable users to tune thresholds for their preferences

## Documentation Philosophy

- **README**: User-focused, getting started, common tasks
- **SETUP.md**: Step-by-step for first-time setup
- **Code comments**: Implementation details for developers
- **This file**: Assumptions and design rationale

All documentation aims to be:
- **Actionable**: Includes commands to run
- **Complete**: Covers all common scenarios
- **Maintainable**: Easy to update as code evolves
