#!/usr/bin/env python3
"""
Extract only items whose title contains "night" (case-insensitive) from
videos.json and write them to night_surely.json (de-duplicated + sorted).

Usage:
  python make_night_surely.py [input_json] [output_json]

Defaults:
  input_json  = videos.json
  output_json = night_surely.json
"""

import json
import sys
from pathlib import Path


def stable_key(item: dict) -> tuple:
    # Used for deterministic ordering and de-duplication.
    return (
        (item.get("location") or "").strip(),
        (item.get("title") or "").strip(),
        (item.get("url_1080p") or "").strip(),
        (item.get("url_1080p_hdr") or "").strip(),
        (item.get("url_4k") or "").strip(),
        (item.get("url_4k_hdr") or "").strip(),
    )


def main() -> int:
    inp = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("videos.json")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("night_surely.json")

    data = json.loads(inp.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array, got: {type(data).__name__}")

    filtered = []
    seen = set()

    for item in data:
        title = (item.get("title") or "")
        if "night" not in title.lower():
            continue

        k = stable_key(item)
        if k in seen:
            continue
        seen.add(k)

        filtered.append(item)

    filtered.sort(key=lambda x: ((x.get("location") or ""), (x.get("title") or "")))

    out.write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(filtered)} items -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
