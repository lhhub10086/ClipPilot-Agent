from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from .segment_export_tool import resolve_ffmpeg


def recover_risky_windows(
    *,
    video_path: str,
    risk_report_path: str,
    output_dir: str,
    config: dict[str, Any],
    threshold: float = 0.65,
    max_windows: int = 20,
) -> dict[str, Any]:
    risk_report = json.loads(Path(risk_report_path).read_text(encoding="utf-8"))
    risks = [item for item in risk_report.get("risks", []) if float(item.get("risk_score", 0.0)) >= threshold][:max_windows]
    root = Path(output_dir)
    clips_dir = root / "local_asr_audio"
    clips_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for item in risks:
        result = recover_one_window(video_path=video_path, risk=item, output_dir=str(clips_dir), config=config)
        results.append(result)
    payload = {
        "processed_count": len(results),
        "threshold": threshold,
        "max_windows": max_windows,
        "recoveries": results,
    }
    path = root / "local_asr_recovery.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "backend": "local_asr_recovery", "output_path": str(path), "data": payload}


def recover_one_window(*, video_path: str, risk: dict[str, Any], output_dir: str, config: dict[str, Any]) -> dict[str, Any]:
    start = max(0.0, float(risk.get("start", 0.0)) - 3.0)
    end = float(risk.get("end", 0.0)) + 3.0
    duration = max(0.1, end - start)
    sid = str(risk.get("sentence_id"))
    out = Path(output_dir)
    audio_window_hash = _hash_window(video_path, start, end)
    audio_path = out / f"{sid}_{audio_window_hash}.wav"
    cache_path = out / f"{audio_path.stem}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg:
        result = _failure(sid, risk, str(audio_path), "ffmpeg unavailable")
        cache_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    cmd = [ffmpeg, "-y", "-ss", str(start), "-t", str(duration), "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", str(audio_path)]
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.returncode != 0 or not audio_path.exists():
        result = _failure(sid, risk, str(audio_path), completed.stderr[-1000:])
        cache_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    candidates = []
    try:
        from faster_whisper import WhisperModel

        asr_cfg = config.get("asr", {}) if isinstance(config, dict) else {}
        model_size = asr_cfg.get("recovery_model_size") or asr_cfg.get("model_size", "small")
        model = WhisperModel(model_size, device=asr_cfg.get("device", "cpu"), compute_type=asr_cfg.get("compute_type", "int8"))
        kwargs = {"vad_filter": True, "task": asr_cfg.get("task", "transcribe")}
        if asr_cfg.get("language"):
            kwargs["language"] = asr_cfg["language"]
        if asr_cfg.get("initial_prompt"):
            kwargs["initial_prompt"] = asr_cfg["initial_prompt"]
        segments, _info = model.transcribe(str(audio_path), **kwargs)
        text = "".join(str(seg.text).strip() for seg in segments if str(seg.text).strip())
        if text:
            candidates.append(
                {
                    "backend": "faster_whisper",
                    "model": model_size,
                    "audio_window_hash": audio_window_hash,
                    "text": text,
                    "confidence": 0.7,
                    "language": asr_cfg.get("language", ""),
                    "glossary_used": bool(asr_cfg.get("initial_prompt")),
                }
            )
    except Exception as exc:
        asr_cfg = config.get("asr", {}) if isinstance(config, dict) else {}
        candidates.append(
            {
                "backend": "faster_whisper",
                "model": asr_cfg.get("model_size", "small"),
                "audio_window_hash": audio_window_hash,
                "text": "",
                "confidence": 0.0,
                "language": asr_cfg.get("language", ""),
                "glossary_used": bool(asr_cfg.get("initial_prompt")),
                "error": str(exc),
            }
        )
    result = {
        "sentence_id": sid,
        "window_start": round(start, 3),
        "window_end": round(end, 3),
        "audio_window_hash": audio_window_hash,
        "audio_clip_path": str(audio_path),
        "original_asr": risk.get("text", ""),
        "risk_types": risk.get("risk_types", []),
        "risk_score": risk.get("risk_score"),
        "recovered_candidates": candidates,
    }
    cache_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _failure(sentence_id: str, risk: dict[str, Any], audio_path: str, error: str) -> dict[str, Any]:
    return {
        "sentence_id": sentence_id,
        "audio_clip_path": audio_path,
        "original_asr": risk.get("text", ""),
        "risk_types": risk.get("risk_types", []),
        "risk_score": risk.get("risk_score"),
        "recovered_candidates": [],
        "error": error,
    }


def _hash_window(video_path: str, start: float, end: float) -> str:
    return hashlib.sha256(f"{Path(video_path).resolve()}:{start:.3f}:{end:.3f}".encode()).hexdigest()[:12]

