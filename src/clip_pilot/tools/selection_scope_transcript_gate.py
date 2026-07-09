from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path
from typing import Any

from .segment_export_tool import resolve_ffmpeg


REVIEW_FIELDS = [
    "sentence_id",
    "start",
    "end",
    "context_start",
    "context_end",
    "audio_clip_path",
    "optional_video_clip_path",
    "context_before",
    "original_text",
    "candidate_texts",
    "context_after",
    "risk_types",
    "confidence",
    "selected_by_editor",
    "required_for_current_edit",
    "corrected_text",
    "review_status",
]


def run_selection_scope_gate(
    *,
    selector_response_path: str | None = None,
    selector_response: dict[str, Any] | None = None,
    semantic_blocks_path: str,
    editing_units_path: str | None,
    asr_risk_report_path: str,
    transcript_resolution_path: str | None,
    output_path: str,
    video_path: str | None = None,
    sentence_units_path: str | None = None,
    manual_review_csv_path: str | None = None,
    manual_review_assets_dir: str | None = None,
    generate_audio_assets: bool = True,
) -> dict[str, Any]:
    selector = selector_response or _read_json(selector_response_path or "").get("selector_response", _read_json(selector_response_path or ""))
    blocks = _read_json(semantic_blocks_path).get("semantic_blocks", [])
    editing_units = _read_json(editing_units_path or "").get("editing_units", []) if editing_units_path else []
    risk_report = _read_json(asr_risk_report_path)
    resolution = _read_json(transcript_resolution_path or "") if transcript_resolution_path else {}
    risk_by_sentence = {str(item.get("sentence_id")): item for item in risk_report.get("risks", []) if item.get("sentence_id")}
    unresolved_by_sentence = _unresolved_from_resolution(resolution, risk_by_sentence)

    selected_block_ids = set(_selected_block_ids(selector))
    selected_blocks = [block for block in blocks if block.get("block_id") in selected_block_ids]
    selected_sentence_ids = set()
    for block in selected_blocks:
        selected_sentence_ids.update(str(sid) for sid in block.get("sentence_ids", []))
    for unit in editing_units:
        if unit.get("selected_by_editor") or unit.get("editing_unit_id") in set(selector.get("selected_editing_unit_ids", [])):
            selected_sentence_ids.update(str(sid) for sid in unit.get("sentence_ids", []))

    selected_unresolved = sorted(sid for sid in selected_sentence_ids if sid in unresolved_by_sentence)
    risky_selected_blocks = [block for block in selected_blocks if set(map(str, block.get("sentence_ids", []))) & set(selected_unresolved)]
    safe_alternatives = [
        block
        for block in blocks
        if block.get("block_id") not in selected_block_ids
        and not set(map(str, block.get("sentence_ids", []))) & set(unresolved_by_sentence)
        and block.get("block_type") not in {"filler", "transition"}
    ]

    if not selected_unresolved:
        status = "auto_pass_with_exclusions" if risk_by_sentence else "auto_pass"
        editing_allowed = True
        blocked_reason = None
    elif safe_alternatives:
        status = "needs_selector_retry"
        editing_allowed = False
        blocked_reason = "selected_scope_has_replaceable_unresolved_asr"
    else:
        status = "manual_review_required"
        editing_allowed = False
        blocked_reason = "selected_scope_unresolved_asr"

    report = {
        "selected_scope_lexical_valid": not selected_unresolved,
        "selected_scope_unresolved_count": len(selected_unresolved),
        "selected_scope_unresolved_sentence_ids": selected_unresolved,
        "editing_allowed": editing_allowed,
        "status": status,
        "blocked_reason": blocked_reason,
        "global_unresolved_count": len(risk_by_sentence),
        "excluded_global_unresolved_sentence_ids": sorted(sid for sid in risk_by_sentence if sid not in selected_unresolved),
        "risky_selected_block_ids": [block.get("block_id") for block in risky_selected_blocks],
        "safe_alternative_block_ids": [block.get("block_id") for block in safe_alternatives[:10]],
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if manual_review_csv_path:
        write_manual_review_queue(
            sentence_units_path=sentence_units_path,
            asr_risk_report_path=asr_risk_report_path,
            transcript_resolution_path=transcript_resolution_path,
            output_csv_path=manual_review_csv_path,
            video_path=video_path,
            assets_dir=manual_review_assets_dir,
            required_sentence_ids=selected_unresolved,
            generate_audio_assets=generate_audio_assets,
        )

    return {"success": True, "backend": "selection_scope_transcript_gate", "output_path": str(path), "data": report}


def write_manual_review_queue(
    *,
    sentence_units_path: str | None,
    asr_risk_report_path: str,
    transcript_resolution_path: str | None,
    output_csv_path: str,
    video_path: str | None = None,
    assets_dir: str | None = None,
    required_sentence_ids: list[str] | set[str] | None = None,
    generate_audio_assets: bool = True,
) -> dict[str, Any]:
    units = _read_json(sentence_units_path or "").get("sentence_units", [])
    unit_by_id = {str(unit.get("sentence_id")): unit for unit in units}
    risks = _read_json(asr_risk_report_path).get("risks", [])
    resolutions = _read_json(transcript_resolution_path or "").get("resolutions", []) if transcript_resolution_path else []
    resolution_by_id = {str(item.get("sentence_id")): item for item in resolutions}
    required = set(required_sentence_ids or [])
    all_risk_ids = {str(risk.get("sentence_id")) for risk in risks if risk.get("sentence_id")}
    rows = []
    for risk in risks:
        sid = str(risk.get("sentence_id"))
        unit = unit_by_id.get(sid, {})
        resolution = resolution_by_id.get(sid, {})
        context_start = max(0.0, float(risk.get("start") or unit.get("start") or 0.0) - 5.0)
        context_end = float(risk.get("end") or unit.get("end") or 0.0) + 5.0
        required_for_current_edit = sid in required
        audio_path = ""
        if required_for_current_edit and generate_audio_assets and video_path and assets_dir:
            audio_path = _extract_context_audio(video_path, sid, context_start, context_end, assets_dir)
        rows.append(
            {
                "sentence_id": sid,
                "start": risk.get("start", unit.get("start", "")),
                "end": risk.get("end", unit.get("end", "")),
                "context_start": round(context_start, 3),
                "context_end": round(context_end, 3),
                "audio_clip_path": audio_path,
                "optional_video_clip_path": "",
                "context_before": "",
                "original_text": risk.get("text") or unit.get("refined_text", ""),
                "candidate_texts": json.dumps([resolution.get("selected_text")] if resolution.get("selected_text") else [], ensure_ascii=False),
                "context_after": "",
                "risk_types": "|".join(risk.get("risk_types", [])),
                "confidence": resolution.get("confidence", ""),
                "selected_by_editor": required_for_current_edit,
                "required_for_current_edit": required_for_current_edit,
                "corrected_text": "",
                "review_status": "pending" if required_for_current_edit or sid in all_risk_ids else "",
            }
        )
    path = Path(output_csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return {"success": True, "backend": "manual_review_queue", "output_path": str(path), "data": {"row_count": len(rows), "required_count": len(required)}}


def _selected_block_ids(selector: dict[str, Any]) -> list[str]:
    block_ids: list[str] = []
    for topic in selector.get("selected_topics", []):
        block_ids.extend(str(block_id) for block_id in topic.get("candidate_block_ids", []))
    return block_ids


def _unresolved_from_resolution(resolution: dict[str, Any], risk_by_sentence: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    unresolved = dict(risk_by_sentence)
    for item in resolution.get("resolutions", []):
        sid = str(item.get("sentence_id"))
        if item.get("resolution_status") == "resolved" and sid in unresolved:
            unresolved.pop(sid, None)
    return unresolved


def _extract_context_audio(video_path: str, sentence_id: str, start: float, end: float, assets_dir: str) -> str:
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg:
        return ""
    out_dir = Path(assets_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{sentence_id}_context.wav"
    duration = max(0.1, end - start)
    cmd = [ffmpeg, "-y", "-ss", str(start), "-t", str(duration), "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", str(out_path)]
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.returncode != 0 or not out_path.exists():
        return ""
    return str(out_path)


def _read_json(path: str) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

