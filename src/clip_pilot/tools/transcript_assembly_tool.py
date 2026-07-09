from __future__ import annotations

from pathlib import Path
from typing import Any


def assemble_transcript(editor_timeline: dict[str, Any], markdown_path: str, text_path: str) -> dict[str, Any]:
    md_lines = ["# Final Review Transcript", ""]
    text_lines = []
    for item in editor_timeline.get("timeline_items", []):
        md_lines.extend(
            [
                f"## {item.get('segment_id')} - {item.get('role')}",
                f"Time: {item.get('source_start')} - {item.get('source_end')}",
                f"Why included: {item.get('why_included')}",
                "",
            ]
        )
        if item.get("bridge_before"):
            md_lines.extend([f"Bridge before: {item.get('bridge_before')}", ""])
            text_lines.append(str(item.get("bridge_before")))
        transcript = str(item.get("transcript", "")).strip()
        md_lines.extend([transcript, ""])
        text_lines.append(transcript)
        if item.get("bridge_after"):
            md_lines.extend([f"Bridge after: {item.get('bridge_after')}", ""])
            text_lines.append(str(item.get("bridge_after")))
    md = Path(markdown_path)
    txt = Path(text_path)
    md.write_text("\n".join(md_lines), encoding="utf-8")
    txt.write_text("\n\n".join(text_lines), encoding="utf-8")
    return {"success": True, "backend": "transcript_assembly", "output_path": str(md), "data": {"markdown_path": str(md), "text_path": str(txt), "segment_count": len(editor_timeline.get("timeline_items", []))}}

