# ScenReq 优化迭代方案

> 基于论文《From Exploration to Specification: LLM-Based Property Generation for Mobile App Testing》(PropGen) 的方法借鉴

---

## 一、背景与目标

### 1.1 当前 ScenReq 定位
- **核心能力**：从 APK/界面截图/应用描述中自动生成自然语言需求
- **优势**：无需运行 App，支持静态分析场景
- **待优化点**：需求质量稳定性、幻觉过滤、可验证性

### 1.2 PropGen 核心借鉴价值
| PropGen 特性 | ScenReq 可迁移价值 |
|-------------|-------------------|
| 功能假设 + 控件接地 | 需求与界面元素绑定，减少幻觉 |
| 行为证据结构化摘要 | 从执行轨迹/截图序列中抽象需求 |
| 跨状态功能记忆 | 避免重复生成，提升效率 |
| 反馈驱动精化 | 需求质量迭代优化机制 |
| 自然语言中间表示 | 分层生成，支持多视角输出 |

### 1.3 优化目标
1. **准确性**：提升生成需求的合理性和准确性
2. **可验证性**：需求可被后续测试验证
3. **一致性**：相似 App/功能生成一致的需求描述
4. **效率**：减少重复计算，支持批量处理

---

## 二、优化方案总览

```
┌─────────────────────────────────────────────────────────────────┐
│                    ScenReq 优化架构 V2.0                         │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: 需求输出层                                              │
│  ├── 需求描述生成（自然语言）                                      │
│  ├── 测试用例生成（可执行）                                        │
│  └── 用户故事生成（敏捷格式）                                      │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: 功能意图层（新增）                                       │
│  ├── 功能意图推断（What + Why）                                    │
│  ├── 控件接地绑定（Where）                                         │
│  └── 功能签名生成（用于去重）                                      │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: 输入处理层                                               │
│  ├── APK 静态分析（Activity/布局/权限）                            │
│  ├── 界面截图理解（控件检测 + OCR）                                │
│  └── 应用描述解析（商店文案/官网介绍）                             │
├─────────────────────────────────────────────────────────────────┤
│  基础设施层（新增）                                                │
│  ├── 功能记忆池（全局功能库）                                      │
│  ├── 需求验证器（一致性检验）                                      │
│  └── 反馈精化模块（迭代优化）                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、核心优化模块详解

### 模块一：功能意图层（Function Intent Layer）

#### 3.1.1 设计目标
将"输入 → 需求"的单步生成拆分为"输入 → 功能意图 → 需求"，引入中间抽象层。

#### 3.1.2 功能意图结构
```yaml
功能意图 (FunctionIntent):
  intent_id: "unique_hash"           # 唯一标识
  
  # What: 功能是什么
  what:
    action: "添加收藏"                # 动作
    target: "笔记内容"                # 操作对象
    expected_outcome: "笔记被加入收藏列表"  # 预期结果
  
  # Why: 功能目的
  why:
    user_goal: "保存感兴趣的内容以便后续查看"
    business_value: "提升用户留存率"
  
  # Where: 在哪里触发（控件接地）
  where:
    trigger_context: "笔记详情页"
    trigger_widgets:                # 关键控件列表
      - widget_id: "btn_favorite"
        widget_type: "ImageButton"
        widget_desc: "心形收藏按钮"
        location: "toolbar"
    preconditions:                  # 前置条件
      - "当前处于笔记详情页"
      - "笔记未被收藏"
  
  # How: 如何操作
  how:
    interaction_flow:
      - step: 1
        action: "点击收藏按钮"
        widget_ref: "btn_favorite"
      - step: 2
        action: "系统反馈"
        expected_ui_change: "按钮变为填充状态，显示Toast提示"
  
  # 元数据
  metadata:
    source_app: "OmniNotes"
    source_screens: ["screenshot_01.png", "screenshot_02.png"]
    confidence: 0.92
    signature: "hash_of_what_and_where"  # 用于去重
```

#### 3.1.3 生成流程
```python
# 伪代码示意
def generate_function_intent(input_data: AppInput) -> FunctionIntent:
    # Step 1: 提取界面元素
    widgets = extract_widgets(input_data.screenshots)
    
    # Step 2: MLLM 推断功能意图
    prompt = f"""
    基于以下信息推断功能意图：
    - 应用名称: {input_data.app_name}
    - 应用描述: {input_data.description}
    - 当前界面控件: {widgets}
    
    请输出：
    1. 该界面支持什么功能？
    2. 用户为什么要用这个功能？
    3. 触发该功能的界面元素是什么？
    4. 操作后预期发生什么变化？
    """
    
    intent = mllm.generate(prompt, schema=FunctionIntentSchema)
    
    # Step 3: 控件接地验证
    intent.where.trigger_widgets = validate_widget_bindings(
        intent.what.action, 
        widgets
    )
    
    # Step 4: 生成功能签名
    intent.metadata.signature = compute_signature(intent.what, intent.where)
    
    return intent
```

---

### 模块二：控件接地机制（Widget Grounding）

#### 3.2.1 核心思想
每条功能意图必须绑定到**可观测的界面元素**，避免 LLM 凭空捏造功能。

#### 3.2.2 控件标注规范
```python
# 界面控件结构化表示
Widget = {
    "id": "w_001",                    # 系统分配唯一ID
    "type": "ImageButton",            # 控件类型
    "bounds": [x1, y1, x2, y2],       # 屏幕坐标
    "attributes": {
        "resource_id": "btn_favorite",
        "content_desc": "收藏",
        "text": None,
        "clickable": True,
        "visible": True
    },
    "semantic_label": "[收藏按钮]"     # 用于LLM引用的标签
}
```

#### 3.2.3 接地验证规则
```python
def validate_grounding(intent: FunctionIntent, widgets: List[Widget]) -> bool:
    """验证功能意图是否正确接地"""
    
    for trigger in intent.where.trigger_widgets:
        # 规则1: 引用的控件必须存在
        matched = find_widget_by_ref(trigger.widget_ref, widgets)
        if not matched:
            return False, f"控件 {trigger.widget_ref} 不存在"
        
        # 规则2: 控件必须是可交互的
        if not matched.attributes.clickable:
            return False, f"控件 {trigger.widget_ref} 不可点击"
        
        # 规则3: 控件语义与功能描述一致
        semantic_match = check_semantic_consistency(
            intent.what.action, 
            matched.attributes
        )
        if semantic_match.score < 0.7:
            return False, f"控件语义与功能描述不一致"
    
    return True, "接地验证通过"
```

#### 3.2.4 接地失败处理
```python
# 接地失败时的修复策略
def repair_grounding(intent: FunctionIntent, widgets: List[Widget]) -> FunctionIntent:
    # 策略1: 模糊匹配找相似控件
    similar = find_similar_widgets(intent.what.action, widgets)
    
    # 策略2: 询问 LLM 重新推断
    if not similar:
        prompt = f"功能'{intent.what.action}'在当前界面无匹配控件，请重新推断或标记为不可接地"
        intent = mllm.generate(prompt)
        intent.metadata.grounding_status = "ungrounded"
    else:
        intent.where.trigger_widgets = similar
        intent.metadata.grounding_status = "repaired"
    
    return intent
```

---

### 模块三：功能记忆池（Function Memory Pool）

#### 3.3.1 设计目标
- 避免在相似界面/相似 App 中重复推断相同功能
- 支持跨 App 的功能复用和迁移

#### 3.3.2 功能签名设计
```python
class FunctionSignature:
    """用于快速比对和去重的功能签名"""
    
    def __init__(self, intent: FunctionIntent):
        # 语义签名：功能意图的向量表示
        self.semantic_hash = self._compute_semantic_hash(intent.what)
        
        # 结构签名：触发条件的结构化表示
        self.struct_hash = self._compute_struct_hash(intent.where)
        
        # 组合签名
        self.composite = hash((self.semantic_hash, self.struct_hash))
    
    def _compute_semantic_hash(self, what: WhatInfo) -> str:
        """基于动作+对象+结果的语义哈希"""
        text = f"{what.action}:{what.target}:{what.expected_outcome}"
        embedding = text_encoder.encode(text)
        return lsh_hash(embedding)  # 局部敏感哈希
    
    def _compute_struct_hash(self, where: WhereInfo) -> str:
        """基于触发上下文的结构哈希"""
        key_elements = [
            where.trigger_context,
            sorted([w.widget_type for w in where.trigger_widgets])
        ]
        return hashlib.md5(str(key_elements).encode()).hexdigest()
```

#### 3.3.3 记忆池结构
```yaml
FunctionMemoryPool:
  version: "2.0"
  
  # 功能库：按签名索引
  function_library:
    "sig_abc123":
      intent: <FunctionIntent对象>
      usage_count: 15
      source_apps: ["OmniNotes", "Markor", "Notion"]
      quality_score: 0.94
      last_used: "2026-04-22"
    
  # 相似度索引：支持模糊匹配
  similarity_index:
    type: "faiss"  # 或 hnswlib
    dimension: 768
    
  # 分类索引：按功能类别组织
  category_index:
    "内容管理": ["sig_abc123", "sig_def456", ...]
    "社交互动": ["sig_ghi789", ...]
    "系统设置": [...]
```

#### 3.3.4 记忆检索与复用流程
```python
def retrieve_or_create_intent(
    input_data: AppInput,
    memory_pool: FunctionMemoryPool
) -> FunctionIntent:
    
    # Step 1: 提取当前界面的候选签名
    candidate_signatures = extract_candidate_signatures(input_data)
    
    # Step 2: 在记忆池中检索相似功能
    for sig in candidate_signatures:
        similar = memory_pool.similarity_search(sig, top_k=3)
        
        for match in similar:
            if match.similarity > 0.85:
                # 高相似度：直接复用并适配
                return adapt_intent(match.intent, input_data)
            elif match.similarity > 0.70:
                # 中等相似度：作为参考生成新意图
                return generate_with_reference(input_data, match.intent)
    
    # Step 3: 无匹配，全新生成
    new_intent = generate_function_intent(input_data)
    memory_pool.add(new_intent)
    return new_intent
```

---

### 模块四：需求验证与精化（Validation & Refinement）

#### 3.4.1 验证器设计
```python
class RequirementValidator:
    """多维度需求验证器"""
    
    def validate(self, intent: FunctionIntent) -> ValidationReport:
        report = ValidationReport()
        
        # 维度1: 接地验证
        report.grounding = self._check_grounding(intent)
        
        # 维度2: 完整性验证
        report.completeness = self._check_completeness(intent)
        
        # 维度3: 一致性验证
        report.consistency = self._check_consistency(intent)
        
        # 维度4: 可验证性评估
        report.verifiability = self._assess_verifiability(intent)
        
        return report
    
    def _check_grounding(self, intent: FunctionIntent) -> CheckResult:
        """验证是否有效接地到界面元素"""
        if not intent.where.trigger_widgets:
            return CheckResult(passed=False, issue="未绑定触发控件")
        
        for w in intent.where.trigger_widgets:
            if not w.widget_id:
                return CheckResult(passed=False, issue=f"控件 {w.widget_desc} 无有效ID")
        
        return CheckResult(passed=True)
    
    def _check_completeness(self, intent: FunctionIntent) -> CheckResult:
        """验证功能意图结构完整"""
        required_fields = ['what.action', 'what.target', 'where.trigger_context']
        missing = [f for f in required_fields if not get_nested_attr(intent, f)]
        
        if missing:
            return CheckResult(passed=False, issue=f"缺失字段: {missing}")
        return CheckResult(passed=True)
    
    def _check_consistency(self, intent: FunctionIntent) -> CheckResult:
        """验证内部一致性"""
        # 检查：动作与控件类型是否匹配
        action = intent.what.action
        widget_types = [w.widget_type for w in intent.where.trigger_widgets]
        
        if "输入" in action and "EditText" not in widget_types:
            return CheckResult(
                passed=False, 
                issue=f"动作'{action}'需要输入控件，但绑定的是{widget_types}"
            )
        
        return CheckResult(passed=True)
    
    def _assess_verifiability(self, intent: FunctionIntent) -> ScoreResult:
        """评估需求的可验证性（0-1分）"""
        score = 0.0
        
        # 有明确触发控件 +0.3
        if intent.where.trigger_widgets:
            score += 0.3
        
        # 有明确预期结果 +0.3
        if intent.what.expected_outcome:
            score += 0.3
        
        # 预期结果可观测（UI变化） +0.2
        if self._is_ui_observable(intent.what.expected_outcome):
            score += 0.2
        
        # 有前置条件定义 +0.2
        if intent.where.preconditions:
            score += 0.2
        
        return ScoreResult(score=score)
```

#### 3.4.2 精化策略
```python
def refine_intent(intent: FunctionIntent, report: ValidationReport) -> FunctionIntent:
    """基于验证报告精化功能意图"""
    
    # 策略1: 接地失败 → 重新推断或标记
    if not report.grounding.passed:
        intent = repair_grounding(intent, get_available_widgets())
    
    # 策略2: 完整性不足 → 补充缺失信息
    if not report.completeness.passed:
        prompt = f"请补充以下缺失信息: {report.completeness.issue}"
        intent = mllm.generate(prompt, base_intent=intent)
    
    # 策略3: 一致性错误 → 修正矛盾
    if not report.consistency.passed:
        prompt = f"存在不一致: {report.consistency.issue}，请修正"
        intent = mllm.generate(prompt, base_intent=intent)
    
    # 策略4: 可验证性低 → 增强可观测性
    if report.verifiability.score < 0.6:
        prompt = """
        当前需求可验证性较低，请增强以下方面：
        1. 明确触发控件的具体标识
        2. 描述可观测的预期结果（UI变化）
        3. 定义清晰的前置条件
        """
        intent = mllm.generate(prompt, base_intent=intent)
    
    return intent
```

#### 3.4.3 迭代精化流程
```
生成初始功能意图
    ↓
运行验证器 → 生成验证报告
    ↓
检查是否全部通过？
    ├── 是 → 进入需求输出阶段
    └── 否 → 应用精化策略
              ↓
         检查迭代次数 < 上限？
              ├── 是 → 返回验证步骤
              └── 否 → 标记为"需人工审核"，输出当前最佳版本
```

---

### 模块五：多视角需求输出

#### 3.5.1 从功能意图到不同输出格式
```python
def generate_requirements(intent: FunctionIntent, output_format: str) -> str:
    """基于功能意图生成不同格式的需求描述"""
    
    generators = {
        "natural_language": generate_nl_requirement,
        "user_story": generate_user_story,
        "test_case": generate_test_case,
        "gherkin": generate_gherkin_scenario
    }
    
    return generators[output_format](intent)

# 自然语言需求
def generate_nl_requirement(intent: FunctionIntent) -> str:
    return f"""
    需求名称：{intent.what.action}{intent.what.target}
    
    需求描述：
    作为用户，我需要在{intent.where.trigger_context}中{intent.what.action}，
    以便{intent.why.user_goal}。
    
    前置条件：
    {format_preconditions(intent.where.preconditions)}
    
    操作流程：
    {format_interaction_flow(intent.how.interaction_flow)}
    
    预期结果：
    {intent.what.expected_outcome}
    """

# 用户故事格式
def generate_user_story(intent: FunctionIntent) -> str:
    return f"""
    ## 用户故事
    
    **作为** 想要{intent.why.user_goal}的用户
    **我希望** 在{intent.where.trigger_context}中{intent.what.action}
    **从而** {intent.what.expected_outcome}
    
    **验收标准：**
    - 当{intent.where.preconditions[0]}时，可以看到{intent.where.trigger_widgets[0].widget_desc}
    - 点击{intent.where.trigger_widgets[0].widget_desc}后，{intent.what.expected_outcome}
    """

# Gherkin 格式（用于自动化测试）
def generate_gherkin_scenario(intent: FunctionIntent) -> str:
    return f"""
    Feature: {intent.what.action}功能
    
    Scenario: 用户成功{intent.what.action}
      Given {intent.where.preconditions[0]}
      And 用户在{intent.where.trigger_context}
      When 用户点击"{intent.where.trigger_widgets[0].widget_desc}"
      Then {intent.what.expected_outcome}
    """
```

---

## 四、实施路线图

### Phase 1: 基础层建设（2-3周）
- [ ] 设计 FunctionIntent 数据结构
- [ ] 实现控件检测与标注模块
- [ ] 搭建功能记忆池基础框架

### Phase 2: 核心功能开发（3-4周）
- [ ] 实现功能意图生成模块
- [ ] 实现控件接地与验证机制
- [ ] 实现记忆池检索与复用

### Phase 3: 质量提升（2-3周）
- [ ] 实现需求验证器
- [ ] 实现精化策略
- [ ] 集成迭代精化流程

### Phase 4: 输出扩展（2周）
- [ ] 实现多格式需求生成
- [ ] 集成测试用例生成
- [ ] 端到端流程验证

### Phase 5: 评估与优化（持续）
- [ ] 设计定量评估指标
- [ ] 在测试集上验证效果
- [ ] 迭代优化各模块

---

## 五、评估指标设计

### 5.1 准确性指标
| 指标 | 定义 | 目标值 |
|-----|------|-------|
| 功能意图有效性 | 人工判断合理的功能意图占比 | > 90% |
| 接地成功率 | 成功绑定到控件的功能占比 | > 85% |
| 需求准确性 | 需求描述与真实功能一致的比例 | > 90% |

### 5.2 效率指标
| 指标 | 定义 | 目标值 |
|-----|------|-------|
| 功能复用率 | 从记忆池复用的功能占比 | > 30% |
| 平均生成时间 | 单个 App 需求生成耗时 | < 5分钟 |
| 迭代精化次数 | 平均每个意图的精化轮数 | < 2 |

### 5.3 可验证性指标
| 指标 | 定义 | 目标值 |
|-----|------|-------|
| 可验证需求比例 | 可生成测试用例的需求占比 | > 80% |
| 测试通过率 | 生成测试用例的执行成功率 | > 75% |

---

## 六、与 PropGen 的对比总结

| 维度 | PropGen | 优化后的 ScenReq |
|------|---------|-----------------|
| **输入** | 可运行的 App | APK / 截图 / 描述 |
| **核心流程** | 动态探索 → 行为证据 → 性质 | 静态分析 → 功能意图 → 需求 |
| **控件接地** | 运行时控件绑定 | 截图/布局分析绑定 |
| **记忆机制** | 跨状态功能池 | 跨 App 功能库 |
| **精化机制** | 基于测试反馈 | 基于验证规则 |
| **输出** | 可执行测试性质 | 多格式需求描述 |
| **适用场景** | 白盒/可运行测试 | 黑盒/静态分析 |

---

## 七、附录：Prompt 设计参考

### A.1 功能意图推断 Prompt
```
你是一位移动应用功能分析专家。请基于以下信息推断该界面支持的功能：

【应用信息】
- 应用名称: {app_name}
- 应用类型: {app_category}
- 应用描述: {app_description}

【界面信息】
- 当前页面: {activity_name}
- 可交互控件列表:
{formatted_widgets}

【分析要求】
1. 识别该界面支持的核心功能（What）
2. 分析用户使用该功能的目的（Why）
3. 指出触发该功能的具体控件（Where）
4. 描述操作后的预期效果（How）

请按以下 JSON 格式输出：
{
  "what": {
    "action": "动作描述",
    "target": "操作对象",
    "expected_outcome": "预期结果"
  },
  "why": {
    "user_goal": "用户目标",
    "business_value": "业务价值"
  },
  "where": {
    "trigger_context": "触发上下文",
    "trigger_widgets": ["控件引用"],
    "preconditions": ["前置条件"]
  },
  "how": {
    "interaction_flow": [{"step": 1, "action": "..."}]
  }
}
```

### A.2 需求精化 Prompt
```
以下是一个功能意图描述，但在验证中发现以下问题：

【原始意图】
{intent_json}

【验证问题】
{validation_issues}

请修正上述问题，输出优化后的功能意图。注意：
1. 保持原始功能意图不变
2. 仅针对指出的问题进行最小化修改
3. 确保修改后的意图内部一致

输出格式与原始意图相同。
```

---

*文档版本: v1.0*
*创建日期: 2026-04-22*
*基于: PropGen (arXiv:2604.13463)*
