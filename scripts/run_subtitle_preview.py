from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from clip_pilot.tools.subtitle_tool import parse_subtitle
from clip_pilot.tools.subtitle_refinement_tool import refine_subtitle_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Run subtitle parsing/refinement preview only; this does not export video.")
    parser.add_argument("--subtitle", required=True, help="Input .vtt or .srt subtitle file.")
    parser.add_argument("--out", required=True, help="Output directory for preview artifacts.")
    parser.add_argument("--language", default="zh")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    parsed = parse_subtitle(args.subtitle)
    cues = parsed.get("data", {}).get("segments", []) if parsed.get("success") else []
    raw_preview = out / "raw_subtitle_preview.json"
    raw_preview.write_text(json.dumps({"cue_count": len(cues), "cues": cues[:50]}, ensure_ascii=False, indent=2), encoding="utf-8")
    refined = refine_subtitle_file(args.subtitle, str(out), language=args.language, use_llm=False)
    print(json.dumps({"raw_preview": str(raw_preview), **refined}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

