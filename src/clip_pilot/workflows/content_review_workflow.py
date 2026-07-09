from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from clip_pilot.agent.coherence_judge import run_coherence_judge
from clip_pilot.agent.content_selector import run_content_selector
from clip_pilot.agent.planner import build_task_plan
from clip_pilot.agent.timeline_editor import run_timeline_editor
from clip_pilot.agent.timeline_repair import judge_passed, run_timeline_repair_round
from clip_pilot.harness import ArtifactValidator, RunContext, StepExecutor, ToolRegistry, TraceRecorder
from clip_pilot.schemas.edit_plan_schema import validate_edit_plan
from clip_pilot.schemas.timeline_schema import build_timeline, validate_timeline
from clip_pilot.tools import final_subtitle_tool, final_video_tool, llm_tool, policy_validator, review_sheet_tool, segment_export_tool, subtitle_tool, title_card_tool, transcript_quality_tool
from clip_pilot.tools import coherence_validator, semantic_block_tool, sentence_segment_tool, transcript_assembly_tool


def run_content_review_workflow(
    *,
    video_path: str,
    subtitle_path: str | None,
    intent: str,
    out_dir: str,
    config: dict[str, Any] | None = None,
    run_id: str = "workflow_run",
    clip_count: int | None = None,
    no_llm_planner: bool = False,
    export_video: bool = False,
) -> dict[str, Any]:
    context = RunContext(video_path=video_path, subtitle_path=subtitle_path or "", intent=intent, out_dir=out_dir, run_id=run_id, clip_count=clip_count, config=config or {})
    context.state["export_video"] = export_video
    context.prepare_dirs()
    trace = TraceRecorder()
    executor = StepExecutor(trace)
    registry = build_registry(context)

    executor.run(
        step_name="input_validation",
        tool_name="input_validator",
        input_summary={"video_path": video_path, "subtitle_path": subtitle_path or ""},
        func=lambda: {"success": Path(video_path).exists(), "backend": "input_validator", "data": {"video_exists": Path(video_path).exists()}, "error": None if Path(video_path).exists() else "video file not found"},
    )
    executor.run(step_name="intent_parse", tool_name="intent_parser", input_summary={"intent_chars": len(intent)}, func=lambda: {"success": True, "data": {"intent": intent}})
    subtitle_result = executor.run(step_name="subtitle_parse", tool_name="subtitle_tool", input_summary={"subtitle_path": subtitle_path or "", "video_path": video_path}, func=lambda: registry.get("subtitle_parse")())
    transcript = subtitle_result["data"]["segments"]
    context.state["transcript"] = transcript
    context.state["subtitle_output_path"] = subtitle_result.get("output_path") or subtitle_path or ""
    context.state["subtitle_backend"] = subtitle_result.get("backend", "")

    subtitle_metadata = {"subtitle_path": context.state["subtitle_output_path"], "segment_count": len(transcript), "duration": max([float(item["end"]) for item in transcript], default=0.0)}
    quality_result = executor.run(
        step_name="transcript_quality_check",
        tool_name="transcript_quality_tool",
        input_summary={"segment_count": len(transcript), "subtitle_path": context.state["subtitle_output_path"], "backend": context.state["subtitle_backend"]},
        func=lambda: transcript_quality_tool.check_transcript_quality(
            segments=transcript,
            video_duration=float(subtitle_result.get("data", {}).get("source_duration") or subtitle_metadata["duration"]),
            output_path=str(context.output_path("transcript_quality_report.json")),
            subtitle_path=context.state["subtitle_output_path"],
            backend=context.state["subtitle_backend"],
        ),
    )
    context.state["transcript_quality"] = quality_result["data"]
    if not quality_result["data"].get("transcript_valid"):
        context.state["export_gate_decision"] = {
            "video_export_allowed": False,
            "export_requested": bool(export_video),
            "judge_final_score": None,
            "judge_passed": False,
            "repair_rounds": 0,
            "blocked_reason": "transcript_quality_failed",
        }
        context.output_path("export_gate_decision.json").write_text(json.dumps(context.state["export_gate_decision"], ensure_ascii=False, indent=2), encoding="utf-8")
        summary = write_summary(context)
        trace.record({"step_name": "artifact_validation", "tool_name": "artifact_validator", "success": True, "artifact_type": "validation_report_json", "input_summary": {"out_dir": str(context.root)}, "output_summary": {"pending": True}, "output_path": str(context.output_path("validation_report.json")), "error": None, "duration_seconds": 0.0})
        trace.save(context.output_path("trace.json"))
        validation = ArtifactValidator().validate(str(context.root), {"success": True, "backend": "blocked_by_transcript_quality", "data": {}})
        context.output_path("validation_report.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
        trace.steps[-1]["success"] = bool(validation["harness_behavior_valid"])
        trace.steps[-1]["output_summary"] = validation
        trace.steps[-1]["error"] = None if validation["harness_behavior_valid"] else validation.get("blocked_reason")
        trace.save(context.output_path("trace.json"))
        if not validation["harness_behavior_valid"]:
            raise RuntimeError(f"artifact validation failed: {validation}")
        return {**summary, "edit_plan": "", "trace": str(context.output_path("trace.json")), "validation_report": str(context.output_path("validation_report.json"))}

    task_plan = executor.run(
        step_name="planner_llm_call",
        tool_name="llm_planner",
        input_summary={"intent_chars": len(intent), "subtitle_duration": subtitle_metadata["duration"], "subtitle_segments": len(transcript)},
        func=lambda: _planner_tool_result(
            build_task_plan(
                intent=intent,
                video_metadata={"video_path": video_path},
                subtitle_metadata=subtitle_metadata,
                config=context.config,
                user_constraints={"target_segments": clip_count} if clip_count else {},
                output_dir=str(context.root),
                no_llm_planner=no_llm_planner,
            )
        ),
    )["data"]["task_plan"]
    context.state["task_plan"] = task_plan

    sentences = executor.run(step_name="sentence_segmentation", tool_name="sentence_segment_tool", input_summary={"cue_count": len(transcript)}, func=lambda: registry.get("sentence_segmentation")())["data"]["sentences"]
    context.state["sentences"] = sentences
    blocks = executor.run(step_name="semantic_block_generation", tool_name="semantic_block_tool", input_summary={"sentence_count": len(sentences)}, func=lambda: registry.get("semantic_block_generation")())["data"]["blocks"]
    context.state["semantic_blocks"] = blocks

    selector = executor.run(step_name="selector_llm_call", tool_name="content_selector", input_summary={"block_count": len(blocks)}, func=lambda: registry.get("selector_llm_call")())["data"]["selector_response"]
    context.state["selector_response"] = selector
    editor_timeline = executor.run(step_name="editor_llm_call", tool_name="timeline_editor", input_summary={"selected_topics": len(selector.get("selected_topics", []))}, func=lambda: registry.get("editor_llm_call")())["data"]["editor_timeline"]
    context.state["editor_timeline"] = editor_timeline

    transcript_result = executor.run(step_name="final_review_transcript_generation", tool_name="transcript_assembly_tool", input_summary={"segments": len(editor_timeline.get("timeline_items", []))}, func=lambda: registry.get("final_review_transcript_generation")())
    context.state["final_review_transcript_path"] = transcript_result["data"]["markdown_path"]
    judge = executor.run(step_name="judge_llm_call_round_1", tool_name="coherence_judge", input_summary={"segments": len(editor_timeline.get("timeline_items", [])), "repair_round": 0}, func=lambda: registry.get("judge_llm_call")(1, context.root))["data"]["judge_response"]
    context.state["initial_judge_response"] = judge
    context.state["final_judge_response"] = judge
    context.state["repair_rounds"] = 0
    context.state["repair_loop_triggered"] = False
    context.state["repair_success"] = bool(judge_passed(judge))
    context.state["repair_round_summaries"] = []
    policy_result = executor.run(
        step_name="policy_validation_round_1",
        tool_name="policy_validator",
        input_summary={"segments": len(editor_timeline.get("timeline_items", [])), "judge_passed": judge_passed(judge)},
        func=lambda: policy_validator.validate_policy(
            task_plan=context.state["task_plan"],
            editor_timeline=context.state["editor_timeline"],
            transcript_markdown_path=context.state["final_review_transcript_path"],
            output_path=str(context.output_path("policy_validation_report.json")),
        ),
    )
    current_policy = policy_result["data"]
    context.state["policy_validation_report"] = current_policy
    context.state["policy_valid"] = bool(current_policy.get("policy_valid"))
    context.state["policy_repair_triggered"] = False

    max_repair_rounds = 3
    current_judge = judge
    for round_index in range(1, max_repair_rounds + 1):
        if judge_passed(current_judge) and bool(current_policy.get("policy_valid")):
            context.state["repair_success"] = True
            break
        context.state["repair_loop_triggered"] = True
        if not current_policy.get("policy_valid", True):
            context.state["policy_repair_triggered"] = True
        repair_result = executor.run(
            step_name=f"timeline_repair_round_{round_index}",
            tool_name="timeline_editor_repair",
            input_summary={
                "judge_score": current_judge.get("score"),
                "major_problem_count": len(current_judge.get("major_problems", [])),
                "policy_valid": current_policy.get("policy_valid"),
                "policy_violation_count": len(current_policy.get("violations", [])),
                "repair_round": round_index,
            },
            func=lambda round_index=round_index, current_judge=current_judge: run_timeline_repair_round(
                editor_timeline=context.state["editor_timeline"],
                judge_response=current_judge,
                output_dir=str(context.root),
                round_index=round_index,
                policy_report=current_policy,
                task_plan=context.state["task_plan"],
                semantic_blocks=context.state["semantic_blocks"],
            ),
        )
        context.state["editor_timeline"] = repair_result["data"]["editor_timeline"]
        context.state["repair_rounds"] = round_index
        context.state["repair_round_summaries"].append(repair_result["data"])
        transcript_path = repair_result["data"]["transcript_path"]
        context.state["final_review_transcript_path"] = transcript_path
        judge_result = executor.run(
            step_name=f"judge_llm_call_round_{round_index + 1}",
            tool_name="coherence_judge",
            input_summary={"segments": len(context.state["editor_timeline"].get("timeline_items", [])), "repair_round": round_index},
            func=lambda round_index=round_index, transcript_path=transcript_path: registry.get("judge_llm_call")(round_index + 1, context.root / f"repair_round_{round_index}", transcript_path),
        )
        current_judge = judge_result["data"]["judge_response"]
        judge_alias = context.root / f"repair_round_{round_index}" / "judge_response.json"
        judge_alias.write_text(json.dumps(current_judge, ensure_ascii=False, indent=2), encoding="utf-8")
        context.state["final_judge_response"] = current_judge
        policy_result = executor.run(
            step_name=f"policy_validation_round_{round_index + 1}",
            tool_name="policy_validator",
            input_summary={"segments": len(context.state["editor_timeline"].get("timeline_items", [])), "judge_passed": judge_passed(current_judge), "repair_round": round_index},
            func=lambda round_index=round_index: policy_validator.validate_policy(
                task_plan=context.state["task_plan"],
                editor_timeline=context.state["editor_timeline"],
                transcript_markdown_path=context.state["final_review_transcript_path"],
                output_path=str(context.root / f"repair_round_{round_index}" / "policy_validation_report.json"),
            ),
        )
        current_policy = policy_result["data"]
        context.state["policy_validation_report"] = current_policy
        context.state["policy_valid"] = bool(current_policy.get("policy_valid"))
        (context.root / "policy_validation_report.json").write_text(json.dumps(current_policy, ensure_ascii=False, indent=2), encoding="utf-8")
        if judge_passed(current_judge) and current_policy.get("policy_valid"):
            context.state["repair_success"] = True
            break

    context.state["repair_success"] = bool(judge_passed(current_judge) and current_policy.get("policy_valid"))

    if context.state["repair_rounds"]:
        transcript_result = transcript_assembly_tool.assemble_transcript(context.state["editor_timeline"], str(context.output_path("final_review_transcript.md")), str(context.output_path("final_review_transcript.txt")))
        context.state["final_review_transcript_path"] = transcript_result["data"]["markdown_path"]

    semantic_timeline = write_semantic_timeline_from_editor(context)
    context.state["semantic_timeline"] = semantic_timeline
    executor.run(step_name="semantic_timeline_generation", tool_name="timeline_editor", input_summary={"segments": len(semantic_timeline.get("items", []))}, func=lambda: {"success": True, "backend": "editor_timeline", "output_path": str(context.output_path("semantic_timeline.json")), "data": {"semantic_timeline": semantic_timeline, "segment_count": len(semantic_timeline.get("items", []))}})
    executor.run(step_name="transcript_review_generation", tool_name="transcript_assembly_tool", input_summary={"segments": len(semantic_timeline.get("items", []))}, func=lambda: coherence_validator.write_transcript_review(semantic_timeline, str(context.output_path("transcript_review.md"))))
    gate = executor.run(step_name="export_gate_decision", tool_name="export_gate", input_summary={"judge_score": context.state["final_judge_response"].get("score"), "export_requested": export_video}, func=lambda: write_export_gate(context))["data"]["export_gate_decision"]
    context.state["export_gate_decision"] = gate

    final_video_result: dict[str, Any] = {"success": True, "backend": "dry_run_no_video", "data": {}}
    edit_plan_result: dict[str, Any] = {"output_path": ""}
    if export_video and gate.get("video_export_allowed"):
        selected = editor_items_to_clips(context.state["editor_timeline"])
        context.state["semantic_selected"] = selected
        llm_result = executor.run(step_name="llm_content_generation", tool_name="llm_tool", input_summary={"selected_count": len(selected)}, func=lambda: llm_tool.generate_content(context.intent, selected, context.config))
        context.state["clips"] = llm_result["data"]["clips"]
        executor.run(step_name="selected_segment_export", tool_name="segment_export_tool", input_summary={"clip_count": len(context.state["clips"])}, func=lambda: registry.get("selected_segment_export")())
        executor.run(step_name="title_card_generation", tool_name="title_card_tool", input_summary={"clip_count": len(context.state["clips"])}, func=lambda: registry.get("title_card_generation")())
        timeline_result = executor.run(step_name="timeline_generation", tool_name="timeline_schema", input_summary={"clip_count": len(context.state["clips"])}, func=lambda: registry.get("timeline_generation")())
        context.state["timeline"] = timeline_result["data"]["timeline"]
        executor.run(step_name="final_subtitle_generation", tool_name="final_subtitle_tool", input_summary={"timeline_items": len(context.state["timeline"]["items"])}, func=lambda: registry.get("final_subtitle_generation")())
        final_video_result = executor.run(step_name="final_review_video_generation", tool_name="final_video_tool", input_summary={"clip_count": len(context.state["clips"])}, func=lambda: registry.get("final_review_video_generation")())
        context.state["final_video_result"] = final_video_result
        edit_plan_result = executor.run(step_name="edit_plan_generation", tool_name="edit_plan_schema", input_summary={"clip_count": len(context.state["clips"])}, func=lambda: registry.get("edit_plan_generation")())
        executor.run(step_name="review_sheet_generation", tool_name="review_sheet_tool", input_summary={"clip_count": len(context.state["clips"])}, func=lambda: registry.get("review_sheet_generation")())

    summary = write_summary(context)
    trace.record({"step_name": "artifact_validation", "tool_name": "artifact_validator", "success": True, "artifact_type": "validation_report_json", "input_summary": {"out_dir": str(context.root)}, "output_summary": {"pending": True}, "output_path": str(context.output_path("validation_report.json")), "error": None, "duration_seconds": 0.0})
    trace.save(context.output_path("trace.json"))
    validation = ArtifactValidator().validate(str(context.root), final_video_result)
    context.output_path("validation_report.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    trace.steps[-1]["success"] = bool(validation["harness_behavior_valid"])
    trace.steps[-1]["output_summary"] = validation
    trace.steps[-1]["error"] = validation.get("error")
    trace.save(context.output_path("trace.json"))
    if not validation["harness_behavior_valid"]:
        raise RuntimeError(f"artifact validation failed: {validation}")
    return {**summary, "edit_plan": edit_plan_result.get("output_path", ""), "trace": str(context.output_path("trace.json")), "validation_report": str(context.output_path("validation_report.json"))}


def build_registry(context: RunContext) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register("subtitle_parse", lambda: subtitle_tool.load_or_transcribe(context.video_path, context.subtitle_path or None, str(context.temp_chunks_dir), context.config))
    registry.register("sentence_segmentation", lambda: sentence_segment_tool.build_sentences(context.state["transcript"]))
    registry.register("semantic_block_generation", lambda: semantic_block_tool.build_blocks(context.state["sentences"]))
    registry.register("selector_llm_call", lambda: run_content_selector(intent=context.intent, video_metadata={"video_path": context.video_path}, semantic_blocks=context.state["semantic_blocks"], config=context.config, output_dir=str(context.root)))
    registry.register("editor_llm_call", lambda: run_timeline_editor(intent=context.intent, selector_response=context.state["selector_response"], semantic_blocks=context.state["semantic_blocks"], default_policy=context.state["task_plan"], config=context.config, output_dir=str(context.root)))
    registry.register("final_review_transcript_generation", lambda: transcript_assembly_tool.assemble_transcript(context.state["editor_timeline"], str(context.output_path("final_review_transcript.md")), str(context.output_path("final_review_transcript.txt"))))
    registry.register("judge_llm_call", lambda round_index=1, output_dir=context.root, transcript_path=None: run_coherence_judge(intent=context.intent, editor_timeline=context.state["editor_timeline"], transcript_markdown=Path(transcript_path or context.state["final_review_transcript_path"]).read_text(encoding="utf-8"), config=context.config, output_dir=str(output_dir), round_index=round_index))
    registry.register("selected_segment_export", lambda: segment_export_tool.export_segments(context.video_path, context.state["clips"], str(context.selected_segments_dir), add_boundary_fade=False))
    registry.register("title_card_generation", lambda: title_card_tool.generate_title_cards(context.state["clips"], str(context.title_cards_dir)))
    registry.register("timeline_generation", lambda: write_timeline(context))
    registry.register("final_subtitle_generation", lambda: final_subtitle_tool.write_final_srt(context.state["transcript"], context.state["timeline"], str(context.output_path("final_review.srt"))))
    registry.register("final_review_video_generation", lambda: final_video_tool.generate_final_review(context.state["clips"], str(context.output_path("final_review.mp4")), str(context.temp_chunks_dir)))
    registry.register("edit_plan_generation", lambda: write_edit_plan(context))
    registry.register("review_sheet_generation", lambda: review_sheet_tool.write_review_sheet(Path(context.video_path).stem, context.state["clips"], str(context.output_path("human_review_sheet.csv"))))
    return registry


def write_export_gate(context: RunContext) -> dict[str, Any]:
    judge = context.state["final_judge_response"]
    score = float(judge.get("score", 0.0))
    major = judge.get("major_problems") or []
    content_valid = bool(judge.get("passed")) and score >= 0.75 and not major
    policy_valid = bool(context.state.get("policy_valid", False))
    allowed = content_valid and policy_valid
    blocked_reason = None
    if not allowed:
        if not policy_valid:
            blocked_reason = "policy_violation"
        elif context.state.get("repair_loop_triggered") and int(context.state.get("repair_rounds", 0)) >= 3:
            blocked_reason = "coherence_judge_failed_after_repair"
        else:
            blocked_reason = judge.get("reason") or "judge_failed_or_score_below_threshold"
    payload = {
        "video_export_allowed": allowed,
        "export_requested": bool(context.state.get("export_video")),
        "judge_final_score": score,
        "judge_passed": bool(judge.get("passed")),
        "content_valid": content_valid,
        "policy_valid": policy_valid,
        "policy_violations": context.state.get("policy_validation_report", {}).get("violations", []),
        "repair_rounds": int(context.state.get("repair_rounds", 0)),
        "repair_loop_triggered": bool(context.state.get("repair_loop_triggered", False)),
        "repair_success": bool(context.state.get("repair_success", False)),
        "blocked_reason": blocked_reason,
        "judge_final_reason": judge.get("reason"),
    }
    path = context.output_path("export_gate_decision.json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "backend": "export_gate", "output_path": str(path), "data": {"export_gate_decision": payload, "score": score, "repair_round": payload["repair_rounds"]}}


def write_semantic_timeline_from_editor(context: RunContext) -> dict[str, Any]:
    items = []
    cursor = 0.0
    for item in context.state["editor_timeline"].get("timeline_items", []):
        duration = round(float(item["source_end"]) - float(item["source_start"]), 3)
        items.append(
            {
                "segment_id": item["segment_id"],
                "role": item.get("role", "core_concept"),
                "source_start": item["source_start"],
                "source_end": item["source_end"],
                "target_start": round(cursor, 3),
                "target_end": round(cursor + duration, 3),
                "duration": duration,
                "text": item.get("transcript", ""),
                "sentence_ids": [],
                "semantic_block_ids": item.get("source_block_ids", []),
                "starts_mid_sentence": False,
                "ends_mid_sentence": False,
                "standalone_score": 0.8,
                "completeness_score": 0.82,
                "coherence_score": 0.8,
                "selection_reason": item.get("why_included", ""),
                "bridge_text_before": item.get("bridge_before"),
                "bridge_text_after": item.get("bridge_after"),
            }
        )
        cursor += duration
    payload = {"source_video": context.video_path, "duration": round(cursor, 3), "items": items, "editor_timeline_path": str(context.output_path("editor_timeline.json"))}
    context.output_path("semantic_timeline.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def editor_items_to_clips(editor_timeline: dict[str, Any]) -> list[dict[str, Any]]:
    clips = []
    for idx, item in enumerate(editor_timeline.get("timeline_items", []), start=1):
        clips.append(
            {
                "clip_id": f"clip_{idx:03}",
                "start": item["source_start"],
                "end": item["source_end"],
                "duration": round(float(item["source_end"]) - float(item["source_start"]), 3),
                "transcript": item.get("transcript", ""),
                "score": 0.8,
                "cut_quality_score": 0.8,
                "duplicate_ratio": 0.0,
                "selection_reason": item.get("why_included", ""),
                "original_start": item["source_start"],
                "original_end": item["source_end"],
                "refined_start": item["source_start"],
                "refined_end": item["source_end"],
                "boundary_refined": True,
            }
        )
    return clips


def _planner_tool_result(task_plan: dict[str, Any]) -> dict[str, Any]:
    return {"success": True, "backend": task_plan.get("planner_backend", "llm_planner"), "output_path": task_plan.get("task_plan_path", ""), "data": {"task_plan": task_plan, "model": task_plan.get("planner_model"), "prompt_hash": task_plan.get("planner_prompt_hash"), "raw_response_path": task_plan.get("planner_raw_response_path"), "task_plan_path": task_plan.get("task_plan_path"), "fallback_used": task_plan.get("planner_fallback_used"), "fallback_reason": task_plan.get("planner_fallback_reason")}}


def write_timeline(context: RunContext) -> dict[str, Any]:
    timeline = build_timeline(context.video_path, str(context.output_path("final_review.mp4")), context.state["clips"], context.state.get("task_plan", {}))
    errors = validate_timeline(timeline)
    if errors:
        return {"success": False, "error": "; ".join(errors)}
    path = context.output_path("timeline.json")
    path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "backend": "timeline_schema", "output_path": str(path), "data": {"timeline": timeline, "duration": timeline["duration"]}}


def write_edit_plan(context: RunContext) -> dict[str, Any]:
    payload = {"video_path": context.video_path, "subtitle_path": context.state.get("subtitle_output_path") or context.subtitle_path, "intent": context.intent, "selected_clips": context.state["clips"], "task_plan": context.state.get("task_plan", {}), "editor_timeline_path": str(context.output_path("editor_timeline.json")), "timeline_path": str(context.output_path("timeline.json")), "final_review_path": str(context.output_path("final_review.mp4")), "trace_path": str(context.output_path("trace.json")), "human_review_sheet_path": str(context.output_path("human_review_sheet.csv"))}
    errors = validate_edit_plan(payload)
    if errors:
        return {"success": False, "error": "; ".join(errors)}
    path = context.output_path("edit_plan.json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "backend": "edit_plan_schema", "output_path": str(path), "data": {"selected_count": len(context.state["clips"])}}


def write_summary(context: RunContext) -> dict[str, Any]:
    judge_initial = context.state.get("initial_judge_response", {})
    judge_final = context.state.get("final_judge_response", {})
    gate = context.state.get("export_gate_decision", {})
    final_probe = context.state.get("final_video_result", {}).get("data", {}).get("final_probe", {})
    transcript_valid = bool(context.state.get("transcript_quality", {}).get("transcript_valid", False))
    export_video = bool(context.state.get("export_video"))
    if not transcript_valid:
        primary_outputs = ["transcript_quality_report.json", "export_gate_decision.json"]
    elif not export_video:
        primary_outputs = ["selector_response.json", "editor_timeline.json", "final_review_transcript.md", "judge_response_round_1.json", "export_gate_decision.json"]
    else:
        primary_outputs = ["final_review.mp4", "timeline.json", "edit_plan.json", "human_review_sheet.csv"]
    summary = {
        "run_id": context.run_id,
        "success": True,
        "export_video": export_video,
        "multi_agent_loop": True,
        "transcript_source": context.state.get("transcript_quality", {}).get("transcript_source", "unknown"),
        "transcript_quality_score": context.state.get("transcript_quality", {}).get("quality_score"),
        "transcript_valid": transcript_valid,
        "asr_backend": context.state.get("transcript_quality", {}).get("asr_backend", ""),
        "asr_fallback_used": bool(context.state.get("transcript_quality", {}).get("asr_fallback_used", False)),
        "selector_model": context.config.get("llm", {}).get("model", "deepseek-chat"),
        "editor_model": context.config.get("llm", {}).get("model", "deepseek-chat"),
        "judge_model": context.config.get("llm", {}).get("model", "deepseek-chat"),
        "judge_initial_score": judge_initial.get("score"),
        "judge_final_score": judge_final.get("score"),
        "repair_loop_triggered": bool(context.state.get("repair_loop_triggered", False)),
        "repair_rounds": int(context.state.get("repair_rounds", 0)),
        "repair_success": bool(context.state.get("repair_success", False)),
        "policy_valid": bool(context.state.get("policy_valid", False)),
        "policy_violations": context.state.get("policy_validation_report", {}).get("violations", []),
        "max_final_duration_seconds": context.state.get("policy_validation_report", {}).get("max_final_duration_seconds"),
        "actual_final_duration_seconds": context.state.get("policy_validation_report", {}).get("final_duration_seconds"),
        "policy_repair_triggered": bool(context.state.get("policy_repair_triggered", False)),
        "video_export_allowed": bool(gate.get("video_export_allowed")),
        "export_blocked_reason": gate.get("blocked_reason"),
        "primary_outputs": primary_outputs,
        "supporting_outputs": ["trace.json", "validation_report.json", "workflow_summary.json"],
        "intermediate_assets": ["assets/selected_segments/", "assets/title_cards/", "assets/temp_chunks/"],
        "selected_segment_count": len(context.state.get("editor_timeline", {}).get("timeline_items", [])),
        "semantic_timeline_valid": bool(gate.get("video_export_allowed")),
        "final_video_backend": context.state.get("final_video_result", {}).get("backend"),
        "final_review_visual_valid": bool(final_probe.get("visual_valid")),
        "final_review_black_frame_ratio": final_probe.get("black_frame_ratio"),
        "policy": context.state.get("task_plan", {}),
    }
    context.output_path("workflow_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary

