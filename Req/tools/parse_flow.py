import os
import json
from pathlib import Path
import xml.etree.ElementTree as ET

try:
    from androguard.core.bytecodes.apk import APK
except Exception:
    APK = None

from Req.config.RunConfig import OUTPUT_ROOT, ANALYSIS_DIR
from Req.tools.apktool import apktool_apk
from Req.llm.activity_analysis import combina_activity

# Enhanced pipeline imports
from Req.tools.update.run_smali_enhancement import run_pipeline as enhanced_run_pipeline
from Req.tools.update.legacy_bridge import export_legacy_inputs


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def write_activity_list(app_dir: Path, activities: list):
    fp = app_dir / "activity_list.txt"
    with open(fp.as_posix(), 'w', encoding='utf-8') as f:
        for act in activities:
            f.write(act + "\n")
    return fp


def find_manifest(app_dir: Path) -> Path | None:
    candidates = [
        app_dir / "AndroidManifest.xml",
        app_dir / "original" / "AndroidManifest.xml",
    ]
    for c in candidates:
        if c.exists():
            return c
    for p in app_dir.rglob("AndroidManifest.xml"):
        return p
    return None


def get_package_from_manifest(manifest_path: Path) -> str:
    try:
        root = ET.parse(manifest_path.as_posix()).getroot()
        return root.get('package') or ''
    except Exception:
        return ''


def _extract_activities_from_manifest(manifest_path: str) -> list:
    """Extract activities from AndroidManifest.xml (basic version)."""
    try:
        root = ET.parse(manifest_path).getroot()
        pkg = root.get('package', '')
        app = root.find('application')
        activities = []
        if app is not None:
            for act in app.findall('activity'):
                name = act.get(f'{{{"http://schemas.android.com/apk/res/android"}}}name', '')
                if name.startswith('.'):
                    name = pkg + name
                elif '.' not in name and pkg:
                    name = pkg + '.' + name
                exported = act.get(f'{{{"http://schemas.android.com/apk/res/android"}}}exported', '')
                launcher = False
                for i_f in act.findall('intent-filter'):
                    actions = i_f.findall('action')
                    categories = i_f.findall('category')
                    has_main = any(a.get(f'{{{"http://schemas.android.com/apk/res/android"}}}name') == 'android.intent.action.MAIN' for a in actions)
                    has_launcher = any(c.get(f'{{{"http://schemas.android.com/apk/res/android"}}}name') == 'android.intent.category.LAUNCHER' for c in categories)
                    if has_main and has_launcher:
                        launcher = True
                activities.append({'name': name, 'is_launcher': launcher, 'exported': exported})
        return activities
    except Exception:
        return []


def find_main_activity_from_manifest(manifest_path: Path) -> str:
    activities = _extract_activities_from_manifest(manifest_path.as_posix())
    main = ''
    for a in activities:
        if a.get('is_launcher'):
            main = a.get('name')
            break
    if not main and activities:
        main = activities[0].get('name', '')
    return main


def preprocess_existing_dir(app_dir: str) -> dict:
    """Preprocess an existing decompiled app directory using enhanced pipeline."""
    app_path = Path(app_dir).resolve()
    manifest = find_manifest(app_path)
    if not manifest:
        return {"ok": False, "message": "未找到 AndroidManifest.xml"}

    package = get_package_from_manifest(manifest)
    main_activity = find_main_activity_from_manifest(manifest)
    acts = _extract_activities_from_manifest(manifest.as_posix())
    names = [x['name'] for x in acts]
    list_path = write_activity_list(app_path, names)

    # Run enhanced pipeline
    out_dir = app_path / "enhanced_analysis"
    ensure_dir(out_dir)
    try:
        summary = enhanced_run_pipeline(
            app_dir=str(app_path),
            output_dir=str(out_dir),
            max_smali_files=8000,
            min_confidence=0.45,
            aggregate_by_type=True,
        )
        # Export legacy-compatible artifacts
        resource_index = summary.get("artifacts", {}).get("resource_index")
        smali_ir = summary.get("artifacts", {}).get("smali_ir")
        intent_graph_path = summary.get("artifacts", {}).get("intent_graph")
        intent_graph = json.loads(Path(intent_graph_path).read_text(encoding="utf-8")) if intent_graph_path and Path(intent_graph_path).exists() else {}
        if resource_index and smali_ir and intent_graph:
            export_legacy_inputs(
                resource_index=json.loads(Path(resource_index).read_text(encoding="utf-8")),
                smali_ir=json.loads(Path(smali_ir).read_text(encoding="utf-8")),
                intent_graph=intent_graph,
                output_dir=str(out_dir),
            )
    except Exception as e:
        # Enhanced pipeline failed, fall back to basic processing
        print(f"Enhanced pipeline failed: {e}, falling back to basic processing")

    # Legacy merged_dir for backward compatibility
    merged_dir = app_path / "merged_methods"
    ensure_dir(merged_dir)

    return {
        "ok": True,
        "app_dir": app_path.as_posix(),
        "package": package,
        "main_activity": main_activity,
        "activities": names,
        "activity_list_path": list_path.as_posix(),
        "merged_dir": merged_dir.as_posix(),
        "merged_file_count": 0,
        "nonempty_merged_file_count": 0,
        "enhanced_output_dir": str(out_dir),
    }


def preprocess_apk(apk_path: str, out_root: str = '') -> dict:
    """Preprocess an APK file: decompile and analyze."""
    if not os.path.isfile(apk_path):
        return {"ok": False, "message": "APK 不存在"}
    out = Path(out_root).resolve() if out_root else Path(OUTPUT_ROOT).resolve()
    ensure_dir(out)
    if APK is None:
        return {"ok": False, "message": "未安装 androguard"}
    a = APK(apk_path)
    package = a.get_package()
    app_id = package or Path(apk_path).stem
    app_dir = out / app_id
    ensure_dir(app_dir)
    apktool_apk(apk_path, app_dir.as_posix())
    return preprocess_existing_dir(app_dir.as_posix())


def analyze_existing_dir(app_dir: str) -> dict:
    """Analyze an existing decompiled app directory."""
    base = preprocess_existing_dir(app_dir)
    if not base.get('ok'):
        return base
    pkg = base.get('package') or Path(app_dir).name
    out_dir = Path(ANALYSIS_DIR) / pkg
    ensure_dir(out_dir)

    analysis_json_path = None

    try:
        merged_dir = base.get('merged_dir')
        activity_list_path = base.get('activity_list_path')
        if merged_dir and activity_list_path and Path(merged_dir).exists():
            txt_path, json_path = combina_activity(merged_dir, out_dir.as_posix(), activity_list_path)
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    legacy_data = json.load(f)
                has_valid = any(
                    not item.get('function', '').startswith('[-]')
                    for item in legacy_data
                )
                if has_valid:
                    return {"ok": True, "analysis_txt_path": txt_path, "analysis_json_path": json_path, **base}
                analysis_json_path = json_path
            except Exception:
                pass
    except Exception:
        pass

    enhanced_dir = base.get('enhanced_output_dir')
    enhanced_json = Path(enhanced_dir) / "activity_analysis_enhanced.json" if enhanced_dir else None
    if enhanced_json and enhanced_json.exists():
        try:
            enhanced_data = json.loads(enhanced_json.read_text(encoding="utf-8"))
            ans = [{"activity": item.get("activity", ""), "function": item.get("function", "")}
                   for item in enhanced_data
                   if not item.get("function", "").startswith("[-]")]
            if ans:
                json_path = out_dir / 'activity_analysis_results.json'
                txt_path = out_dir / 'activity_analysis_results.txt'
                with open(json_path.as_posix(), 'w', encoding='utf-8') as f:
                    json.dump(ans, f, ensure_ascii=False, indent=4)
                with open(txt_path.as_posix(), 'w', encoding='utf-8') as f:
                    for item in ans:
                        f.write(f"=== {item['activity']} ===\n{item['function']}\n\n")
                return {"ok": True, "analysis_txt_path": txt_path.as_posix(), "analysis_json_path": json_path.as_posix(), **base}
        except Exception:
            pass

    if analysis_json_path:
        return {"ok": True, "analysis_txt_path": str(Path(analysis_json_path).with_suffix('.txt')), "analysis_json_path": str(analysis_json_path), **base}


def analyze_batch_dir(root_dir: str, limit: int = 10) -> list:
    base = Path(root_dir).resolve()
    if not base.exists() or not base.is_dir():
        return [{"ok": False, "message": "目录不存在或不可用", "root_dir": base.as_posix()}]
    apps = [p for p in base.iterdir() if p.is_dir()]
    selected = apps[:max(0, limit)]
    results = []
    for d in selected:
        try:
            res = analyze_existing_dir(d.as_posix())
            results.append({"app": d.name, **res})
        except Exception as e:
            results.append({"app": d.name, "ok": False, "message": str(e)})
    return results
