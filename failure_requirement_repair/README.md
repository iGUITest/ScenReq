# Failure Requirement Repair (Hot-Plug Reserved Module)

## 目标
当测试智能体执行测试需求失败时，调用本模块接口并传入：
- 运行日志
- 失败截图（路径）
- 原始 APK / 源码 / 应用介绍 / Activity 分析等上下文

模块将基于这些输入重新生成优化后的需求 JSON，用于修正原需求中的不可测、歧义或断言不足问题。

说明：
- 本模块为独立预留目录，不改现有主流程。
- 当前不要求接入现有系统，可后续热拔插。

## 目录结构
- `models.py`: 接口请求与响应模型
- `context_builder.py`: 日志/截图/上下文聚合与失败信号提取
- `optimizer.py`: 需求优化核心逻辑（LLM + 兜底策略）
- `api.py`: FastAPI 接口
- `run_api.py`: 启动脚本

## 技术原理
1. 上下文聚合
- 支持直接传文本，也支持传文件路径。
- 对运行日志、APK信息、源码摘要、应用介绍、Activity 分析进行统一拼接。
- 对截图路径做摘要（文件名、后缀、大小、路径），并记录缺失截图告警。

2. 失败信号抽取
- 从日志中抽取关键失败标签（如 `timeout`、`element_not_found`、`app_crash`、`runtime_exception` 等）。
- 失败信号作为需求重写约束输入模型，指导“针对性修复”。

3. 双通道优化
- LLM 通道：存在 API Key 时，调用现有 `Req.llm.langchain_client` 生成结构化优化结果。
- 兜底通道：无 API Key 或 LLM失败时，使用启发式策略增强原需求：
  - 补强前置条件和可观测步骤
  - 补强 expected_result 与 success_criteria
  - 注入失败信号，保证可追踪性

4. 输出落盘
- 生成两个优化文件：
  - `{app}_SRS_optimized_{timestamp}.json`
  - `{app}_TestRequirements_optimized_{timestamp}.json`
- 默认输出目录：`Req/output/test_requirements`

## 预期效果
- 失败后可快速形成“可回归、可断言、可定位”的新需求版本。
- 降低因需求描述不清导致的重复失败。
- 为后续自动修复闭环（失败 -> 修复需求 -> 重测）提供标准接口。

## 启动
在 `ScenReq` 根目录执行：

```bash
python -m failure_requirement_repair.run_api
```

默认地址：`http://0.0.0.0:8012`

## API
### 健康检查
`GET /health`

### 需求修复
`POST /api/repair/requirements`

关键字段：
- `app_name` (必填)
- `run_log_text` 或 `run_log_path`
- `screenshot_paths` (数组)
- `apk_info_text/path`, `source_info_text/path`, `app_intro_text/path`, `activity_analysis_text/path`
- `original_srs_path`, `original_tests_path`
- `output_dir` (可选)

示例：

```json
{
  "app_name": "com.ferrarid.converterpro",
  "lang": "zh",
  "run_log_path": "D:/nju/需求生成系统/ScenReq/logs/fail.log",
  "screenshot_paths": [
    "D:/nju/需求生成系统/ScenReq/logs/shot_01.png",
    "D:/nju/需求生成系统/ScenReq/logs/shot_02.png"
  ],
  "app_intro_path": "D:/nju/需求生成系统/APP/携程.txt",
  "activity_analysis_path": "D:/nju/需求生成系统/ScenReq/Req/demo/sample_app/activity_list.txt",
  "original_srs_path": "D:/nju/需求生成系统/ScenReq/Req/demo/output/应用介绍+Activity分析/com.ferrarid.converterpro/com.ferrarid.converterpro_SRS.json",
  "original_tests_path": "D:/nju/需求生成系统/ScenReq/Req/demo/output/应用介绍+Activity分析/com.ferrarid.converterpro/com.ferrarid.converterpro_TestRequirements.json",
  "output_dir": "D:/nju/需求生成系统/ScenReq/Req/output/test_requirements"
}
```

返回将包含：
- `mode`：`llm` 或 `heuristic`
- `failure_signals`：抽取到的失败标签
- `output_srs_path` / `output_tests_path`
- `warnings`：上下文不足或文件缺失等告警

## 后续热拔插接入建议
- 在测试智能体失败回调处直接调用 `/api/repair/requirements`。
- 将日志路径与截图路径作为标准参数传入。
- 可配置“仅失败N次后触发”，避免过度生成。
