# LLM 辅助泛化设计（Update 模块）

## 1. 目标
在不替换现有规则管线的前提下，引入可选 LLM 辅助层，提升跨 APP 的功能意图识别泛化能力，并将增强结果桥接给原系统需求生成逻辑。

设计原则：
- 默认关闭，显式开启。
- 规则优先，LLM 增强。
- 失败自动回退，不影响主流程可用性。
- 证据约束，降低幻觉。

## 2. 接入位置
现有流程：
1. `resource_indexer.py`
2. `smali_ir_builder.py`
3. `intent_graph_builder.py`
4. `legacy_bridge.py`

增强后流程：
1. `resource_indexer.py`
2. `smali_ir_builder.py`
3. `intent_graph_builder.py`
4. `llm_assist.py`（新增，可选）
5. `legacy_bridge.py`

说明：LLM 仅精炼意图层（intent units），不在 update 模块内直接生成最终需求，保证结构稳定并与原系统解耦。

## 3. 模型与调用方式
- 模型：通义千问（默认 `qwen-plus`，可参数化）。
- 调用：LangChain `get_chat()`（复用项目已有客户端封装）。
- API Key：
  - 优先读取环境变量 `descope`。
  - 若未设置，再读取 `DASHSCOPE_API_KEY`。

## 4. 触发策略（控制成本与风险）
只将“高不确定性”意图送入 LLM：
- `intent_type` 属于 `通用功能` 或 `列表浏览`。
- 或 `confidence < llm_trigger_confidence`（默认 0.55）。
- 送入数量上限 `llm_max_candidates`（默认 8）。

## 5. 输入输出约束
输入给 LLM 的内容：
- `source_intent_id`
- `name/entry/intent_type/confidence`
- 精简证据：`methods/actions/layout_views`
- 现有步骤（用于参考）

要求 LLM 输出严格 JSON：
- `source_intent_id`
- `intent_type`
- `name`
- `confidence`
- `steps`
- `success_signal`
- `failure_signal`

校验规则：
- `source_intent_id` 必须命中已有意图。
- `intent_type` 不能为空。
- `confidence` 强制裁剪到 [0.05, 0.99]。
- `steps` 少于 3 条则回退原步骤。

## 6. 失败与回退机制
- 未配置 API Key：跳过 LLM，保留规则结果。
- LLM 调用异常：记录错误，保留规则结果。
- 解析失败/字段不合法：忽略该条精炼，保留原条目。

## 7. 新增产物
- `llm_refinement.json`
  - 记录候选意图、接受结果、状态统计、错误信息。
- `pipeline_summary.json` 增补字段：
  - `llm_assist_enabled`
  - `llm_assist_status`
  - `llm_assist_candidates`
  - `llm_assist_accepted`

## 8. 运行方式
默认规则模式：

```bash
python -m Req.tools.update.run_smali_enhancement --app-dir "<decompiled_app_dir>" --output-dir "Req/tools/update/output/<app_name>"
```

开启 LLM 辅助：

```bash
python -m Req.tools.update.run_smali_enhancement --app-dir "<decompiled_app_dir>" --output-dir "Req/tools/update/output/<app_name>" --enable-llm-assist --llm-model qwen-plus --llm-trigger-confidence 0.55 --llm-max-candidates 8 --llm-lang zh
```

## 9. 泛化评估建议
建议在多 APP 数据集上对比两组：
- Baseline：仅规则
- Hybrid：规则 + LLM 辅助

关注指标：
- 意图多样性（去通用化程度）
- 桥接可复用性（activity/function 与原流程兼容度）
- 误识别率（无证据支撑条目占比）
- 平均单 APP 处理耗时与 token 成本

## 10. 后续可扩展
- 增加术语字典自动扩展：从 LLM 结果反哺关键词词典。
- 引入双阶段校验：LLM 生成后再用规则进行一致性判定。
- 按 APP 类型自适应阈值：工具类/内容类/交易类采用不同触发阈值。
