from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from manual_edit_sync.word_json_sync import sync_word_to_json


def _load_json(path: Path) -> List[Dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _diff_by_id(
    before: List[Dict[str, Any]],
    after: List[Dict[str, Any]],
    fields: List[str],
) -> Tuple[int, List[Dict[str, Any]]]:
    before_map = {str(item.get("id", "")).strip(): item for item in before}
    after_map = {str(item.get("id", "")).strip(): item for item in after}

    changed: List[Dict[str, Any]] = []
    for rid, new_item in after_map.items():
        old_item = before_map.get(rid, {})
        row_changes = {}
        for f in fields:
            if old_item.get(f) != new_item.get(f):
                row_changes[f] = {
                    "before": old_item.get(f),
                    "after": new_item.get(f),
                }
        if row_changes:
            changed.append({"id": rid, "changes": row_changes})

    return len(changed), changed


def run_test(in_place: bool = False) -> None:
    module_dir = Path(__file__).resolve().parent
    test_data_dir = module_dir / "test_data"

    report_src = test_data_dir / "com.ferrarid.converterpro_功能测试报告.docx"
    json_dir_src = test_data_dir / "com.ferrarid.converterpro_data"
    srs_src = json_dir_src / "com.ferrarid.converterpro_SRS.json"
    tests_src = json_dir_src / "com.ferrarid.converterpro_TestRequirements.json"

    if not report_src.exists():
        raise FileNotFoundError(f"Report not found: {report_src}")
    if not srs_src.exists() or not tests_src.exists():
        raise FileNotFoundError("SRS/Test JSON not found in test_data/com.ferrarid.converterpro_data")

    if in_place:
        report_tmp = report_src
        srs_tmp = srs_src
        tests_tmp = tests_src
        print("[Mode] in-place (will update source JSON files)")
        _run_once(report_tmp, srs_tmp, tests_tmp)
        return

    with tempfile.TemporaryDirectory(prefix="manual_edit_sync_") as tmp:
        tmp_dir = Path(tmp)
        report_tmp = tmp_dir / report_src.name
        srs_tmp = tmp_dir / srs_src.name
        tests_tmp = tmp_dir / tests_src.name

        shutil.copy2(report_src, report_tmp)
        shutil.copy2(srs_src, srs_tmp)
        shutil.copy2(tests_src, tests_tmp)

        print("[Mode] safe-temp (source JSON files will NOT be modified)")
        _run_once(report_tmp, srs_tmp, tests_tmp)


def _run_once(report_tmp: Path, srs_tmp: Path, tests_tmp: Path) -> None:

    srs_before = _load_json(srs_tmp)
    tests_before = _load_json(tests_tmp)

    result = sync_word_to_json(
        report_path=str(report_tmp),
        srs_json_path=str(srs_tmp),
        tests_json_path=str(tests_tmp),
    )

    srs_after = _load_json(srs_tmp)
    tests_after = _load_json(tests_tmp)

    srs_changed_count, srs_changed_rows = _diff_by_id(
        srs_before,
        srs_after,
        fields=["name", "requirement", "type"],
    )
    tests_changed_count, tests_changed_rows = _diff_by_id(
        tests_before,
        tests_after,
        fields=["name", "description", "objective", "test_data", "expected_result"],
    )

    print("===== Sync Result =====")
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))

    print("\n===== Diff Summary =====")
    print(f"SRS changed rows: {srs_changed_count}")
    print(f"Tests changed rows: {tests_changed_count}")

    preview_limit = 5
    if srs_changed_rows:
        print("\nSRS changed preview:")
        print(json.dumps(srs_changed_rows[:preview_limit], ensure_ascii=False, indent=2))
    if tests_changed_rows:
        print("\nTests changed preview:")
        print(json.dumps(tests_changed_rows[:preview_limit], ensure_ascii=False, indent=2))

    if not srs_changed_rows and not tests_changed_rows:
        print("\nNo content changes detected. Word and JSON may already be aligned.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run manual_edit_sync integration test.")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Update source JSON files directly instead of using a temp copy.",
    )
    args = parser.parse_args()
    run_test(in_place=args.in_place)
