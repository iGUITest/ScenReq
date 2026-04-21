from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RepairRequest(BaseModel):
    app_name: str = Field(..., description="Application name")
    lang: str = Field("zh", description="Language: zh/en")

    run_log_text: str = Field("", description="Raw test runtime log text")
    run_log_path: Optional[str] = Field(None, description="Path to runtime log file")

    screenshot_paths: List[str] = Field(default_factory=list, description="Screenshot file paths")
    screenshot_notes: List[str] = Field(default_factory=list, description="Optional manual notes per screenshot")

    apk_info_text: str = Field("", description="Optional APK meta information")
    apk_info_path: Optional[str] = Field(None, description="Optional APK meta file path")

    source_info_text: str = Field("", description="Optional source code summary")
    source_info_path: Optional[str] = Field(None, description="Optional source summary path")

    app_intro_text: str = Field("", description="Optional app introduction")
    app_intro_path: Optional[str] = Field(None, description="Optional app introduction file path")

    activity_analysis_text: str = Field("", description="Optional activity analysis summary")
    activity_analysis_path: Optional[str] = Field(None, description="Optional activity analysis path")

    original_srs_path: Optional[str] = Field(None, description="Original SRS JSON path")
    original_tests_path: Optional[str] = Field(None, description="Original TestRequirements JSON path")

    output_dir: Optional[str] = Field(None, description="Output directory for optimized JSON")


class RepairResult(BaseModel):
    ok: bool
    app_name: str
    mode: str
    output_srs_path: str
    output_tests_path: str
    summary: str
    failure_signals: List[str]
    software_requirements_count: int
    test_requirements_count: int
    warnings: List[str] = Field(default_factory=list)


class OptimizedPayload(BaseModel):
    app: str
    software_requirements: List[Dict[str, Any]]
    test_requirements: List[Dict[str, Any]]
