# Manual Edit Sync (Hot-Plug Reserved Module)

## 目标
该模块用于支持人工修改 Word 报告后，自动回写对应的 JSON 文件。

说明：
- 不修改现有主流程逻辑。
- 作为独立模块预留，后续可热拔插接入现有后端。

## 支持能力
- 单次同步接口：手动调用 API，将 `.docx` 回写到 `*_SRS.json` 与 `*_TestRequirements.json`。
- 自动监听接口：启动后轮询 Word 文件修改时间，检测到保存后自动回写。

## 目录
- `word_json_sync.py`：核心同步逻辑（无系统耦合）。
- `api.py`：独立 FastAPI 接口（可单独启动）。
- `run_api.py`：启动脚本。

## Word 与 JSON 对应关系
根据现有 `Req/tools/report_generator.py` 的表格格式解析：

- 表1（软件需求）
  - `ID` -> `id`
  - `Name` -> `name`
  - `Requirement` -> `requirement`
  - `Type` -> `type`

- 表2（测试需求）
  - `ID` -> `id`
  - `Name` -> `name`
  - `Description/Objective` -> `description` + `objective`
  - `Test Data` -> `test_data`
  - `Expected Result` -> `expected_result`

注意：
- 测试需求里 Word 不直接展示的字段（例如 `extra_info`）会在按 `id` 合并时保留，不会被覆盖删除。
- 以 Word 表格行作为最终条目集合，删除行会体现在 JSON 中。

## 路径自动推断
当只提供 report 路径时，自动推断：
- `xxx_功能测试报告.docx` -> `xxx_SRS.json`
- `xxx_功能测试报告.docx` -> `xxx_TestRequirements.json`

文件需位于同一目录。

## 快速运行
在 `ScenReq` 根目录执行：

```bash
python -m manual_edit_sync.run_api
```

默认监听：`http://0.0.0.0:8011`

## API 示例
### 1) 单次同步

`POST /api/manual-edit/sync`

```json
{
  "report_path": "D:/nju/需求生成系统/ScenReq/Req/demo/output/应用介绍+Activity分析/com.ferrarid.converterpro/com.ferrarid.converterpro_功能测试报告.docx"
}
```

### 2) 启动自动监听

`POST /api/manual-edit/watch/start`

```json
{
  "report_path": "D:/.../com.ferrarid.converterpro_功能测试报告.docx",
  "poll_interval_seconds": 2.0
}
```

### 3) 停止自动监听

`POST /api/manual-edit/watch/stop`

```json
{
  "report_path": "D:/.../com.ferrarid.converterpro_功能测试报告.docx"
}
```

## 接入建议（后续）
- 方案A：在主后端中挂载该模块路由（`app.include_router` 或直接转发）。
- 方案B：保持独立服务，通过主系统配置项控制是否启用。
- 方案C：任务完成后自动启动 watcher，实现“下载报告-人工修改-自动回写”的闭环。
