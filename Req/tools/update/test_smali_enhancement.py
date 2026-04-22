from __future__ import annotations

import json
from pathlib import Path

from ..apktool import apktool_apk

from .run_smali_enhancement import run_pipeline


def test_with_converter_now() -> dict:
    apk_path = Path(r"d:\nju\需求生成系统\测试APP\APK\ConverterNOW.apk")
    app_dir = Path(r"d:\nju\需求生成系统\ScenReq\Req\tools\update\output\decompiled\ConverterNOW")
    out_dir = Path(r"d:\nju\需求生成系统\ScenReq\Req\tools\update\output\ConverterNOW")

    if not apk_path.exists():
        raise FileNotFoundError(f"Test APK not found: {apk_path}")

    # Always decompile from APK for this test to avoid using stale artifacts.
    app_dir.parent.mkdir(parents=True, exist_ok=True)
    apktool_apk(str(apk_path), str(app_dir))

    if not app_dir.exists():
        raise FileNotFoundError(f"Decompiled app dir not found after apktool: {app_dir}")

    # ConverterNOW on smali-only evidence can be sparse; use a lower threshold for test stability.
    summary = run_pipeline(
        app_dir=str(app_dir),
        output_dir=str(out_dir),
        max_smali_files=5000,
        min_confidence=0.2,
        aggregate_by_type=True,
    )

    required_files = [
        out_dir / "resource_index.json",
        out_dir / "smali_ir.json",
        out_dir / "intent_graph.json",
        out_dir / "activity_analysis_enhanced.json",
        out_dir / "legacy_parse_bundle.json",
        out_dir / "pipeline_summary.json",
    ]
    missing = [str(p) for p in required_files if not p.exists()]
    if missing:
        raise AssertionError(f"Missing output files: {missing}")

    bridge = json.loads((out_dir / "legacy_parse_bundle.json").read_text(encoding="utf-8"))
    if not bridge.get("intent_units"):
        raise AssertionError("intent_units is empty in legacy_parse_bundle")

    print("=== Update Module Test Passed ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"intent_units_count: {len(bridge.get('intent_units', []))}")
    return summary


def main() -> None:
    test_with_converter_now()


if __name__ == "__main__":
    main()
