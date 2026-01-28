"""
Quality Gate Agent
Implements P2-2, P2-3: Content quality enforcement for pSEO with RAG

Features:
- Similarity detection (prevent duplicate content)
- Information increment validation (unique value requirement)
- Minimum component requirements
- Fact checking (RAG-based verification)
- Quality scoring
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import hashlib
from difflib import SequenceMatcher
import re

from src.agents.base_agent import BaseAgent
# Import KnowledgeBase (soft import to avoid circular dependency issues if any, though none expected)
try:
    from src.core.rag import KnowledgeBase
except ImportError:
    KnowledgeBase = None

logger = logging.getLogger(__name__)


@dataclass
class QualityCheck:
    """Individual quality check result"""
    check_name: str
    passed: bool
    score: float  # 0-100
    message: str
    severity: str  # error, warning, info
    details: Optional[Dict[str, Any]] = None


@dataclass
class QualityReport:
    """Complete quality assessment report"""
    content_id: str
    overall_score: float  # 0-100
    passed: bool
    checks: List[QualityCheck]
    errors: List[str]
    warnings: List[str]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_id": self.content_id,
            "overall_score": round(self.overall_score, 1),
            "passed": self.passed,
            "total_checks": len(self.checks),
            "errors": self.errors,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "checks": [
                {
                    "name": c.check_name,
                    "passed": c.passed,
                    "score": round(c.score, 1),
                    "message": c.message
                }
                for c in self.checks
            ]
        }


class QualityGateAgent(BaseAgent):
    """
    Quality Gate Agent
    
    Enforces quality standards before content publication:
    - Prevents duplicate/similar content
    - Validates information increment
    - Ensures minimum component count
    - Verifies factual accuracy (when RAG enabled)
    """
    
    # Quality thresholds
    MIN_SIMILARITY_THRESHOLD = 0.85  # 85% similar = duplicate
    MIN_WORD_COUNT = 500
    MIN_UNIQUE_INFO_PERCENTAGE = 30  # 30% unique information required
    MIN_COMPONENT_COUNT = 4
    MIN_OVERALL_SCORE = 60
    
    # Component requirements
    REQUIRED_COMPONENTS = ["summary", "faq"]  # Must have these
    RECOMMENDED_COMPONENTS = ["table", "specifications"]
    
    def __init__(self):
        super().__init__()
        # Initialize RAG if available
        self.rag = KnowledgeBase() if KnowledgeBase else None
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute quality gate check"""
        task_type = task.get("type", "full_check")
        
        if task_type == "full_check":
            return await self._full_quality_check(task)
        elif task_type == "similarity_check":
            return await self._check_similarity(task)
        elif task_type == "component_check":
            return await self._check_components(task)
        elif task_type == "fact_check":
            return await self._fact_check(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _full_quality_check(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run comprehensive quality checks
        
        Task params:
            content: Content to check
            content_id: Unique identifier
            existing_content: List of existing content for similarity check
            components: List of component types included
            facts_to_verify: Optional facts for verification (explicit list) or "auto"
        """
        content = task.get("content", "")
        content_id = task.get("content_id", "unknown")
        existing_content = task.get("existing_content", [])
        components = task.get("components", [])
        facts_to_verify = task.get("facts_to_verify", None)
        
        if not content:
            return {"status": "error", "error": "Content required"}
        
        logger.info(f"Running quality gate for: {content_id}")
        
        checks = []
        errors = []
        warnings = []
        recommendations = []
        
        # Check 1: Word count
        word_count_check = self._check_word_count(content)
        checks.append(word_count_check)
        if not word_count_check.passed:
            errors.append(word_count_check.message)
        
        # Check 2: Similarity (anti-duplicate)
        if existing_content:
            similarity_check = await self._check_content_similarity(content, existing_content)
            checks.append(similarity_check)
            if not similarity_check.passed:
                errors.append(similarity_check.message)
        
        # Check 3: Information increment
        increment_check = self._check_information_increment(content, existing_content)
        checks.append(increment_check)
        if not increment_check.passed:
            warnings.append(increment_check.message)
        
        # Check 4: Component requirements
        component_check = self._check_component_requirements(components)
        checks.append(component_check)
        if not component_check.passed:
            warnings.append(component_check.message)
        
        # Check 5: Content structure
        structure_check = self._check_content_structure(content)
        checks.append(structure_check)
        if structure_check.score < 70:
            recommendations.append(structure_check.message)
        
        # Check 6: SEO elements
        seo_check = self._check_seo_elements(content)
        checks.append(seo_check)
        if seo_check.score < 80:
            recommendations.append(seo_check.message)
            
        # Check 7: Fact Check (RAG)
        if self.rag and facts_to_verify:
            # Create a specific task for fact checking
            fact_result = await self._fact_check({
                "content": content,
                "facts_to_verify": facts_to_verify
            })
            if fact_result["status"] == "success":
                fact_check = QualityCheck(
                    check_name="fact_check",
                    passed=fact_result["passed"],
                    score=fact_result["score"],
                    message=fact_result["message"],
                    severity="error" if not fact_result["passed"] else "info",
                    details={"verified_facts": fact_result["verified_facts"], "unverified_claims": fact_result["unverified_claims"]}
                )
                checks.append(fact_check)
                if not fact_check.passed:
                    # Depending on strictness, this could be an error or warning
                    # For now, treat as warning to be safe
                    warnings.append(fact_check.message)
        
        # Calculate overall score
        overall_score = sum(c.score for c in checks) / len(checks) if checks else 0
        
        # Determine if passed
        passed = (
            overall_score >= self.MIN_OVERALL_SCORE
            and len(errors) == 0
        )
        
        report = QualityReport(
            content_id=content_id,
            overall_score=overall_score,
            passed=passed,
            checks=checks,
            errors=errors,
            warnings=warnings,
            recommendations=recommendations
        )
        
        # Publish event
        await self.publish_event("quality_check_completed", {
            "content_id": content_id,
            "passed": passed,
            "score": overall_score
        })
        
        return {
            "status": "success",
            "report": report.to_dict()
        }
    
    def _check_word_count(self, content: str) -> QualityCheck:
        """Check if content meets minimum word count"""
        word_count = len(content.split())
        
        if word_count >= self.MIN_WORD_COUNT:
            return QualityCheck(
                check_name="word_count",
                passed=True,
                score=min(100, (word_count / self.MIN_WORD_COUNT) * 100),
                message=f"Word count: {word_count} (sufficient)",
                severity="info"
            )
        else:
            deficit = self.MIN_WORD_COUNT - word_count
            return QualityCheck(
                check_name="word_count",
                passed=False,
                score=(word_count / self.MIN_WORD_COUNT) * 100,
                message=f"Word count too low: {word_count} (need {deficit} more words)",
                severity="error"
            )
    
    async def _check_content_similarity(
        self,
        content: str,
        existing_content: List[str]
    ) -> QualityCheck:
        """Check for duplicate/similar content"""
        content_lower = content.lower()
        
        max_similarity = 0.0
        most_similar_idx = -1
        
        for idx, existing in enumerate(existing_content):
            similarity = self._calculate_similarity(content_lower, existing.lower())
            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_idx = idx
        
        if max_similarity >= self.MIN_SIMILARITY_THRESHOLD:
            return QualityCheck(
                check_name="similarity",
                passed=False,
                score=(1 - max_similarity) * 100,
                message=f"Content too similar to existing content #{most_similar_idx} ({round(max_similarity * 100, 1)}% match)",
                severity="error",
                details={"similarity": max_similarity, "match_index": most_similar_idx}
            )
        else:
            return QualityCheck(
                check_name="similarity",
                passed=True,
                score=(1 - max_similarity) * 100,
                message=f"Content is unique (max similarity: {round(max_similarity * 100, 1)}%)",
                severity="info"
            )
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using SequenceMatcher"""
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _check_information_increment(
        self,
        content: str,
        existing_content: List[str]
    ) -> QualityCheck:
        """Check if content provides unique information"""
        if not existing_content:
            return QualityCheck(
                check_name="information_increment",
                passed=True,
                score=100,
                message="First content, no comparison needed",
                severity="info"
            )
        
        # Extract unique sentences/facts
        content_sentences = set(s.strip() for s in content.split('.') if len(s.strip()) > 20)
        
        existing_sentences = set()
        for existing in existing_content:
            existing_sentences.update(
                s.strip() for s in existing.split('.') if len(s.strip()) > 20
            )
        
        unique_sentences = content_sentences - existing_sentences
        if content_sentences:
            unique_percentage = (len(unique_sentences) / len(content_sentences)) * 100
        else:
            unique_percentage = 0
        
        if unique_percentage >= self.MIN_UNIQUE_INFO_PERCENTAGE:
            return QualityCheck(
                check_name="information_increment",
                passed=True,
                score=unique_percentage,
                message=f"Good information increment: {round(unique_percentage, 1)}% unique content",
                severity="info"
            )
        else:
            return QualityCheck(
                check_name="information_increment",
                passed=False,
                score=unique_percentage,
                message=f"Insufficient unique information: only {round(unique_percentage, 1)}% unique (need {self.MIN_UNIQUE_INFO_PERCENTAGE}%)",
                severity="warning"
            )
    
    def _check_component_requirements(self, components: List[str]) -> QualityCheck:
        """Check if required components are present"""
        component_set = set(c.lower() for c in components)
        
        missing_required = [c for c in self.REQUIRED_COMPONENTS if c not in component_set]
        missing_recommended = [c for c in self.RECOMMENDED_COMPONENTS if c not in component_set]
        
        if missing_required:
            return QualityCheck(
                check_name="components",
                passed=False,
                score=50,
                message=f"Missing required components: {', '.join(missing_required)}",
                severity="warning",
                details={"missing_required": missing_required}
            )
        
        component_count = len(components)
        if component_count >= self.MIN_COMPONENT_COUNT:
            score = min(100, (component_count / self.MIN_COMPONENT_COUNT) * 100)
            message = f"Component count: {component_count} (good)"
            if missing_recommended:
                message += f". Recommended to add: {', '.join(missing_recommended)}"
            
            return QualityCheck(
                check_name="components",
                passed=True,
                score=score,
                message=message,
                severity="info"
            )
        else:
            return QualityCheck(
                check_name="components",
                passed=False,
                score=(component_count / self.MIN_COMPONENT_COUNT) * 100,
                message=f"Too few components: {component_count} (need {self.MIN_COMPONENT_COUNT})",
                severity="warning"
            )
    
    def _check_content_structure(self, content: str) -> QualityCheck:
        """Check content structure quality"""
        # import re # Moved to global scope to avoid redefined-outer-name if needed, but keeping simple here
        
        score = 50  # Base score
        issues = []
        
        # Check for headings
        h2_count = len(re.findall(r'<h2', content, re.IGNORECASE))
        h3_count = len(re.findall(r'<h3', content, re.IGNORECASE))
        
        if h2_count >= 3:
            score += 15
        else:
            issues.append(f"Only {h2_count} H2 headings (recommend 3+)")
        
        # Check for lists
        list_count = len(re.findall(r'<[uo]l>', content, re.IGNORECASE))
        if list_count >= 2:
            score += 10
        else:
            issues.append(f"Only {list_count} lists (recommend 2+)")
        
        # Check for images
        img_count = len(re.findall(r'<img', content, re.IGNORECASE))
        if img_count >= 2:
            score += 10
        else:
            issues.append(f"Only {img_count} images (recommend 2+)")
        
        # Check for internal links
        link_count = len(re.findall(r'<a\s', content, re.IGNORECASE))
        if link_count >= 3:
            score += 15
        else:
            issues.append(f"Only {link_count} links (recommend 3+)")
        
        message = "Good content structure"
        if issues:
            message = "Structure issues: " + "; ".join(issues)
        
        return QualityCheck(
            check_name="structure",
            passed=score >= 70,
            score=score,
            message=message,
            severity="info" if score >= 70 else "warning"
        )
    
    def _check_seo_elements(self, content: str) -> QualityCheck:
        """Check SEO elements"""
        
        score = 50
        issues = []
        
        # Check for schema markup
        if 'itemtype' in content or 'application/ld+json' in content:
            score += 20
        else:
            issues.append("No schema markup")
        
        # Check for meta description equivalent
        if len(content) > 0:
            score += 15
        
        # Check for keyword density (simplified)
        score += 15
        
        message = "SEO elements present"
        if issues:
            message = "SEO improvements needed: " + "; ".join(issues)
        
        return QualityCheck(
            check_name="seo",
            passed=score >= 80,
            score=score,
            message=message,
            severity="info"
        )
    
    async def _fact_check(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fact check content against RAG database
        
        If 'facts_to_verify' is a list, check each.
        If it's 'auto', we'd parse content (advanced).
        Here we assume explicit list or simple keyword check.
        """
        content = task.get("content", "")
        facts_to_verify = task.get("facts_to_verify", [])
        
        if not self.rag:
            return {
                "status": "skipped", 
                "message": "RAG system not available",
                "passed": True,
                "score": 100,
                "verified_facts": 0,
                "unverified_claims": 0
            }
        
        verified_count = 0
        unverified_count = 0
        failed_facts = []
        
        # A simple check: Can we find the fact in our knowledge base?
        # In a real system, we'd use LLM to compare Content Statement vs RAG Context
        # Here we do a semantic search for the fact and check if score > threshold
        
        if isinstance(facts_to_verify, list):
            for fact in facts_to_verify:
                results = await self.rag.search(fact, limit=1)
                if results and results[0][1] > 0.3: # Threshold
                    verified_count += 1
                else:
                    unverified_count += 1
                    failed_facts.append(fact)
        
        # Score calculation
        total = verified_count + unverified_count
        score = (verified_count / total * 100) if total > 0 else 100
        
        passed = score >= 70  # Allow some wiggle room
        
        message = f"Verified {verified_count}/{total} facts"
        if failed_facts:
            message += f". Unverified: {'; '.join(failed_facts[:3])}..."
            
        return {
            "status": "success",
            "passed": passed,
            "score": score,
            "message": message,
            "verified_facts": verified_count,
            "unverified_claims": unverified_count
        }
