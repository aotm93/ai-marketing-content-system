# Content Intelligence Layer - 完整实施计划

## 📋 需求确认

### 用户选择
- ✅ **1. 完整的 Content Intelligence Layer**  
- ✅ **2. 完整的研究-写作协作流程**
- ✅ **3. 仅在必要时调用 API**

---

## 🏗️ 架构设计

### 核心组件

```
┌─────────────────────────────────────────────────────────────┐
│                    Content Intelligence Layer                │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐ │
│  │  ContentIntelligenceService                           │ │
│  │  ├─ ResearchOrchestrator                              │ │
│  │  ├─ TopicGenerator                                    │ │
│  │  ├─ ValueScorer                                       │ │
│  │  └─ ResearchCache                                     │ │
│  └───────────────────────────────────────────────────────┘ │
│                          │                                  │
│  ┌───────────────────────┼───────────────────────────────┐ │
│  │                       │                                │ │
│  ▼                       ▼                                │ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │ │
│  │  TrendResearch│  │ PainPoint    │  │ Competitive  │   │ │
│  │  Service     │  │  Analysis    │  │  Analysis    │   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘   │ │
│                                                          │ │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Research-Writer Collaboration Pipeline             │ │
│  │  ├─ Outline Generator                               │ │
│  │  ├─ Hook Optimizer                                  │ │
│  │  ├─ Research Assistant                              │ │
│  │  └─ Content Refiner                                 │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 实施模块

### Phase 1: Content Intelligence Service (Task 1-3)

**Task 1: Core Service Structure**
- `src/services/content_intelligence.py`
- `src/models/research_models.py`
- 研究驱动的 topic 生成器
- 商业价值评分系统

**Task 2: Research Orchestrator**
- 趋势研究服务 (TrendResearchService)
- 痛点分析服务 (PainPointAnalyzer)
- 竞争分析服务 (CompetitiveAnalyzer)
- API 调用控制 (仅在必要时)

**Task 3: Research Cache System**
- Redis/内存缓存
- 缓存策略设计
- 缓存失效机制

### Phase 2: Research-Writer Pipeline (Task 4-6)

**Task 4: Content Outline Generator**
- 基于研究的大纲生成
- Content-Research-Writer skill 集成
- 角度差异化分析

**Task 5: Hook & Title Optimizer**
- 标题吸引力评分
- 多种 hook 类型生成 (数据/故事/问题)
- A/B 测试准备

**Task 6: Research Assistant**
- 实时研究补充
- 引用管理
- 数据验证

### Phase 3: Integration (Task 7-9)

**Task 7: Replace Fallback Layer**
- 修改 `jobs.py` Layer 1.4
- 移除硬编码 keywords
- 接入 ContentIntelligenceService

**Task 8: Content Creator Agent Enhancement**
- 增强 `_create_article()`
- 集成研究上下文
- 改进 prompt 模板

**Task 9: API & Admin Interface**
- 研究缓存管理 API
- 手动触发研究端点
- 研究质量监控

### Phase 4: Testing & Optimization (Task 10)

**Task 10: Tests & Performance**
- 集成测试
- 缓存性能测试
- API 调用频率监控

---

## 🎯 关键特性

### 1. 智能回退机制 (替代 Layer 1.4)

**Before:**
```python
# 硬编码、无价值的回退
fallback_keywords = [
    "how to choose packaging supplier",
    "packaging materials comparison",
]
```

**After:**
```python
# 研究驱动的智能回退
intelligence_service = ContentIntelligenceService()
topics = await intelligence_service.generate_research_based_topics(
    industry=website_profile.business_type,
    audience=website_profile.target_audience,
    pain_points=website_profile.customer_pain_points
)
# 返回高商业价值的独特角度
```

### 2. 研究驱动的工作流

```python
class ContentIntelligenceService:
    async def generate_high_value_topics(self, context: ResearchContext) -> List[ContentTopic]:
        """
        研究驱动的高价值主题生成
        """
        # 1. 检查缓存
        cached = await self.cache.get(context.cache_key)
        if cached:
            return cached
        
        # 2. 并行研究 (仅在必要时调用 API)
        research_tasks = [
            self._research_trends(context),
            self._analyze_pain_points(context),
            self._identify_content_gaps(context)
        ]
        results = await asyncio.gather(*research_tasks)
        
        # 3. 生成独特角度
        topics = self._generate_unique_angles(results)
        
        # 4. 评分和排序
        scored_topics = self._score_topics(topics)
        
        # 5. 缓存结果
        await self.cache.set(context.cache_key, scored_topics, ttl=86400)
        
        return scored_topics
```

### 3. 商业价值评分系统

评分维度 (总分 100):
- **商业意图强度** (30%): 是否导向购买决策
- **搜索趋势** (25%): 趋势上升/下降
- **竞争难度** (20%): 是否可排名
- **内容差异化** (15%): 是否独特角度
- **品牌价值** (10%): 是否符合品牌定位

### 4. 研究-写作协作流程

```python
class ResearchWriterPipeline:
    """
    Content-Research-Writer skill 集成
    """
    
    async def create_research_based_content(self, topic: ContentTopic) -> Article:
        # 1. 生成大纲 (带研究支持)
        outline = await self._generate_outline_with_research(topic)
        
        # 2. 优化 Hook
        hook_variants = await self._generate_hook_variants(topic)
        best_hook = self._select_best_hook(hook_variants)
        
        # 3. 逐段写作 (带实时研究)
        sections = []
        for section_outline in outline.sections:
            research = await self._research_section(section_outline)
            content = await self._write_section(section_outline, research)
            sections.append(content)
        
        # 4. 整体润色
        article = await self._refine_article(sections)
        
        return article
```

---

## 📊 数据模型

### ContentTopic (研究驱动的主题)
```python
class ContentTopic(BaseModel):
    title: str  # 优化后的标题
    angle: str  # 独特角度
    hook_type: HookType  # hook 类型
    business_intent: float  # 商业意图评分 (0-1)
    trend_score: float  # 趋势评分
    research_sources: List[ResearchSource]  # 研究来源
    outline: ContentOutline  # 生成的大纲
    value_score: float  # 综合价值评分
```

### ResearchResult (研究结果)
```python
class ResearchResult(BaseModel):
    trend_data: Optional[TrendData]
    pain_points: List[PainPoint]
    content_gaps: List[ContentGap]
    competitor_insights: List[CompetitorInsight]
    timestamp: datetime
    cache_ttl: int
```

---

## 🔧 技术实现细节

### API 调用控制策略

```python
class APICallController:
    """
    仅在必要时调用外部 API
    """
    
    def __init__(self):
        self.daily_call_limit = 100
        self.call_count = 0
        self.cache_hit_rate = 0.0
    
    async def get_trend_data(self, keyword: str) -> Optional[TrendData]:
        # 1. 检查缓存
        cached = await self._check_cache(f"trend:{keyword}")
        if cached:
            return cached
        
        # 2. 检查调用限额
        if self.call_count >= self.daily_call_limit:
            logger.warning("API call limit reached, using fallback")
            return await self._generate_estimate(keyword)
        
        # 3. 调用 API
        data = await self._call_trend_api(keyword)
        self.call_count += 1
        
        # 4. 缓存结果
        await self._cache_result(f"trend:{keyword}", data)
        
        return data
```

### 缓存策略

```python
class ResearchCache:
    """
    多级缓存策略
    """
    
    # L1: 内存缓存 (1小时)
    # L2: Redis 缓存 (24小时)
    # L3: 数据库缓存 (7天)
    
    async def get(self, key: str) -> Optional[Any]:
        # 尝试 L1
        if key in self.memory_cache:
            return self.memory_cache[key]
        
        # 尝试 L2
        data = await self.redis.get(key)
        if data:
            self.memory_cache[key] = data
            return data
        
        # 尝试 L3
        data = await self.db.query(ResearchCacheModel).filter(...).first()
        if data:
            await self.redis.set(key, data, ttl=3600)
            return data
        
        return None
```

---

## 📈 成功指标

### 内容质量提升
- [ ] 平均商业意图评分 > 0.7
- [ ] 标题独特性 > 80%
- [ ] 用户参与度提升 (停留时间 +30%)

### 系统性能
- [ ] API 调用减少 70% (通过缓存)
- [ ] 研究响应时间 < 2秒 (缓存命中)
- [ ] 内容生成成功率 > 95%

### 业务价值
- [ ] 转化率提升 (目标 +20%)
- [ ] 搜索排名改善 (目标 top 10 增加 50%)
- [ ] 内容生产成本降低 (目标 -40%)

---

## 🚀 实施路线图

### Week 1: 基础设施
- Day 1-2: Task 1 (Core Service)
- Day 3-4: Task 2 (Research Orchestrator)
- Day 5: Task 3 (Cache System)

### Week 2: 研究-写作流程
- Day 1-2: Task 4 (Outline Generator)
- Day 3-4: Task 5 (Hook Optimizer)
- Day 5: Task 6 (Research Assistant)

### Week 3: 集成与测试
- Day 1-2: Task 7 (Replace Fallback)
- Day 3-4: Task 8 (Agent Enhancement)
- Day 5: Task 9 (API Interface)

### Week 4: 优化与上线
- Day 1-3: Task 10 (Testing)
- Day 4-5: 性能优化与文档

---

## 💰 成本估算

### API 成本 (DataForSEO)
- 关键词研究: ~$0.001/请求
- 预估月调用: 1000次
- 预估月成本: $1-3

### 开发时间
- 总任务数: 10
- 预估工时: 80小时
- 并行优化: 可缩短至 40小时

---

## ✅ 下一步行动

**请确认:**
1. 这个架构设计是否符合你的预期？
2. 是否需要调整优先级或范围？
3. 我可以开始生成详细的工作计划 (Task 1-10) 吗？

**一旦确认，我将:**
- 创建 `.sisyphus/plans/content-intelligence-layer.md`
- 包含所有 10 个任务的详细实现计划
- 每个任务包含代码示例和验收标准
