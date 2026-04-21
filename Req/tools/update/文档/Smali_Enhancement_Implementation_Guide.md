# Smali 增强模块实现与测试说明

## 1. 本次新增内容（仅 update 目录）
本次实现严格遵循“不修改原系统代码”的约束，所有新增文件位于 `Req/tools/update/`：

1. `resource_indexer.py`
- 作用：解析 Manifest、布局 XML、字符串资源，生成资源索引。
- 技术原理：XML 结构化抽取 + 资源引用解析（`@string/...`）。
- 预期效果：恢复接近源码层的 UI 元素语义（id/text/hint/inputType/onClick）。

2. `smali_ir_builder.py`
- 作用：从 `smali*` 目录提取类、方法、调用关系和关键行为动作。
- 技术原理：Smali 模式匹配（`.class/.method/invoke-*`）+ 行为特征识别（点击、跳转、Toast、网络、DB）。
- 预期效果：得到方法级中间表示（IR）与调用关系图基础数据。

3. `intent_graph_builder.py`
- 作用：融合资源索引和 Smali IR，构建意图图与操作步骤草案。
- 技术原理：Activity 维度证据聚合 + 关键词分类 + 步骤模板生成。
- 预期效果：形成可追溯的 `intent_units`，每个意图包含入口、步骤、证据、置信度。

4. `legacy_bridge.py`
- 作用：将意图单元导出为原系统可复用的解析桥接文件。
- 技术原理：意图聚合结果转换为 `activity/function` 分析结构 + Prompt 上下文补充。
- 预期效果：增强 APK 解析信息可直接喂给原系统既有需求生成逻辑。

5. `run_smali_enhancement.py`
- 作用：独立增强管线入口，不接入原流程。
- 技术原理：分阶段调用（资源索引 -> IR -> 意图图 -> 桥接导出）。
- 预期效果：一次命令完成解析增强并输出可复用桥接产物。

6. `test_smali_enhancement.py`
- 作用：面向真实 APK 反编译目录的测试函数。
- 技术原理：调用增强管线后断言关键桥接产物存在且意图单元非空。
- 预期效果：快速验证模块可运行性和桥接输出完整性。

---

## 2. 测试对象与测试命令
测试对象（真实 APK 反编译目录）：
- `d:/nju/需求生成系统/APP/test/workdir/decompiled/com.MobileTicket`

执行命令（在 `ScenReq` 根目录）：

```bash
python -m Req.tools.update.test_smali_enhancement
```

---

## 3. 测试结果摘要
本次测试已通过，输出统计：
1. Activities: 170
2. Layouts: 559
3. Smali classes: 5
4. Smali methods: 67
5. Smali calls: 321
6. Intent units: 170
7. Legacy activity items: 170

产物目录：
- `Req/tools/update/output/com.MobileTicket/`

核心产物文件：
1. `resource_index.json`
2. `smali_ir.json`
3. `intent_graph.json`
4. `activity_analysis_enhanced.json`
5. `activity_analysis_enhanced.txt`
6. `prompt_context_enhanced.txt`
7. `legacy_parse_bundle.json`
8. `pipeline_summary.json`

---

## 4. 当前版本边界
1. 当前是“可运行原型”，优先保证可追溯产物闭环。
2. 在大体量 APK 上，`intent_units` 数量会接近 Activity 数量，需后续做聚类去重。
3. 当前调用链恢复为轻量规则版，尚未实现完整 CFG 基本块级分支合并。

---

## 5. 下一步优化建议（仍可保持旁路）
1. 增加 `intent_units` 聚类与去重，降低重复需求。
2. 增加低置信意图过滤阈值，提升需求质量。
3. 引入分层步骤模板（功能级/场景级），减少模板化描述。
4. 增加 smali 多 dex 增量缓存，提升大包解析性能。
5. 增加证据打分（资源证据、调用证据、文本证据）并输出解释字段。

---

## 6. 已落地的桥接输出策略
当前版本已支持“按功能类型聚合后导出桥接信息”，规则如下：
1. 每个聚合功能类型输出一条 activity/function 摘要，便于原系统复用。
2. 保留入口、步骤摘要、置信度等关键信号，支持后续 Prompt 增强。
3. 输出结果不直接覆盖原系统需求文件，保持无侵入。
