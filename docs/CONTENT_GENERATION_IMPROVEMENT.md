# 内容生成深度优化方案

## 问题分析

**当前问题：**
1. 标题通用化：`"Types of X Explained"`, `"Best X Review"`
2. 内容空洞：缺乏技术深度，都是常识性内容
3. 缺乏真实研究：没有基于用户搜索意图的深度内容

**已完成：**
✅ `SearchIntentAnalyzer` - 基于真实搜索意图生成标题
✅ 集成到 `HookOptimizer` - PROBLEM/HOW_TO 类型使用意图分析

## 优化方案

### 阶段 1: 内容生成器增强（最小化实现）

**核心思路：** 将 `content-research-writer` skill 的研究能力集成到内容生成流程

```python
# src/services/content/professional_writer.py
class ProfessionalContentWriter:
    """基于意图分析和专业研究的内容生成器"""

    def __init__(self):
        self.intent_analyzer = SearchIntentAnalyzer()
        self.research_assistant = ResearchAssistant()

    def generate_section_content(
        self,
        section: OutlineSection,
        intent_signal: IntentSignal
    ) -> str:
        """根据意图生成专业内容"""

        # 1. 基于意图获取研究数据
        research = self.research_assistant.research_section(section)

        # 2. 构建专业提示词（避免通用模板）
        prompt = self._build_professional_prompt(
            section,
            intent_signal,
            research
        )

        # 3. 生成内容
        return self._generate_with_depth(prompt)
```

### 阶段 2: 提示词优化

**关键改进：**
- ❌ 删除：`"Write a comprehensive guide"`
- ✅ 添加：基于意图的具体指令

```python
def _build_professional_prompt(self, section, intent, research):
    if intent.intent == UserIntent.PROBLEM_SOLVING:
        return f"""
        写一段关于 {section.title} 的技术分析：

        要求：
        1. 解释根本原因（不要只说"这是个问题"）
        2. 提供具体数据：{research.statistics}
        3. 给出可操作的解决方案
        4. 避免通用建议
        """

    elif intent.intent == UserIntent.SPECIFICATION:
        return f"""
        写一段关于 {section.title} 的技术规格分析：

        要求：
        1. 提供具体技术参数
        2. 对比不同规格的性能差异
        3. 引用行业标准
        4. 避免"什么是X"这类基础解释
        """
```

### 阶段 3: 集成 content-research-writer

**最小化集成：**
