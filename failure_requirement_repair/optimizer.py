from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from Req.config.RunConfig import API_KEY
from Req.llm.langchain_client import get_chat

from .context_builder import build_context_block, infer_failure_signals
from .models import OptimizedPayload, RepairRequest, RepairResult


def _load_json_list(path: str | None) -> List[Dict[str, Any]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _dump_json(path: Path, payload: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _strip_code_fence(text: str) -> str:
    out = (text or "").strip()
    if out.startswith("```json"):
        return out[7:-3].strip()
    if out.startswith("```"):
        return out[3:-3].strip()
    return out


def _repair_prompt(lang: str = "zh") -> str:
    if lang == "en":
        return (
            "You are a senior QA requirement repair expert. Based on test failure logs, screenshots summary, "
            "APK/source/app context, and original requirements, regenerate optimized requirements to fix bad, "
            "ambiguous, or untestable requirements.\\n"
            "Output strict JSON only:\\n"
            "{\\n"
            "  \"app\": \"AppName\",\\n"
            "  \"software_requirements\": [{\"id\":\"FR-001\",\"name\":\"...\",\"requirement\":\"...\",\"type\":\"...\"}],\\n"
            "  \"test_requirements\": [{\"id\":\"TC-001\",\"name\":\"...\",\"description\":\"...\",\"extra_info\":\"...\",\"objective\":\"...\",\"test_data\":{},\"expected_result\":\"...\",\"success_criteria\":\"...\"}]\\n"
            "}\\n"
            "Rules:\\n"
            "1) Strengthen preconditions, observability, and expected assertions.\\n"
            "2) Avoid unverifiable or external-system-dependent statements unless core feature requires them.\\n"
            "3) Preserve stable IDs when possible and keep wording concrete.\\n"
            "4) Return JSON only."
        )

    return (
        "你是资深测试需求修复专家。基于测试失败日志、截图摘要、APK/源码/应用介绍上下文以及原始需求，"
        "重新生成优化后的需求，用于修复描述含糊、不可测、断言不足、依赖外部环境过强等问题。\\n"
        "只输出严格 JSON：\\n"
        "{\\n"
        "  \"app\": \"应用名\",\\n"
        "  \"software_requirements\": [{\"id\":\"FR-001\",\"name\":\"...\",\"requirement\":\"...\",\"type\":\"...\"}],\\n"
        "  \"test_requirements\": [{\"id\":\"TC-001\",\"name\":\"...\",\"description\":\"...\",\"extra_info\":\"...\",\"objective\":\"...\",\"test_data\":{},\"expected_result\":\"...\",\"success_criteria\":\"...\"}]\\n"
        "}\\n"
        "修复规则：\\n"
        "1) 强化前置条件、可观测步骤和可断言预期。\\n"
        "2) 避免不可验证或强依赖外部系统的表述（除非是核心功能）。\\n"
        "3) 尽量保留已有 ID 并使描述可执行、可验证。\\n"
        "4) 仅输出 JSON，不要解释。"
    )


def _heuristic_optimize(
    app_name: str,
    original_srs: List[Dict[str, Any]],
    original_tests: List[Dict[str, Any]],
    failure_signals: List[str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    hint = "；".join(failure_signals)

    srs = []
    for item in original_srs:
        s = dict(item)
        req = str(s.get("requirement", "")).strip()
        if req:
            s["requirement"] = f"{req}（需具备可观测状态与明确失败提示，避免歧义）"
        srs.append(s)

    tests = []
    for item in original_tests:
        t = dict(item)
        desc = str(t.get("description", "")).strip()
        exp = str(t.get("expected_result", "")).strip()
        suc = str(t.get("success_criteria", "")).strip()

        if desc:
            t["description"] = f"{desc}。步骤需可重复执行，并在关键节点记录可观测结果。"
        if exp:
            t["expected_result"] = f"{exp}；若失败应返回可定位错误信息。"
        t["success_criteria"] = suc or "关键断言满足，且无崩溃/无未处理异常/无长时间无响应"

        extra = str(t.get("extra_info", "")).strip()
        repair_hint = f"失败信号: {hint}"
        t["extra_info"] = f"{extra} | {repair_hint}" if extra else repair_hint
        tests.append(t)

    if not srs:
        srs = [
            {
                "id": "FR-001",
                "name": "失败场景可观测性",
                "requirement": "系统应在关键失败场景提供明确错误提示和可追踪状态，以支持自动化断言。",
                "type": "功能性",
            }
        ]

    if not tests:
        tests = [
            {
                "id": "TC-001",
                "name": "失败场景回归验证",
                "description": "基于失败日志复现场景并验证修复后行为。",
                "extra_info": f"失败信号: {hint}",
                "objective": "确保需求表述可测且断言明确",
                "test_data": {},
                "expected_result": "步骤可执行，断言明确，出现异常时可定位原因",
                "success_criteria": "无崩溃、无未处理异常、关键断言全部通过",
            }
        ]

    return srs, tests


def optimize_requirements(req: RepairRequest) -> RepairResult:
    context_block, warnings = build_context_block(
        run_log_text=req.run_log_text,
        run_log_path=req.run_log_path,
        apk_info_text=req.apk_info_text,
        apk_info_path=req.apk_info_path,
        source_info_text=req.source_info_text,
        source_info_path=req.source_info_path,
        app_intro_text=req.app_intro_text,
        app_intro_path=req.app_intro_path,
        activity_analysis_text=req.activity_analysis_text,
        activity_analysis_path=req.activity_analysis_path,
        screenshot_paths=req.screenshot_paths,
        screenshot_notes=req.screenshot_notes,
    )

    run_log_raw = req.run_log_text or ""
    if not run_log_raw and req.run_log_path and os.path.exists(req.run_log_path):
        run_log_raw = Path(req.run_log_path).read_text(encoding="utf-8", errors="ignore")
    failure_signals = infer_failure_signals(run_log_raw)

    original_srs = _load_json_list(req.original_srs_path)
    original_tests = _load_json_list(req.original_tests_path)

    mode = "heuristic"
    optimized_srs: List[Dict[str, Any]]
    optimized_tests: List[Dict[str, Any]]

    if (API_KEY or "").strip():
        try:
            chat = get_chat("qwen-plus", API_KEY)
            user_prompt = (
                f"App: {req.app_name}\\n"
                f"FailureSignals: {failure_signals}\\n\\n"
                f"[Original SRS JSON]\\n{json.dumps(original_srs, ensure_ascii=False)}\\n\\n"
                f"[Original TestRequirements JSON]\\n{json.dumps(original_tests, ensure_ascii=False)}\\n\\n"
                f"[Failure And App Context]\\n{context_block}"
            )
            result = chat.invoke(
                [
                    SystemMessage(content=_repair_prompt(req.lang)),
                    HumanMessage(content=user_prompt),
                ]
            )
            parsed = json.loads(_strip_code_fence(getattr(result, "content", str(result))))
            payload = OptimizedPayload(**parsed)
            optimized_srs = payload.software_requirements
            optimized_tests = payload.test_requirements
            mode = "llm"
        except Exception as exc:
            warnings.append(f"llm_fallback: {exc}")
            optimized_srs, optimized_tests = _heuristic_optimize(
                app_name=req.app_name,
                original_srs=original_srs,
                original_tests=original_tests,
                failure_signals=failure_signals,
            )
    else:
        warnings.append("api_key_missing_use_heuristic")
        optimized_srs, optimized_tests = _heuristic_optimize(
            app_name=req.app_name,
            original_srs=original_srs,
            original_tests=original_tests,
            failure_signals=failure_signals,
        )

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path(req.output_dir) if req.output_dir else Path("Req/output/test_requirements")
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_app = req.app_name.replace(" ", "_")
    srs_path = out_dir / f"{safe_app}_SRS_optimized_{ts}.json"
    tests_path = out_dir / f"{safe_app}_TestRequirements_optimized_{ts}.json"

    _dump_json(srs_path, optimized_srs)
    _dump_json(tests_path, optimized_tests)

    summary = (
        "已根据失败信号重建需求约束，重点增强可观测性、断言明确性与异常提示约束。"
        if req.lang != "en"
        else "Requirements were rebuilt using failure signals to strengthen observability and assertions."
    )

    return RepairResult(
        ok=True,
        app_name=req.app_name,
        mode=mode,
        output_srs_path=str(srs_path),
        output_tests_path=str(tests_path),
        summary=summary,
        failure_signals=failure_signals,
        software_requirements_count=len(optimized_srs),
        test_requirements_count=len(optimized_tests),
        warnings=warnings,
    )
