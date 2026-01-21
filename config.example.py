# Configuration for Overflight Night Feed Generator
# Copy this file to config.py and customize as needed

# Upstream JSON feed URL
UPSTREAM_JSON_URL = "https://raw.githubusercontent.com/projectivy/overflight/main/videos.json"

# Output file name
OUTPUT_JSON_NAME = "night.json"

# Maximum number of items to process (None = no limit)
MAX_ITEMS = None

# Concurrency settings
MAX_WORKERS = 8

# Request timeout in seconds
REQUEST_TIMEOUT = 30

# Darkness thresholds (lower = darker required)
# Night/Dark acceptance
NIGHT_MEDIAN_THRESHOLD = 0.22
NIGHT_DARK_RATIO_THRESHOLD = 0.65
NIGHT_P75_THRESHOLD = 0.35
NIGHT_DARK_LUMINANCE = 0.18

# Sunset acceptance (stricter than night)
SUNSET_MEDIAN_THRESHOLD = 0.28
SUNSET_P25_THRESHOLD = 0.14
SUNSET_DARK_RATIO_THRESHOLD = 0.55

# Cache settings
CACHE_MAX_AGE_DAYS = 7
