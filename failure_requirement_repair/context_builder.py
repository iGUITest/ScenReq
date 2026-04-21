from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple


def _read_text_file(path: str, max_chars: int = 12000) -> str:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    if len(text) > max_chars:
        return text[:max_chars] + "\n...[truncated]"
    return text


def summarize_screenshots(screenshot_paths: List[str]) -> Tuple[str, List[str]]:
    lines: List[str] = []
    warnings: List[str] = []

    for i, raw in enumerate(screenshot_paths, start=1):
        p = Path(raw)
        if not p.exists():
            warnings.append(f"screenshot_not_found: {raw}")
            lines.append(f"{i}. {raw} (missing)")
            continue

        stat = p.stat()
        lines.append(
            f"{i}. name={p.name}, suffix={p.suffix.lower()}, size={stat.st_size} bytes, path={str(p)}"
        )

    if not lines:
        return "(none)", warnings
    return "\n".join(lines), warnings


def build_context_block(
    run_log_text: str,
    run_log_path: str | None,
    apk_info_text: str,
    apk_info_path: str | None,
    source_info_text: str,
    source_info_path: str | None,
    app_intro_text: str,
    app_intro_path: str | None,
    activity_analysis_text: str,
    activity_analysis_path: str | None,
    screenshot_paths: List[str],
    screenshot_notes: List[str],
) -> tuple[str, List[str]]:
    warnings: List[str] = []

    run_log = (run_log_text or "").strip() or _read_text_file(run_log_path or "")
    apk_info = (apk_info_text or "").strip() or _read_text_file(apk_info_path or "")
    source_info = (source_info_text or "").strip() or _read_text_file(source_info_path or "")
    app_intro = (app_intro_text or "").strip() or _read_text_file(app_intro_path or "")
    activity_info = (activity_analysis_text or "").strip() or _read_text_file(activity_analysis_path or "")

    if not run_log:
        warnings.append("run_log_empty")
    if not (apk_info or source_info or app_intro or activity_info):
        warnings.append("app_context_sparse")

    screenshot_summary, screenshot_warnings = summarize_screenshots(screenshot_paths)
    warnings.extend(screenshot_warnings)

    notes_text = "\n".join([f"- {n}" for n in screenshot_notes if (n or "").strip()]) or "(none)"

    context = (
        "[Run Log]\n"
        f"{run_log or '(empty)'}\n\n"
        "[Screenshot Summary]\n"
        f"{screenshot_summary}\n\n"
        "[Screenshot Notes]\n"
        f"{notes_text}\n\n"
        "[APK Info]\n"
        f"{apk_info or '(empty)'}\n\n"
        "[Source Info]\n"
        f"{source_info or '(empty)'}\n\n"
        "[App Introduction]\n"
        f"{app_intro or '(empty)'}\n\n"
        "[Activity Analysis]\n"
        f"{activity_info or '(empty)'}"
    )

    return context, warnings


def infer_failure_signals(run_log: str) -> List[str]:
    text = (run_log or "").lower()
    signals: List[str] = []

    keys = [
        ("timeout", "timeout"),
        ("assert", "assertion_failure"),
        ("not found", "element_not_found"),
        ("no such element", "element_not_found"),
        ("crash", "app_crash"),
        ("exception", "runtime_exception"),
        ("network", "network_dependency"),
        ("permission", "permission_issue"),
        ("stale", "stale_element"),
        ("flaky", "test_flaky"),
    ]

    for needle, label in keys:
        if needle in text:
            signals.append(label)

    if not signals:
        signals.append("unspecified_failure")

    return sorted(set(signals))
