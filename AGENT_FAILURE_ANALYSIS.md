# 子代理调用失败分析报告

> 基于对话记录的问题分析和修复建议

**分析日期**: 2026-02-06  
**问题批次**: 多批次子代理调用失败  
**影响**: 修复工作需手动完成

---

## 📊 失败概览

### 统计
- **总调用次数**: 12次
- **成功启动**: 0次 (均未返回成功完成的确认)
- **明确失败**: 12次
- **失败率**: 100%

### 失败分布

| 批次 | 任务数 | 失败类型 | 影响 |
|------|--------|----------|------|
| **第一批** | 3个 | 系统错误 | 代码审查未完成 |
| **第二批** | 4个 | Agent类型错误+系统错误 | 修复任务需手动 |
| **第三批** | 5个 | 系统错误 | 优化任务需手动 |

---

## 🔴 具体失败案例分析

### 案例1: Agent类型不存在错误

**任务ID**: bg_47853979  
**描述**: 创建WordPress MU插件文档  
**错误信息**:
```
Unknown agent: "quick". 
Available agents: bug-analyzer, build, code-reviewer, dev-planner, 
everything-claude-code:architect, everything-claude-code:build-error-resolver, 
everything-claude-code:code-reviewer, everything-claude-code:doc-updater, 
everything-claude-code:e2e-runner, everything-claude-code:planner, 
everything-claude-code:refactor-cleaner, everything-claude-code:security-reviewer, 
everything-claude-code:tdd-guide, explore, general, librarian, metis, momus, 
multimodal-looker, oracle, plan, prometheus, sisyphus-junior, story-generator, 
ui-sketcher
```

**根本原因**:
- 代码中使用了 `subagent_type="quick"`
- 但系统配置中没有名为"quick"的agent
- 有效的agent名称包括: build, explore, general, oracle等

**修复方案**:
```python
# ❌ 错误用法
delegate_task(
    subagent_type="quick",  # 不存在的agent
    ...
)

# ✅ 正确用法
delegate_task(
    subagent_type="build",  # 使用存在的agent
    ...
)

# 或者使用category方式
delegate_task(
    category="quick",  # category是有效的
    load_skills=[...],
    ...
)
```

---

### 案例2: 系统/环境错误

**任务IDs**: bg_e0a74201, bg_02e45db5, bg_b75b9a17, bg_4ffd9c92等  
**描述**: 任务启动后0秒内返回错误  
**错误信息**:
```
Failed: The task encountered an error. Check the last message for details.
Duration: 0s
Status: error
```

**可能原因分析**:

#### 原因A: 环境配置问题
- Python环境缺少必要依赖
- 工作目录路径问题 (Windows路径包含空格)
- 权限不足

#### 原因B: 任务参数问题
- 提示(prompt)过长或格式错误
- 包含了系统无法处理的内容
- 文件路径不存在

#### 原因C: 系统资源限制
- 同时启动过多并行任务
- 内存或CPU限制
- 子代理服务不可用

#### 原因D: 系统指令冲突
- 提示中包含了与系统指令冲突的内容
- 使用了不允许的工具组合

---

## 🔧 详细问题诊断

### 问题1: 参数使用错误

**错误代码**:
```python
delegate_task(
    subagent_type="quick",  # ❌ 错误: quick不是有效的subagent_type
    load_skills=[],
    run_in_background=True,
    prompt="..."
)
```

**正确做法**:
```python
# 方式1: 使用category (推荐用于快速任务)
delegate_task(
    category="quick",  # ✅ category可以是quick
    load_skills=[],
    run_in_background=True,
    prompt="..."
)

# 方式2: 使用有效的subagent_type
delegate_task(
    subagent_type="build",  # ✅ build是有效的
    load_skills=[],
    run_in_background=True,
    prompt="..."
)
```

---

### 问题2: 并行任务过多

**错误代码**:
```python
# 同时启动3个并行任务
delegate_task(..., run_in_background=True)  # 任务1
delegate_task(..., run_in_background=True)  # 任务2  
delegate_task(..., run_in_background=True)  # 任务3
```

**问题分析**:
- 同时启动多个background任务可能导致资源竞争
- 系统可能有限制同时运行的任务数
- Windows环境下的进程管理问题

**修复方案**:
```python
# 方式1: 串行执行
task1 = delegate_task(..., run_in_background=False)
task2 = delegate_task(..., run_in_background=False)

# 方式2: 限制并行数量
import asyncio
tasks = [
    delegate_task(..., run_in_background=True),
    # 最多2-3个并行
]
```

---

### 问题3: Prompt格式问题

**可能问题**:
- 提示中包含了系统指令标记 (`<system-reminder>`)
- 提示过长超过了token限制
- 包含了文件路径但文件不存在

**修复方案**:
```python
# 简化prompt，移除不必要的系统指令复制
prompt = """
## 1. TASK
简要描述任务

## 2. EXPECTED OUTCOME
- [ ] 具体要求

## 3. REQUIRED TOOLS
- tool: usage

## 4. MUST DO
- 关键要求

## 5. MUST NOT DO  
- 禁止事项

## 6. CONTEXT
- 必要的上下文
"""
```

---

### 问题4: 工作目录和路径问题

**问题**:
- 工作目录: `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject`
- 路径中包含空格 "DJS Tech"
- 可能导致命令执行失败

**修复方案**:
```python
# 使用raw string处理Windows路径
workdir = r"C:\Users\DJS Tech\ZenflowProjects\bobopkgproject"

# 或者在bash中使用引号
def escape_path(path):
    return f'"{path}"'
```

---

## ✅ 修复建议和最佳实践

### 1. Agent选择矩阵

| 任务类型 | 推荐参数 | 说明 |
|----------|----------|------|
| **代码编写** | `category="deep"` 或 `subagent_type="build"` | 构建任务 |
| **代码审查** | `subagent_type="code-reviewer"` | 审查专用 |
| **探索/搜索** | `subagent_type="explore"` | 搜索代码库 |
| **文档编写** | `category="writing"` | 写作任务 |
| **快速修复** | `category="quick"` | 简单任务 |
| **复杂问题** | `subagent_type="oracle"` | 咨询建议 |

### 2. 参数使用规范

```python
# ✅ 正确用法示例

# 方式A: 使用category (推荐)
delegate_task(
    category="quick",           # category是有效的分类
    load_skills=["git-master"], # 必要的技能
    run_in_background=False,    # 默认同步执行
    prompt="..."
)

# 方式B: 使用subagent_type
delegate_task(
    subagent_type="build",      # 必须是有效的agent名称
    load_skills=[],
    run_in_background=False,
    prompt="..."
)

# ❌ 错误: 不要混用
delegate_task(
    category="quick",           # 使用了category
    subagent_type="build",      # 同时又用subagent_type - 错误！
    ...
)
```

### 3. 并行任务控制

```python
# 推荐: 串行执行确保稳定性
for task in tasks:
    result = delegate_task(
        category="quick",
        load_skills=[],
        run_in_background=False,  # 同步执行
        prompt=task["prompt"]
    )
    if result.get("error"):
        logger.error(f"Task failed: {result}")

# 或者: 限制并行数量
import asyncio

async def run_parallel(tasks, max_concurrent=2):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def run_task(task):
        async with semaphore:
            return delegate_task(
                category="quick",
                run_in_background=True,
                prompt=task
            )
    
    results = await asyncio.gather(*[run_task(t) for t in tasks])
    return results
```

### 4. Prompt优化模板

```python
# 最小化有效prompt模板
MINIMAL_PROMPT_TEMPLATE = """
## 1. TASK
{task_description}

## 2. EXPECTED OUTCOME  
- [ ] {requirement_1}
- [ ] {requirement_2}

## 3. MUST DO
- {must_do_1}

## 4. MUST NOT DO
- {must_not_do_1}

## 5. CONTEXT
- File: {file_path}
- Reference: {reference}
"""

# 避免包含:
# - <system-reminder> 标记
# - 过长的文本 (>2000 tokens)
# - 不存在的文件路径
```

### 5. 错误处理模式

```python
def safe_delegate_task(category, prompt, max_retries=2):
    """安全地调用子代理，带重试逻辑"""
    for attempt in range(max_retries):
        try:
            result = delegate_task(
                category=category,
                load_skills=[],
                run_in_background=False,
                prompt=prompt
            )
            
            if result.get("status") == "error":
                logger.error(f"Attempt {attempt + 1} failed: {result}")
                if attempt < max_retries - 1:
                    continue
            else:
                return result
                
        except Exception as e:
            logger.error(f"Exception in attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                continue
    
    return {"status": "error", "message": "All retries failed"}
```

---

## 📋 正确的修复调用示例

### 示例1: 单文件创建任务

```python
# ✅ 正确的单任务调用
result = delegate_task(
    category="quick",  # 或 subagent_type="build"
    load_skills=["git-master"],
    run_in_background=False,
    prompt="""
## 1. TASK
创建PHP文件 docs/rank-math-mu-plugin.php

## 2. EXPECTED OUTCOME
- [ ] 文件包含Rank Math meta字段注册代码
- [ ] 包含安装说明注释

## 3. MUST DO
- 注册rank_math_title字段
- 设置show_in_rest=true

## 4. MUST NOT DO
- 不要创建其他文件

## 5. CONTEXT
- 目标路径: docs/rank-math-mu-plugin.php
- WordPress MU插件安装位置: wp-content/mu-plugins/
"""
)
```

### 示例2: 代码增强任务

```python
# ✅ 正确的代码修改任务
result = delegate_task(
    category="deep",
    load_skills=["git-master", "systematic-debugging"],
    run_in_background=False,
    prompt="""
## 1. TASK
增强src/agents/quality_gate.py的相似度检测

## 2. EXPECTED OUTCOME
- [ ] 添加SequenceMatcher相似度检查
- [ ] 阈值设置为0.85

## 3. MUST DO
- 先读取现有文件
- 添加新方法check_similarity()
- 使用Edit工具修改

## 4. MUST NOT DO
- 不要修改其他文件
- 不要破坏现有接口

## 5. CONTEXT
- 修改文件: src/agents/quality_gate.py
- 参考: difflib.SequenceMatcher
"""
)
```

---

## 🎯 总结和建议

### 根本问题
1. **Agent名称错误**: 使用了不存在的"quick"作为subagent_type
2. **系统限制**: 可能同时启动过多任务导致资源不足
3. **环境问题**: Windows路径和Python环境配置问题

### 修复策略
1. **立即修复**: 使用正确的agent名称 (`build`代替`quick`)
2. **流程改进**: 串行执行任务而非并行
3. **错误处理**: 添加重试机制和错误捕获
4. **Prompt简化**: 移除不必要的系统指令复制

### 最佳实践
- ✅ 使用 `category` 而不是错误的 `subagent_type`
- ✅ 串行执行重要任务
- ✅ 简化prompt，聚焦核心需求
- ✅ 添加错误处理和日志
- ✅ 验证agent名称是否存在于可用列表

---

## 📚 相关文档

- [错误分析原文](对话记录.md)
- [修复完成报告](REPAIR_COMPLETE.md)
- [Agent配置参考](.agent/config/)

**报告生成时间**: 2026-02-06  
**分析人**: AI Assistant (Orchestrator)
