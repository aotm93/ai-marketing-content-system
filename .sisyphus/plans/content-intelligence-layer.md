# Content Intelligence Layer Implementation Plan

## Overview
Complete implementation of research-driven content generation system to replace the fallback layer with high-value, research-based content topics.

**Total Tasks**: 10
**Estimated Time**: 4 weeks
**Parallel Execution**: Possible for independent tasks

---

## Wave 1: Infrastructure (Week 1)

### Task 1: Core Service Structure
**Status**: Pending
**Priority**: High
**Estimated**: 8 hours

**Files to Create**:
- `src/services/content_intelligence.py` - Main service
- `src/models/content_intelligence.py` - Data models
- `src/services/research/__init__.py` - Research module

**Implementation**:
```python
class ContentIntelligenceService:
    def __init__(self, db: Session, cache: ResearchCache):
        self.db = db
        self.cache = cache
        self.orchestrator = ResearchOrchestrator()
        self.topic_generator = TopicGenerator()
        self.value_scorer = ValueScorer()
    
    async def generate_high_value_topics(
        self, 
        industry: str,
        audience: str,
        pain_points: List[str]
    ) -> List[ContentTopic]:
        # Check cache first
        cache_key = f"research:{industry}:{hash(str(pain_points))}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        # Conduct research
        research = await self.orchestrator.conduct_research(
            industry=industry,
            audience=audience,
            pain_points=pain_points
        )
        
        # Generate topics
        topics = self.topic_generator.generate(research)
        
        # Score and sort
        scored_topics = [
            (topic, self.value_scorer.score(topic)) 
            for topic in topics
        ]
        scored_topics.sort(key=lambda x: x[1], reverse=True)
        
        # Cache results
        await self.cache.set(cache_key, scored_topics, ttl=86400)
        
        return scored_topics
```

**Acceptance Criteria**:
- [ ] Service initializes without errors
- [ ] Can generate topics with mock research data
- [ ] Caching mechanism works
- [ ] Value scoring algorithm implemented

---

### Task 2: Research Orchestrator
**Status**: Pending
**Priority**: High
**Estimated**: 12 hours

**Files to Create**:
- `src/services/research/trend_research.py`
- `src/services/research/pain_point_analyzer.py`
- `src/services/research/competitive_analyzer.py`
- `src/services/research/orchestrator.py`

**Implementation**:
```python
class ResearchOrchestrator:
    async def conduct_research(self, context: ResearchContext) -> ResearchResult:
        # Parallel research with API call control
        tasks = []
        
        # Only call APIs if cache miss and within limits
        if await self._should_research_trends(context):
            tasks.append(self._research_trends(context))
        else:
            tasks.append(self._get_cached_trends(context))
        
        if await self._should_analyze_pain_points(context):
            tasks.append(self._analyze_pain_points(context))
        else:
            tasks.append(self._get_cached_pain_points(context))
        
        if await self._should_analyze_competitors(context):
            tasks.append(self._analyze_competitors(context))
        else:
            tasks.append(self._get_cached_competitors(context))
        
        results = await asyncio.gather(*tasks)
        
        return ResearchResult(
            trend_data=results[0],
            pain_points=results[1],
            competitor_insights=results[2],
            timestamp=datetime.now()
        )
```

**Acceptance Criteria**:
- [ ] Parallel research execution works
- [ ] API call limits enforced
- [ ] Fallback to cached data when limits reached
- [ ] Research results combined correctly

---

### Task 3: Research Cache System
**Status**: Pending
**Priority**: High
**Estimated**: 8 hours

**Files to Create**:
- `src/services/research/cache.py`
- `src/models/research_cache.py`

**Implementation**:
```python
class ResearchCache:
    """Three-tier cache: Memory -> Redis -> Database"""
    
    def __init__(self):
        self.memory_cache = {}
        self.memory_ttl = 3600  # 1 hour
        self.redis_ttl = 86400  # 24 hours
        self.db_ttl = 604800    # 7 days
    
    async def get(self, key: str) -> Optional[Any]:
        # L1: Memory
        if key in self.memory_cache:
            data, expiry = self.memory_cache[key]
            if datetime.now() < expiry:
                return data
            del self.memory_cache[key]
        
        # L2: Redis
        data = await redis.get(key)
        if data:
            self.memory_cache[key] = (data, datetime.now() + timedelta(seconds=self.memory_ttl))
            return json.loads(data)
        
        # L3: Database
        db_entry = self.db.query(ResearchCacheEntry).filter_by(key=key).first()
        if db_entry and db_entry.expiry > datetime.now():
            await redis.set(key, db_entry.data, ex=self.redis_ttl)
            return json.loads(db_entry.data)
        
        return None
```

**Acceptance Criteria**:
- [ ] Three-tier cache works correctly
- [ ] Cache hit rate > 80%
- [ ] Expired entries cleaned up
- [ ] Performance: < 10ms for memory hits

---

## Wave 2: Research-Writer Pipeline (Week 2)

### Task 4: Content Outline Generator
**Status**: Pending
**Priority**: High
**Estimated**: 10 hours

**Files to Create**:
- `src/services/content/outline_generator.py`

**Implementation**:
```python
class OutlineGenerator:
    async def generate_outline(
        self, 
        topic: ContentTopic,
        research: ResearchResult
    ) -> ContentOutline:
        """Generate research-supported outline"""
        
        # Generate sections based on research
        sections = []
        
        # Hook section
        hook = self._generate_hook(topic, research)
        
        # Problem/Pain Point section
        if research.pain_points:
            sections.append(OutlineSection(
                title=f"The {research.pain_points[0].category} Challenge",
                content_type="problem_statement",
                research_support=research.pain_points[0].evidence
            ))
        
        # Solution sections
        for i, solution in enumerate(topic.suggested_solutions, 1):
            sections.append(OutlineSection(
                title=f"Solution {i}: {solution.title}",
                content_type="solution",
                key_points=solution.steps,
                research_support=solution.data_sources
            ))
        
        # Comparison section (if competitive research available)
        if research.competitor_insights:
            sections.append(OutlineSection(
                title="Market Comparison",
                content_type="comparison",
                research_support=research.competitor_insights
            ))
        
        return ContentOutline(
            title=topic.title,
            hook=hook,
            sections=sections,
            conclusion_type="cta" if topic.business_intent > 0.7 else "summary"
        )
```

**Acceptance Criteria**:
- [ ] Outlines include research citations
- [ ] Section structure logical
- [ ] Hook types varied (data/story/question)
- [ ] Business intent reflected in structure

---

### Task 5: Hook & Title Optimizer
**Status**: Pending
**Priority**: High
**Estimated**: 8 hours

**Files to Create**:
- `src/services/content/hook_optimizer.py`

**Implementation**:
```python
class HookOptimizer:
    async def generate_optimized_titles(
        self, 
        topic: ContentTopic,
        count: int = 5
    ) -> List[OptimizedTitle]:
        """Generate multiple title variants with scoring"""
        
        variants = []
        
        # Type 1: Data-driven
        if topic.research_data and topic.research_data.statistics:
            stat = topic.research_data.statistics[0]
            variants.append(OptimizedTitle(
                title=f"{stat.value}% of {stat.subject} {stat.action}: Here's What We Learned",
                hook_type="data",
                expected_ctr=self._estimate_ctr("data", stat.impact_score)
            ))
        
        # Type 2: Problem-focused
        if topic.pain_points:
            pain = topic.pain_points[0]
            variants.append(OptimizedTitle(
                title=f"The Hidden Cost of {pain.problem}: A {topic.industry} Analysis",
                hook_type="problem",
                expected_ctr=self._estimate_ctr("problem", pain.severity)
            ))
        
        # Type 3: How-to with specificity
        variants.append(OptimizedTitle(
            title=f"How to {topic.solution} in {topic.timeframe}: A Step-by-Step Guide",
            hook_type="how_to",
            expected_ctr=self._estimate_ctr("how_to", topic.complexity)
        ))
        
        # Type 4: Question
        variants.append(OptimizedTitle(
            title=f"Is {topic.common_misconception} Actually Hurting Your {topic.business_metric}?",
            hook_type="question",
            expected_ctr=self._estimate_ctr("question", topic.controversy_score)
        ))
        
        # Type 5: Story/Personal
        variants.append(OptimizedTitle(
            title=f"How {topic.example_company} {topic.achievement} in Just {topic.timeframe}",
            hook_type="story",
            expected_ctr=self._estimate_ctr("story", topic.uniqueness)
        ))
        
        # Sort by expected CTR
        variants.sort(key=lambda x: x.expected_ctr, reverse=True)
        
        return variants[:count]
```

**Acceptance Criteria**:
- [ ] Generates 5 different hook types
- [ ] CTR estimation algorithm works
- [ ] Titles are specific and unique
- [ ] A/B test ready variants

---

### Task 6: Research Assistant Integration
**Status**: Pending
**Priority**: Medium
**Estimated**: 10 hours

**Files to Create**:
- `src/services/content/research_assistant.py`

**Implementation**:
```python
class ResearchAssistant:
    """Real-time research support during content writing"""
    
    async def research_section(
        self, 
        section_outline: OutlineSection,
        existing_content: str = ""
    ) -> SectionResearch:
        """Research support for specific section"""
        
        research = SectionResearch()
        
        # Find supporting data
        if section_outline.content_type == "solution":
            research.data_points = await self._find_supporting_data(
                section_outline.title
            )
        
        # Find expert quotes
        if section_outline.content_type in ["problem_statement", "comparison"]:
            research.quotes = await self._find_expert_quotes(
                section_outline.key_points
            )
        
        # Find examples/case studies
        if section_outline.content_type in ["solution", "best_practices"]:
            research.examples = await self._find_case_studies(
                section_outline.title
            )
        
        # Verify claims
        if existing_content:
            research.verifications = await self._verify_claims(existing_content)
        
        return research
    
    async def generate_citations(
        self, 
        research_data: SectionResearch,
        format: CitationFormat = CitationFormat.APA
    ) -> List[Citation]:
        """Format citations according to style guide"""
        citations = []
        
        for source in research_data.sources:
            if format == CitationFormat.APA:
                citation = f"{source.author} ({source.year}). {source.title}. {source.publication}."
            elif format == CitationFormat.MLA:
                citation = f"{source.author}. \"{source.title}.\" {source.publication}, {source.year}."
            
            citations.append(Citation(
                text=citation,
                url=source.url,
                type=source.type
            ))
        
        return citations
```

**Acceptance Criteria**:
- [ ] Section-level research works
- [ ] Citations formatted correctly
- [ ] Claim verification implemented
- [ ] Research context preserved

---

## Wave 3: Integration (Week 3)

### Task 7: Replace Fallback Layer
**Status**: Pending
**Priority**: Critical
**Estimated**: 8 hours

**Files to Modify**:
- `src/scheduler/jobs.py` - Replace Layer 1.4

**Implementation**:
```python
# IN jobs.py, replace the fallback section (lines 274-314)

# OLD CODE (to be removed):
# fallback_keywords = ["how to choose packaging supplier", ...]

# NEW CODE:
if not target_keyword:
    logger.info("All keyword sources exhausted, using Content Intelligence")
    
    try:
        from src.services.content_intelligence import ContentIntelligenceService
        
        intelligence_service = ContentIntelligenceService(db)
        
        # Get website profile for context
        website_profile = await get_cached_website_profile()
        
        context = ResearchContext(
            industry=website_profile.business_type if website_profile else "general",
            audience=website_profile.target_audience if website_profile else "b2b_buyers",
            pain_points=website_profile.customer_pain_points if website_profile else [],
            product_categories=website_profile.product_categories if website_profile else []
        )
        
        # Generate research-based topics
        topics = await intelligence_service.generate_high_value_topics(
            industry=context.industry,
            audience=context.audience,
            pain_points=context.pain_points
        )
        
        if topics:
            # Select highest value unused topic
            for topic in topics:
                if topic.title.lower() not in used_keyword_set:
                    target_keyword = topic.title
                    target_context = {
                        "source": "ContentIntelligence (Research-Based)",
                        "metric": f"Value Score: {topic.value_score:.2f}, Business Intent: {topic.business_intent:.2f}",
                        "research_sources": [s.name for s in topic.research_sources],
                        "outline": topic.outline
                    }
                    logger.info(f"Selected research-based topic: {target_keyword} (Value: {topic.value_score:.2f})")
                    break
        
        if not target_keyword:
            logger.error("Content Intelligence failed to generate usable topic")
            
    except Exception as e:
        logger.error(f"Content Intelligence failed: {e}")
        # Absolute fallback - but now much better quality
        target_keyword = await self._generate_emergency_topic(website_profile)
        target_context = {"source": "Emergency Fallback"}
```

**Acceptance Criteria**:
- [ ] Fallback layer completely removed
- [ ] ContentIntelligenceService integrated
- [ ] Research context passed to content generation
- [ ] Graceful degradation if service fails

---

### Task 8: Enhance Content Creator Agent
**Status**: Pending
**Priority**: High
**Estimated**: 10 hours

**Files to Modify**:
- `src/agents/content_creator.py`

**Implementation**:
```python
class ContentCreatorAgent(BaseAgent):
    async def _create_article(self, task: Dict[str, Any]) -> Dict[str, Any]:
        keyword = task.get("keyword", "")
        research_context = task.get("research_context", {})  # NEW
        outline = task.get("outline", {})  # NEW
        
        # Enhanced prompt with research context
        prompt = f"""
        Write a comprehensive 2000+ word article optimized for: {keyword}
        
        **Research Context** (Use this data to add authority):
        {self._format_research_context(research_context)}
        
        **Article Outline** (Follow this structure):
        {self._format_outline(outline)}
        
        **Writing Requirements**:
        1. Engaging headline with keyword and hook
        2. Clear H2/H3 structure matching outline
        3. Natural keyword integration (1-2% density)
        4. **Include specific data points and statistics from research context**
        5. **Reference real examples and case studies**
        6. **Add expert quotes where relevant**
        7. Actionable insights for wholesale buyers
        8. Internal links to products
        9. Meta description (150-160 chars)
        10. FAQ section with schema markup
        
        **Content Quality Standards**:
        - Avoid generic advice - be specific and actionable
        - Use concrete numbers and percentages from research
        - Include "Pro Tips" callout boxes
        - End each section with a takeaway
        
        Write professional, valuable content that demonstrates expertise.
        """
        
        content = await self.generate_text(prompt, max_tokens=4000)
        
        # NEW: Add citations if research sources available
        if research_context.get("sources"):
            content += self._generate_references_section(research_context["sources"])
        
        return {"status": "success", "content": content, "research_based": bool(research_context)}
```

**Acceptance Criteria**:
- [ ] Enhanced prompt uses research context
- [ ] Outline structure followed
- [ ] Citations added automatically
- [ ] Content quality improved (measured by scoring)

---

### Task 9: API & Admin Interface
**Status**: Pending
**Priority**: Medium
**Estimated**: 8 hours

**Files to Create**:
- `src/api/content_intelligence.py`

**Implementation**:
```python
router = APIRouter(prefix="/api/v1/content-intelligence", tags=["content-intelligence"])

@router.post("/research")
async def trigger_research(
    request: ResearchRequest,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Manually trigger research for a topic"""
    service = ContentIntelligenceService(db)
    topics = await service.generate_high_value_topics(
        industry=request.industry,
        audience=request.audience,
        pain_points=request.pain_points
    )
    return {"topics": [t.dict() for t in topics]}

@router.get("/cache/stats")
async def get_cache_stats(
    current_admin: dict = Depends(get_current_admin)
):
    """Get research cache statistics"""
    cache = ResearchCache()
    return {
        "memory_hit_rate": await cache.get_memory_hit_rate(),
        "redis_hit_rate": await cache.get_redis_hit_rate(),
        "db_hit_rate": await cache.get_db_hit_rate(),
        "api_calls_saved": await cache.get_api_calls_saved(),
        "total_topics_generated": await cache.get_total_topics()
    }

@router.get("/topics/queue")
async def get_pending_topics(
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """View topics waiting to be used"""
    # Get high-value topics that haven't been used
    topics = db.query(ContentTopic).filter(
        ContentTopic.used == False,
        ContentTopic.value_score > 0.7
    ).order_by(ContentTopic.value_score.desc()).all()
    
    return {"topics": [t.dict() for t in topics]}
```

**Acceptance Criteria**:
- [ ] Research trigger endpoint works
- [ ] Cache stats accessible
- [ ] Topic queue visible in admin
- [ ] All endpoints protected by admin auth

---

## Wave 4: Testing & Optimization (Week 4)

### Task 10: Integration Tests & Performance
**Status**: Pending
**Priority**: High
**Estimated**: 12 hours

**Files to Create**:
- `tests/integration/test_content_intelligence.py`
- `tests/unit/test_value_scorer.py`
- `tests/unit/test_research_cache.py`

**Test Coverage**:
```python
class TestContentIntelligenceService:
    async def test_generate_topics_with_cache_hit(self):
        """Test cache hit scenario"""
        
    async def test_generate_topics_with_cache_miss(self):
        """Test cache miss and API calls"""
        
    async def test_value_scoring_accuracy(self):
        """Test value scoring algorithm"""
        
    async def test_api_call_limit_enforcement(self):
        """Test API limits are respected"""
        
    async def test_fallback_to_cached_data(self):
        """Test graceful degradation"""

class TestResearchCache:
    def test_three_tier_cache_hierarchy(self):
        """Test L1->L2->L3 cache flow"""
        
    def test_cache_expiration(self):
        """Test TTL enforcement"""
        
    def test_cache_hit_rates(self):
        """Test hit rate metrics"""

class TestHookOptimizer:
    def test_hook_type_variety(self):
        """Test all 5 hook types generated"""
        
    def test_ctr_estimation(self):
        """Test CTR prediction accuracy"""
```

**Performance Tests**:
```python
@pytest.mark.performance
async def test_topic_generation_performance():
    """Performance requirements:
    - Cache hit: < 10ms
    - Cache miss: < 2s
    - 95th percentile: < 3s
    """
```

**Acceptance Criteria**:
- [ ] 90%+ test coverage
- [ ] Cache hit rate > 80%
- [ ] All performance requirements met
- [ ] Integration tests pass
- [ ] Load testing completed

---

## Success Metrics

### Content Quality
- [ ] Average business intent score > 0.7
- [ ] Title uniqueness > 80%
- [ ] Research citations in > 90% of articles

### System Performance
- [ ] API call reduction: 70% (via caching)
- [ ] Cache hit rate: > 80%
- [ ] Topic generation time: < 2s (cached)

### Business Impact
- [ ] Content engagement: +30%
- [ ] Search rankings: +20% improvement
- [ ] Content production cost: -40%

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| API costs exceed budget | Strict call limits + caching |
| Research quality poor | Multiple sources + verification |
| Cache misses too high | Pre-populate cache |
| Content still generic | Strict scoring thresholds |
| Integration breaks existing | Feature flags + gradual rollout |

---

## Dependencies

- ✅ Wave 1 must complete before Wave 2
- ✅ Task 7 depends on Tasks 1-6
- ✅ Task 8 depends on Task 7
- ✅ Task 10 depends on all previous tasks

---

## Rollout Strategy

1. **Phase 1 (Week 1)**: Deploy Tasks 1-3 (Infrastructure)
2. **Phase 2 (Week 2)**: Deploy Tasks 4-6 (Research-Writer)
3. **Phase 3 (Week 3)**: Deploy Tasks 7-9 (Integration) with feature flag
4. **Phase 4 (Week 4)**: Enable for 10% traffic, monitor, then full rollout

---

Ready to start implementation!
