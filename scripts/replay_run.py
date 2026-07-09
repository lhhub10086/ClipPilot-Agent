from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from clip_pilot.harness.replay import load_trace


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a ClipPilot trace summary.")
    parser.add_argument("--trace", required=True)
    args = parser.parse_args()
    trace = load_trace(args.trace)
    summary = [{"step_name": step.get("step_name"), "success": step.get("success"), "tool_name": step.get("tool_name")} for step in trace.get("steps", [])]
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

