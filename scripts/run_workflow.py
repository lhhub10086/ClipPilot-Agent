from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from clip_pilot.workflows import run_content_review_workflow
from clip_pilot.tools.llm_client import load_dotenv
from clip_pilot.harness.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ClipPilot-Agent Workflow Harness.")
    parser.add_argument("--video", required=True)
    parser.add_argument("--subtitle", default="", help="Optional .vtt/.srt path. If omitted, faster-whisper ASR is used.")
    parser.add_argument("--intent", required=True)
    parser.add_argument("--out", default="")
    parser.add_argument("--run-id", default="workflow_run")
    parser.add_argument("--clip-count", type=int, default=None, help="Optional explicit user constraint. Omit for adaptive planner policy.")
    parser.add_argument("--no-llm-planner", action="store_true", help="Explicitly disable planner LLM and record fallback policy usage.")
    parser.add_argument("--export-video", action="store_true", help="Export final_review.mp4 only after semantic timeline validation passes.")
    parser.add_argument("--config", default=str(ROOT / "configs" / "config.default.yaml"))
    args = parser.parse_args()

    load_dotenv(str(ROOT / ".env"))
    if not os.environ.get("LLM_API_KEY") or not os.environ.get("LLM_BASE_URL"):
        raise SystemExit("ClipPilot-Agent requires LLM_API_KEY and LLM_BASE_URL.")

    out_dir = args.out or str(ROOT / "outputs" / args.run_id)
    config = load_config(args.config)
    result = run_content_review_workflow(
        video_path=args.video,
        subtitle_path=args.subtitle or None,
        intent=args.intent,
        out_dir=out_dir,
        config=config,
        run_id=args.run_id,
        clip_count=args.clip_count,
        no_llm_planner=args.no_llm_planner,
        export_video=args.export_video,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

