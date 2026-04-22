"""
Req.tools - APK 分析与需求生成工具包

本模块提供 APK 反编译、Activity 分析、需求生成等核心功能。

目录结构：
- 基础工具（保留）：
  - apktool.py        : APK 反编译工具
  - parse_flow.py     : 主分析流程入口（已整合增强版流水线）
  - report_generator.py: Word 报告生成
  - zip_utils.py      : ZIP 打包工具

- 增强版本（update/）：
  - smali_ir_builder.py       : Smali IR 构建
  - resource_indexer.py       : 资源索引构建
  - intent_graph_builder.py   : 意图图构建
  - llm_assist.py             : LLM 辅助意图精炼
  - run_smali_enhancement.py  : 增强流水线入口
  - legacy_bridge.py          : 旧版兼容桥接
"""
