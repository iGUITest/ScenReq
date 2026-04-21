# Update 增强模块实现说明

本文档描述 `Req/tools/update` 模块当前实现逻辑、关键技术细节与输出产物定义。该模块为旁路增强能力，不改动原系统主流程。

## 1. 实现逻辑总览

增强管线入口：

```bash
python -m Req.tools.update.run_smali_enhancement --app-dir "<decompiled_app_dir>" --output-dir "Req/tools/update/output/<app_name>"
```

标准处理流程：
1. 资源索引阶段：读取 Manifest、资源目录与关键配置，产出结构化资源索引。
2. Smali 解析阶段：构建类/方法/调用关系的中间表示（IR），提取 UI、网络、存储等行为证据。
3. 意图图构建阶段：将分散证据映射到功能意图节点，进行置信度计算、同类聚合与低置信过滤。
4. 桥接导出阶段：将增强结果导出为原系统可复用的解析输入（而非直接生成需求）。
5. 汇总阶段：输出统计信息（输入证据量、过滤前后数量、桥接条目数量）。

技术原理：
- 通过“静态结构证据 + 语义关键词 + 规则映射”实现对 APP 功能意图的可解释抽取。
- 用聚合和过滤抑制噪声，减少“通用功能”占比，提高需求可执行性。

预期效果：
- 输出“高质量解析证据 + 功能意图结构”，供原系统既有需求生成逻辑复用。
- 对 Flutter 或 Activity 信号较弱的应用，仍可通过 assets/字符串证据完成功能拆分。

## 2. 模块级技术细节

### 2.1 `resource_indexer.py`
- 输入：反编译目录（含 `AndroidManifest.xml`、`res/` 等）。
- 处理：提取包名、组件声明、权限、资源名与部分文案线索。
- 输出：`resource_index.json`。

### 2.2 `smali_ir_builder.py`
- 输入：`smali*/` 目录。
- 处理：
	- 解析类名、方法签名、调用关系。
	- 识别关键 API 调用（如网络请求、文件读写、路由跳转）。
	- 聚合为统一 IR，供后续意图推断。
- 输出：`smali_ir.json`。

### 2.3 `intent_graph_builder.py`
- 输入：资源索引 + Smali IR。
- 处理：
	- 构建功能意图节点（intent nodes）。
	- 进行证据融合与置信打分。
	- 按功能类型做同类聚合（避免重复功能簇）。
	- 删除低置信节点（默认阈值可配置）。
	- 引入 Flutter 资产关键词和文案线索，细化通用节点。
- 输出：`intent_graph.json`。

### 2.4 `legacy_bridge.py`
- 输入：资源索引 + Smali IR + 意图图。
- 处理：
	- 将意图单元转换为原系统可消费的 activity 分析格式。
	- 导出补充提示词上下文（用于增强原有需求生成 Prompt）。
	- 打包桥接文件，便于后续流程直接读取。
- 输出：
	- `activity_analysis_enhanced.json`
	- `activity_analysis_enhanced.txt`
	- `prompt_context_enhanced.txt`
	- `legacy_parse_bundle.json`

### 2.5 `run_smali_enhancement.py`
- 作用：串联所有阶段，统一参数、日志和输出路径。
- 典型参数：
	- `--app-dir`：反编译应用目录。
	- `--output-dir`：输出目录。
	- 可选阈值参数（若实现中启用）用于控制置信过滤与最大功能类数量。
	- `--enable-llm-assist`：开启 LLM 意图精炼（默认关闭）。
	- `--llm-model`：模型名，默认 `qwen-plus`。
	- `--llm-trigger-confidence`：低置信触发阈值，默认 `0.55`。
	- `--llm-max-candidates`：单次送入 LLM 的意图上限，默认 `8`。
	- `--llm-lang`：提示词语言，`zh/en`。

### 2.6 `llm_assist.py`
- 作用：对低置信/通用意图做二次语义精炼，用于提升跨 APP 泛化能力。
- 调用方式：通过 LangChain 复用项目 `get_chat()` 客户端调用通义千问。
- API Key 读取顺序：
	- 优先：环境变量 `descope`
	- 兜底：环境变量 `DASHSCOPE_API_KEY`
- 触发策略：
	- `intent_type` 为 `通用功能` 或 `列表浏览`
	- 或 `confidence < llm_trigger_confidence`
- 安全机制：
	- 输出必须是 JSON；不合法结果自动丢弃。
	- 调用失败自动回退到规则结果。

### 2.7 `test_smali_enhancement.py`
- 作用：端到端测试入口，覆盖“反编译 -> 增强管线 -> 结果校验”。
- 用途：回归验证规则变更是否影响结果稳定性。

## 3. 输出产物说明

默认输出目录：`Req/tools/update/output/<app_name>/`

### 3.1 `resource_index.json`
- 用途：记录资源侧证据。
- 典型字段：
	- `package_name`
	- `permissions`
	- `activities`
	- `resources`
	- `asset_hints`

### 3.2 `smali_ir.json`
- 用途：记录代码结构与行为证据。
- 典型字段：
	- `classes`
	- `methods`
	- `call_edges`
	- `api_signals`

### 3.3 `intent_graph.json`
- 用途：记录功能意图图与过滤结果。
- 典型字段：
	- `intents_raw_count`
	- `intents_filtered_count`
	- `dropped_low_confidence`
	- `intent_nodes`（含 `intent_type`、`confidence`、`evidence`）

### 3.4 `activity_analysis_enhanced.json`
- 用途：桥接原系统分析输入，格式兼容 `activity/function` 列表。
- 典型字段：
	- `activity`
	- `function`

### 3.5 `activity_analysis_enhanced.txt`
- 用途：文本版 activity 功能分析，便于人工检查与日志留存。

### 3.6 `prompt_context_enhanced.txt`
- 用途：给原系统提示词追加的增强上下文（高置信功能类型、权限概览等）。

### 3.7 `legacy_parse_bundle.json`
- 用途：解析增强总包，供原有需求生成逻辑读取。
- 典型字段：
	- `manifest`
	- `resource_stats`
	- `smali_stats`
	- `intent_filters`
	- `intent_units`
	- `legacy_activity_analysis_json`
	- `legacy_activity_analysis_txt`
	- `prompt_context_txt`

### 3.8 `pipeline_summary.json`
- 用途：记录本次运行统计与质量指标。
- 典型字段：
	- `app_name`
	- `resource_signals_count`
	- `smali_signals_count`
	- `intent_before_filter`
	- `intent_after_filter`
	- `legacy_activity_items`

### 3.8 `llm_refinement.json`
- 用途：记录 LLM 辅助精炼过程与结果。
- 典型字段：
	- `stats.enabled`
	- `stats.model`
	- `stats.api_key_source`（`descope` / `DASHSCOPE_API_KEY` / `missing`）
	- `stats.status`（`ok` / `skipped_*` / `failed_fallback`）
	- `stats.candidate_count`
	- `stats.accepted_count`
	- `candidates`
	- `accepted`

## 4. 运行与验证建议

推荐命令：

```bash
python -m Req.tools.update.test_smali_enhancement
```

开启 LLM 辅助的增强命令：

```bash
python -m Req.tools.update.run_smali_enhancement --app-dir "<decompiled_app_dir>" --output-dir "Req/tools/update/output/<app_name>" --enable-llm-assist --llm-model qwen-plus --llm-trigger-confidence 0.55 --llm-max-candidates 8 --llm-lang zh
```

验证重点：
1. `intent_graph.json` 中低置信删除数量是否异常偏大。
2. `activity_analysis_enhanced.json` 是否可被原系统分析输入复用。
3. `pipeline_summary.json` 中过滤前后数量变化是否符合预期。

常见调优方向：
- 关键词词典扩展：提升功能识别召回率。
- 置信阈值微调：平衡噪声与覆盖。
- 类型聚合规则调整：降低重复功能输出。
