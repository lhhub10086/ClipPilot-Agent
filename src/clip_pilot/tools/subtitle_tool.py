from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .segment_export_tool import resolve_ffmpeg
from .subtitle_refinement_tool import refine_segments


def parse_vtt(subtitle_path: str) -> dict[str, Any]:
    path = Path(subtitle_path)
    if not path.exists():
        return {"success": False, "error": f"subtitle file not found: {subtitle_path}"}
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n"))
    segments = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        time_line = next((line for line in lines if "-->" in line), "")
        if not time_line:
            continue
        start, end = [part.strip().split()[0] for part in time_line.split("-->", 1)]
        text = " ".join(line for line in lines if "-->" not in line and not line.isdigit() and line.upper() != "WEBVTT")
        text = re.sub(r"<[^>]+>", "", text).strip()
        if text:
            segments.append({"start": parse_time(start), "end": parse_time(end), "text": text})
    return {"success": True, "backend": "vtt_parser", "data": {"segments": segments, "segment_count": len(segments)}}


def parse_srt(subtitle_path: str) -> dict[str, Any]:
    path = Path(subtitle_path)
    if not path.exists():
        return {"success": False, "error": f"subtitle file not found: {subtitle_path}"}
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n"))
    segments = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        time_line = next((line for line in lines if "-->" in line), "")
        if not time_line:
            continue
        start, end = [part.strip().split()[0] for part in time_line.split("-->", 1)]
        text = " ".join(line for line in lines if "-->" not in line and not line.isdigit())
        text = re.sub(r"<[^>]+>", "", text).strip()
        if text:
            segments.append({"start": parse_time(start), "end": parse_time(end), "text": text})
    return {"success": True, "backend": "srt_parser", "data": {"segments": segments, "segment_count": len(segments)}}


def parse_subtitle(subtitle_path: str) -> dict[str, Any]:
    suffix = Path(subtitle_path).suffix.lower()
    if suffix == ".srt":
        return parse_srt(subtitle_path)
    return parse_vtt(subtitle_path)


def load_or_transcribe(video_path: str, subtitle_path: str | None, output_dir: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    if subtitle_path and Path(subtitle_path).exists():
        result = parse_subtitle(subtitle_path)
        if result.get("success"):
            result["output_path"] = subtitle_path
            result["backend"] = f"{result.get('backend')}_input_subtitle"
        return result

    extracted = extract_embedded_subtitle(video_path, output_dir)
    if extracted.get("success"):
        result = parse_subtitle(extracted["output_path"])
        if result.get("success") and result.get("data", {}).get("segment_count", 0) > 0:
            result["backend"] = f"{result.get('backend')}_extracted_subtitle"
            result["output_path"] = extracted["output_path"]
            result.setdefault("data", {})["extracted_stream_index"] = extracted.get("data", {}).get("stream_index")
            return result

    cache = asr_cache_path(video_path, config)
    if cache.exists():
        result = parse_vtt(str(cache))
        if result.get("success"):
            refined = refine_segments(result["data"]["segments"], output_dir, language=(config.get("asr", {}) or {}).get("language", "zh"), raw_subtitle_path=str(cache))
            if refined.get("success"):
                refined["backend"] = "refined_asr_cache"
                return refined
            result["backend"] = "vtt_parser_asr_cache"
            result["output_path"] = str(cache)
            return result
    asr_result = transcribe_video(video_path, output_dir, config)
    if asr_result.get("success"):
        refined = refine_segments(
            asr_result["data"]["segments"],
            output_dir,
            language=(config.get("asr", {}) or {}).get("language", "zh"),
            raw_subtitle_path=asr_result.get("output_path", ""),
        )
        if refined.get("success"):
            refined["backend"] = "refined_asr_transcript"
            refined.setdefault("data", {})["raw_asr_output_path"] = asr_result.get("output_path")
            refined["data"]["source_duration"] = asr_result.get("data", {}).get("source_duration")
            return refined
    return asr_result


def transcribe_video(video_path: str, output_dir: str, config: dict[str, Any]) -> dict[str, Any]:
    source = Path(video_path)
    if not source.exists():
        return {"success": False, "backend": "faster_whisper", "error": f"video file not found: {video_path}"}
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        return {"success": False, "backend": "faster_whisper", "error": f"faster-whisper unavailable and no subtitle provided: {exc}"}

    asr_cfg = config.get("asr", {}) if isinstance(config, dict) else {}
    model_size = asr_cfg.get("model_size", "tiny")
    device = asr_cfg.get("device", "cpu")
    compute_type = asr_cfg.get("compute_type", "int8")
    language = asr_cfg.get("language")
    task = asr_cfg.get("task", "transcribe")
    initial_prompt = asr_cfg.get("initial_prompt")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    vtt_path = out / "source_transcript.vtt"
    cache_path = asr_cache_path(video_path, config)
    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        video_duration = probe_duration(str(source))
        max_full = float(asr_cfg.get("max_full_duration_sec", 900))
        if video_duration > max_full:
            segments, language = transcribe_sampled_chunks(model, str(source), out, video_duration, asr_cfg)
        else:
            transcribe_kwargs = {"vad_filter": True, "task": task}
            if language:
                transcribe_kwargs["language"] = language
            if initial_prompt:
                transcribe_kwargs["initial_prompt"] = initial_prompt
            segments_iter, info = model.transcribe(str(source), **transcribe_kwargs)
            segments = [
                {"start": float(item.start), "end": float(item.end), "text": str(item.text).strip()}
                for item in segments_iter
                if str(item.text).strip()
            ]
            language = language or getattr(info, "language", "")
        if not segments:
            return {"success": False, "backend": "faster_whisper", "error": "ASR produced no subtitle segments"}
        vtt_text = to_vtt(segments)
        vtt_path.write_text(vtt_text, encoding="utf-8")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(vtt_text, encoding="utf-8")
        return {
            "success": True,
            "backend": "faster_whisper",
            "output_path": str(vtt_path),
            "data": {
                "segments": segments,
                "segment_count": len(segments),
                "language": language,
                "task": task,
                "model_size": model_size,
                "duration": max(float(item["end"]) for item in segments),
                "asr_mode": "sampled_chunks" if video_duration > max_full else "full",
                "source_duration": video_duration,
                "cache_path": str(cache_path),
            },
        }
    except Exception as exc:
        return {"success": False, "backend": "faster_whisper", "error": f"ASR failed: {exc}"}


def parse_time(value: str) -> float:
    value = value.replace(",", ".")
    parts = value.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return float(value)


def to_vtt(segments: list[dict[str, Any]]) -> str:
    lines = ["WEBVTT", ""]
    for idx, item in enumerate(segments, start=1):
        lines.append(str(idx))
        lines.append(f"{format_time(float(item['start']))} --> {format_time(float(item['end']))}")
        lines.append(str(item["text"]))
        lines.append("")
    return "\n".join(lines)


def format_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    rest = seconds - hours * 3600 - minutes * 60
    return f"{hours:02}:{minutes:02}:{rest:06.3f}"


def probe_duration(video_path: str) -> float:
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg:
        return 0.0
    completed = subprocess.run([ffmpeg, "-i", video_path], capture_output=True, text=True)
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", completed.stderr + completed.stdout)
    if not match:
        return 0.0
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def transcribe_sampled_chunks(model: Any, video_path: str, out_dir: Path, video_duration: float, asr_cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("ffmpeg unavailable for sampled ASR")
    chunk_seconds = float(asr_cfg.get("sample_chunk_seconds", 45))
    sample_count = int(asr_cfg.get("sample_count", 12))
    if sample_count <= 1:
        starts = [0.0]
    else:
        span = max(video_duration - chunk_seconds, 0.0)
        starts = [round(idx * span / (sample_count - 1), 3) for idx in range(sample_count)]
    all_segments: list[dict[str, Any]] = []
    language = ""
    for idx, start in enumerate(starts, start=1):
        wav = out_dir / f"asr_chunk_{idx:03}.wav"
        command = [
            ffmpeg,
            "-y",
            "-ss",
            str(start),
            "-t",
            str(chunk_seconds),
            "-i",
            video_path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(wav),
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0 or not wav.exists() or wav.stat().st_size <= 0:
            continue
        transcribe_kwargs = {"vad_filter": True, "task": asr_cfg.get("task", "transcribe")}
        if asr_cfg.get("language"):
            transcribe_kwargs["language"] = asr_cfg.get("language")
        if asr_cfg.get("initial_prompt"):
            transcribe_kwargs["initial_prompt"] = asr_cfg.get("initial_prompt")
        segments_iter, info = model.transcribe(str(wav), **transcribe_kwargs)
        language = language or getattr(info, "language", "")
        for item in segments_iter:
            text = str(item.text).strip()
            if not text:
                continue
            all_segments.append({"start": round(start + float(item.start), 3), "end": round(start + float(item.end), 3), "text": text})
    all_segments.sort(key=lambda item: item["start"])
    return all_segments, language


def transcript_text(segments: list[dict[str, Any]], start: float, end: float) -> str:
    return " ".join(item["text"] for item in segments if float(item["end"]) > start and float(item["start"]) < end).strip()


def extract_embedded_subtitle(video_path: str, output_dir: str) -> dict[str, Any]:
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg:
        return {"success": False, "backend": "embedded_subtitle_extract", "error": "ffmpeg unavailable"}
    streams = subtitle_streams(video_path)
    if not streams:
        return {"success": False, "backend": "embedded_subtitle_extract", "error": "no embedded subtitle stream"}
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stream = streams[0]
    stream_index = int(stream["index"])
    srt_path = out / "extracted_subtitle.srt"
    command = [ffmpeg, "-y", "-i", video_path, "-map", f"0:{stream_index}", str(srt_path)]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0 or not srt_path.exists() or srt_path.stat().st_size <= 0:
        return {"success": False, "backend": "embedded_subtitle_extract", "error": completed.stderr[-1000:]}
    return {"success": True, "backend": "embedded_subtitle_extract", "output_path": str(srt_path), "data": {"stream_index": stream_index, "codec_name": stream.get("codec_name")}}


def subtitle_streams(video_path: str) -> list[dict[str, Any]]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return []
    command = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "s",
        "-show_entries",
        "stream=index,codec_name,codec_type:stream_tags=language",
        "-of",
        "json",
        video_path,
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            return []
        return json.loads(completed.stdout or "{}").get("streams", [])
    except Exception:
        return []


def asr_cache_path(video_path: str, config: dict[str, Any]) -> Path:
    source = Path(video_path)
    asr_cfg = config.get("asr", {}) if isinstance(config, dict) else {}
    model_size = str(asr_cfg.get("model_size", "tiny"))
    language = str(asr_cfg.get("language", "auto"))
    task = str(asr_cfg.get("task", "transcribe"))
    config_name = str(asr_cfg.get("config_name") or config.get("config_name") or "default")
    audio_hash = compute_audio_hash(video_path)
    key_payload = {
        "video_path": str(source.resolve()) if source.exists() else str(source),
        "audio_hash": audio_hash,
        "asr_model": model_size,
        "language": language,
        "task": task,
        "config_name": config_name,
    }
    digest = hashlib.sha256(json.dumps(key_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    return Path("outputs") / "asr_cache" / f"{source.stem}.{digest}.vtt"


def compute_audio_hash(video_path: str, bytes_to_read: int = 2_000_000) -> str:
    path = Path(video_path)
    if not path.exists():
        return "missing"
    h = hashlib.sha256()
    h.update(str(path.resolve()).encode("utf-8", errors="ignore"))
    h.update(str(path.stat().st_size).encode())
    with path.open("rb") as handle:
        h.update(handle.read(bytes_to_read))
        if path.stat().st_size > bytes_to_read:
            handle.seek(max(path.stat().st_size - bytes_to_read, 0))
            h.update(handle.read(bytes_to_read))
    return h.hexdigest()[:16]

