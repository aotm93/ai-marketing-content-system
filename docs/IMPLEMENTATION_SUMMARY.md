# 文章生成深度优化 - 完整实施方案

## 问题总结

**原始问题：**
1. 标题通用：`"Types of Plastic Explained: What You Need to Know"`, `"5 Best HDPE Options (2026 Review)"`
2. 内容空洞：都是常识性内容，没有深度
3. 缺乏真实搜索意图分析

## 已完成的优化（TDD实现，13/13测试通过）

### 1. 标题优化系统 ✅

**新增组件：**
- `SearchIntentAnalyzer` - 分析真实用户搜索意图
- 集成到 `HookOptimizer` - PROBLEM/HOW_TO 类型使用意图分析

**效果对比：**
```
旧: "5 Best HDPE Options (2026 Review)"
新: "Preventing Cracking in Cold Weather in HDPE: Root Causes and Solutions"

旧: "Types of Plastic Explained: What You Need to Know"
新: "HDPE Chemical Resistance: Technical Data and Performance Metrics"
```

### 2. 内容提示词优化系统 ✅

**新增组件：**
- `ProfessionalContentWriter` - 生成专业内容提示词

**效果对比：**
```python
# 旧提示词（通用）
"Write a comprehensive guide about HDPE cracking.
Cover everything readers need to know."

# 新提示词（专业）
"Write technical analysis for: Root Causes of Cold Weather Cracking

Requirements:
- Explain root causes with specific technical details
- Provide data-backed evidence
- Give actionable solutions
- Avoid generic advice like 'be careful'"
```

## 下一步：集成到生产环境

### 方案 A：最小化集成（推荐）

只需修改 `ContentCreatorAgent._build_synchronized_prompt` 一个方法：

```python
from src.services.content.professional_writer import ProfessionalContentWriter
from src.services.content.intent_analyzer import SearchIntentAnalyzer

class ContentCreatorAgent:
    def __init__(self):
        self.professional_writer = ProfessionalContentWriter()
        self.intent_analyzer = SearchIntentAnalyzer()

    def _build_synchronized_prompt(self, ...):
        # 分析意图
        intent_signal = self.intent_analyzer.analyze_intent(keyword)

        # 为每个section生成专业提示词
        for section in outline.get('sections', []):
            section_prompt = self.professional_writer.build_section_prompt(
                section, intent_signal
            )
            # 使用 section_prompt 替换通用模板
```

### 方案 B：完整优化（可选）

如果需要更深度的内容，可以集成 `content-research-writer` skill：
- 在生成内容前调用 skill 进行深度研究
- 获取真实数据、引用、案例研究
- 传递给内容生成 API

## 测试覆盖

- `SearchIntentAnalyzer`: 94% 覆盖率
- `ProfessionalContentWriter`: 100% 覆盖率
- `HookOptimizer` 集成: 100% 通过

## 关键改进点

1. **消除通用模板** - 不再生成 "What You Need to Know", "Review", "Best"
2. **基于真实意图** - 分析用户搜索背后的真实需求
3. **技术深度要求** - 提示词明确要求具体数据、技术参数
4. **避免空洞建议** - 禁止 "be careful", "follow best practices" 等通用建议

## 实施建议

**立即可做：**
1. 在 `ContentCreatorAgent` 中导入 `ProfessionalContentWriter`
2. 修改 `_build_synchronized_prompt` 使用新的提示词生成器
3. 运行现有测试验证兼容性

**后续优化：**
1. 扩展 `SEMANTIC_EXPANSIONS` 字典支持更多行业术语
2. 集成外部 API 获取真实搜索数据
3. 添加内容质量评分系统
