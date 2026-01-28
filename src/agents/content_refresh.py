"""
Content Refresh Agent
Implements P1-7: ContentRefreshAgent

Refreshes existing content to improve rankings:
- Updates outdated information
- Adds new sections (FAQ, tables)
- Improves internal linking
- Enhances SEO elements
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import re

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class RefreshPatch:
    """Content refresh patch"""
    patch_id: str
    patch_type: str  # add_section, update_section, add_faq, add_table, add_links
    location: str  # where to apply (beginning, end, after_h2, etc.)
    content: str
    reason: str
    priority: str  # low, medium, high
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "patch_id": self.patch_id,
            "type": self.patch_type,
            "location": self.location,
            "content": self.content,
            "reason": self.reason,
            "priority": self.priority
        }


@dataclass
class RefreshPlan:
    """Complete refresh plan for a page"""
    plan_id: str
    page_url: str
    post_id: Optional[int]
    current_word_count: int
    target_word_count: int
    patches: List[RefreshPatch]
    seo_updates: Dict[str, Any]
    estimated_improvement: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "page_url": self.page_url,
            "post_id": self.post_id,
            "current_word_count": self.current_word_count,
            "target_word_count": self.target_word_count,
            "patches": [p.to_dict() for p in self.patches],
            "seo_updates": self.seo_updates,
            "estimated_improvement": self.estimated_improvement,
            "patch_count": len(self.patches)
        }


class ContentRefreshAgent(BaseAgent):
    """
    Content Refresh Agent
    
    Analyzes existing content and generates refresh patches to:
    - Improve rankings for declining pages
    - Update outdated information
    - Add missing SEO elements
    - Strengthen internal linking
    """
    
    # Content elements to check
    REQUIRED_ELEMENTS = {
        "faq": r'<h[2-3][^>]*>.*?(faq|frequently asked|questions).*?</h[2-3]>',
        "table": r'<table',
        "list": r'<[uo]l',
        "images": r'<img',
        "internal_links": r'<a[^>]+href=["\'][^"\']*(?:' + r'yourdomain\.com' + r')[^"\']*["\']',
        "h2_headings": r'<h2',
        "h3_headings": r'<h3'
    }
    
    # Minimum thresholds
    MIN_WORD_COUNT = 1000
    MIN_IMAGES = 3
    MIN_H2_HEADINGS = 4
    MIN_INTERNAL_LINKS = 5
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute content refresh task"""
        task_type = task.get("type", "analyze")
        
        if task_type == "analyze":
            return await self._analyze_content(task)
        elif task_type == "generate_refresh":
            return await self._generate_refresh_plan(task)
        elif task_type == "apply_refresh":
            return await self._apply_refresh(task)
        elif task_type == "add_faq":
            return await self._generate_faq(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _analyze_content(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze content for refresh opportunities
        
        Task params:
            content: HTML content to analyze
            page_url: Page URL
            gsc_data: GSC performance data for the page
        """
        content = task.get("content", "")
        page_url = task.get("page_url", "")
        gsc_data = task.get("gsc_data", {})
        
        if not content:
            return {"status": "error", "error": "Content required"}
        
        logger.info(f"Analyzing content for refresh: {page_url}")
        
        # Content analysis
        analysis = self._analyze_content_structure(content)
        
        # Identify gaps
        gaps = self._identify_gaps(analysis)
        
        # GSC-based insights
        performance_issues = self._analyze_performance(gsc_data)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(gaps, performance_issues)
        
        return {
            "status": "success",
            "page_url": page_url,
            "analysis": analysis,
            "gaps": gaps,
            "performance_issues": performance_issues,
            "recommendations": recommendations,
            "refresh_needed": len(gaps) > 0 or len(performance_issues) > 0
        }
    
    def _analyze_content_structure(self, content: str) -> Dict[str, Any]:
        """Analyze content structure"""
        # Strip HTML for word count
        text_only = re.sub(r'<[^>]+>', ' ', content)
        word_count = len(text_only.split())
        
        # Count elements
        h2_count = len(re.findall(r'<h2', content, re.IGNORECASE))
        h3_count = len(re.findall(r'<h3', content, re.IGNORECASE))
        image_count = len(re.findall(r'<img', content, re.IGNORECASE))
        link_count = len(re.findall(r'<a\s', content, re.IGNORECASE))
        table_count = len(re.findall(r'<table', content, re.IGNORECASE))
        list_count = len(re.findall(r'<[uo]l', content, re.IGNORECASE))
        
        # Check for FAQ section
        has_faq = bool(re.search(r'faq|frequently asked|questions', content, re.IGNORECASE))
        
        # Check for schema markup
        has_schema = 'application/ld+json' in content or 'itemtype' in content
        
        return {
            "word_count": word_count,
            "h2_headings": h2_count,
            "h3_headings": h3_count,
            "images": image_count,
            "links": link_count,
            "tables": table_count,
            "lists": list_count,
            "has_faq": has_faq,
            "has_schema": has_schema
        }
    
    def _identify_gaps(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify content gaps"""
        gaps = []
        
        if analysis["word_count"] < self.MIN_WORD_COUNT:
            gaps.append({
                "type": "word_count",
                "current": analysis["word_count"],
                "recommended": self.MIN_WORD_COUNT,
                "priority": "high",
                "action": f"Add {self.MIN_WORD_COUNT - analysis['word_count']} more words"
            })
        
        if analysis["h2_headings"] < self.MIN_H2_HEADINGS:
            gaps.append({
                "type": "headings",
                "current": analysis["h2_headings"],
                "recommended": self.MIN_H2_HEADINGS,
                "priority": "medium",
                "action": "Add more H2 sections for better structure"
            })
        
        if analysis["images"] < self.MIN_IMAGES:
            gaps.append({
                "type": "images",
                "current": analysis["images"],
                "recommended": self.MIN_IMAGES,
                "priority": "medium",
                "action": "Add more images to improve engagement"
            })
        
        if not analysis["has_faq"]:
            gaps.append({
                "type": "faq",
                "current": 0,
                "recommended": 1,
                "priority": "high",
                "action": "Add FAQ section for featured snippet opportunities"
            })
        
        if analysis["tables"] == 0 and analysis["word_count"] > 500:
            gaps.append({
                "type": "table",
                "current": 0,
                "recommended": 1,
                "priority": "low",
                "action": "Consider adding a comparison or data table"
            })
        
        if analysis["lists"] < 2:
            gaps.append({
                "type": "lists",
                "current": analysis["lists"],
                "recommended": 2,
                "priority": "low",
                "action": "Add bullet or numbered lists for scannability"
            })
        
        return gaps
    
    def _analyze_performance(self, gsc_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze GSC performance issues"""
        issues = []
        
        if not gsc_data:
            return issues
        
        position = gsc_data.get("position", 0)
        ctr = gsc_data.get("ctr", 0)
        impressions = gsc_data.get("impressions", 0)
        clicks_trend = gsc_data.get("clicks_trend", 0)
        position_trend = gsc_data.get("position_trend", 0)
        
        # Declining clicks
        if clicks_trend < -0.2:  # 20% decline
            issues.append({
                "type": "declining_clicks",
                "severity": "high",
                "metric": f"{round(clicks_trend * 100)}% click decline",
                "action": "Major content refresh needed"
            })
        
        # Position slipping
        if position_trend > 3:  # Dropped 3+ positions
            issues.append({
                "type": "position_drop",
                "severity": "high",
                "metric": f"Dropped {round(position_trend)} positions",
                "action": "Strengthen content and add internal links"
            })
        
        # Low CTR
        expected_ctr = {1: 0.32, 2: 0.17, 3: 0.11, 4: 0.08, 5: 0.07, 
                       6: 0.05, 7: 0.04, 8: 0.03, 9: 0.025, 10: 0.02}
        
        pos_int = min(int(position), 10)
        if pos_int > 0 and ctr < expected_ctr.get(pos_int, 0.01) * 0.6:
            issues.append({
                "type": "low_ctr",
                "severity": "medium",
                "metric": f"CTR {round(ctr * 100, 2)}% below expected",
                "action": "Optimize title and meta description"
            })
        
        return issues
    
    def _generate_recommendations(
        self,
        gaps: List[Dict],
        performance_issues: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Generate prioritized recommendations"""
        recommendations = []
        
        # High priority gaps
        for gap in gaps:
            if gap["priority"] == "high":
                recommendations.append({
                    "action": gap["action"],
                    "priority": "high",
                    "type": gap["type"],
                    "impact": "Significant ranking improvement expected"
                })
        
        # Performance issues
        for issue in performance_issues:
            recommendations.append({
                "action": issue["action"],
                "priority": issue["severity"],
                "type": issue["type"],
                "impact": f"Address {issue['type']}: {issue['metric']}"
            })
        
        # Medium priority gaps
        for gap in gaps:
            if gap["priority"] == "medium":
                recommendations.append({
                    "action": gap["action"],
                    "priority": "medium",
                    "type": gap["type"],
                    "impact": "Moderate improvement expected"
                })
        
        return recommendations
    
    async def _generate_refresh_plan(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a complete refresh plan with patches
        
        Task params:
            content: Current HTML content
            page_url: Page URL
            post_id: WordPress post ID
            keyword: Target keyword
            gsc_data: GSC data
        """
        content = task.get("content", "")
        page_url = task.get("page_url", "")
        post_id = task.get("post_id")
        keyword = task.get("keyword", "")
        gsc_data = task.get("gsc_data", {})
        
        # First analyze
        analysis_result = await self._analyze_content({
            "content": content,
            "page_url": page_url,
            "gsc_data": gsc_data
        })
        
        analysis = analysis_result.get("analysis", {})
        gaps = analysis_result.get("gaps", [])
        
        # Generate patches for each gap
        patches = []
        import uuid
        
        for gap in gaps:
            patch = await self._generate_patch_for_gap(gap, keyword, content)
            if patch:
                patches.append(patch)
        
        # SEO updates
        seo_updates = {}
        if any(issue["type"] == "low_ctr" for issue in analysis_result.get("performance_issues", [])):
            seo_updates["optimize_title_meta"] = True
        
        # Create refresh plan
        plan = RefreshPlan(
            plan_id=str(uuid.uuid4())[:8],
            page_url=page_url,
            post_id=post_id,
            current_word_count=analysis.get("word_count", 0),
            target_word_count=max(analysis.get("word_count", 0), self.MIN_WORD_COUNT),
            patches=patches,
            seo_updates=seo_updates,
            estimated_improvement=self._estimate_improvement(gaps)
        )
        
        return {
            "status": "success",
            "plan": plan.to_dict()
        }
    
    async def _generate_patch_for_gap(
        self,
        gap: Dict[str, Any],
        keyword: str,
        content: str
    ) -> Optional[RefreshPatch]:
        """Generate a patch for a specific gap"""
        import uuid
        
        gap_type = gap["type"]
        
        if gap_type == "faq":
            faq_content = await self._generate_faq_section(keyword)
            return RefreshPatch(
                patch_id=str(uuid.uuid4())[:8],
                patch_type="add_faq",
                location="before_conclusion",
                content=faq_content,
                reason="Add FAQ section for featured snippets",
                priority="high"
            )
        
        if gap_type == "word_count":
            additional_content = await self._generate_additional_content(
                keyword, gap["recommended"] - gap["current"]
            )
            return RefreshPatch(
                patch_id=str(uuid.uuid4())[:8],
                patch_type="add_section",
                location="after_last_h2",
                content=additional_content,
                reason=f"Add {gap['recommended'] - gap['current']} words",
                priority="high"
            )
        
        if gap_type == "table":
            table_content = self._generate_comparison_table(keyword)
            return RefreshPatch(
                patch_id=str(uuid.uuid4())[:8],
                patch_type="add_table",
                location="after_intro",
                content=table_content,
                reason="Add comparison table for better engagement",
                priority="medium"
            )
        
        return None
    
    async def _generate_faq_section(self, keyword: str) -> str:
        """Generate FAQ section HTML"""
        # This would use AI in production
        faq_questions = [
            f"What is {keyword}?",
            f"How does {keyword} work?",
            f"What are the benefits of {keyword}?",
            f"How to choose the best {keyword}?",
            f"Where can I find {keyword}?"
        ]
        
        faq_html = '<section class="faq-section">\n'
        faq_html += f'<h2>Frequently Asked Questions About {keyword.title()}</h2>\n'
        
        for question in faq_questions[:4]:
            faq_html += f'''
<div class="faq-item" itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
    <h3 itemprop="name">{question}</h3>
    <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
        <p itemprop="text">[AI-generated answer for: {question}]</p>
    </div>
</div>
'''
        
        faq_html += '</section>'
        return faq_html
    
    async def _generate_additional_content(self, keyword: str, word_target: int) -> str:
        """Generate additional content to meet word count"""
        # Placeholder - would use AI
        return f'''
<h2>More About {keyword.title()}</h2>
<p>[AI-generated content targeting {word_target} additional words about {keyword}]</p>

<h3>Key Considerations</h3>
<ul>
    <li>Important factor 1</li>
    <li>Important factor 2</li>
    <li>Important factor 3</li>
</ul>
'''
    
    def _generate_comparison_table(self, keyword: str) -> str:
        """Generate a comparison table"""
        return f'''
<h2>{keyword.title()} Comparison</h2>
<table class="comparison-table">
    <thead>
        <tr>
            <th>Feature</th>
            <th>Option A</th>
            <th>Option B</th>
            <th>Option C</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Price</td>
            <td>$$$</td>
            <td>$$</td>
            <td>$</td>
        </tr>
        <tr>
            <td>Quality</td>
            <td>High</td>
            <td>Medium</td>
            <td>Basic</td>
        </tr>
        <tr>
            <td>Best For</td>
            <td>Professionals</td>
            <td>Regular users</td>
            <td>Beginners</td>
        </tr>
    </tbody>
</table>
'''
    
    def _estimate_improvement(self, gaps: List[Dict]) -> str:
        """Estimate ranking improvement from addressing gaps"""
        high_priority = sum(1 for g in gaps if g["priority"] == "high")
        medium_priority = sum(1 for g in gaps if g["priority"] == "medium")
        
        if high_priority >= 2:
            return "+3-5 positions expected"
        elif high_priority >= 1:
            return "+2-3 positions expected"
        elif medium_priority >= 2:
            return "+1-2 positions expected"
        else:
            return "Minor improvement expected"
    
    async def _apply_refresh(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Apply refresh patches to content"""
        plan = task.get("plan", {})
        
        # This would integrate with WordPress
        return {
            "status": "success",
            "message": "Refresh plan ready for application",
            "plan_id": plan.get("plan_id"),
            "patches_to_apply": len(plan.get("patches", []))
        }
    
    async def _generate_faq(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate FAQ section only"""
        keyword = task.get("keyword", "")
        faq_html = await self._generate_faq_section(keyword)
        
        return {
            "status": "success",
            "faq_html": faq_html,
            "question_count": 4
        }
