"""
Enhanced Quality Gate Service
Implements BUG-009: Comprehensive content quality validation

Features:
- Multi-algorithm similarity detection (SequenceMatcher, Jaccard, Shingle-based)
- Semantic information increment validation
- Detailed diagnostic reports with problem localization
- Actionable fix recommendations for each issue
- Content health scoring with weighted factors
"""

import logging
import re
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class IssueSeverity(str, Enum):
    """Issue severity levels"""
    CRITICAL = "critical"  # Blocks publication
    HIGH = "high"          # Should fix before publish
    MEDIUM = "medium"      # Recommended fix
    LOW = "low"            # Nice to have
    INFO = "info"          # Informational only


class IssueCategory(str, Enum):
    """Issue categories"""
    DUPLICATE = "duplicate"
    THIN_CONTENT = "thin_content"
    STRUCTURE = "structure"
    SEO = "seo"
    QUALITY = "quality"
    FACTUAL = "factual"
    READABILITY = "readability"


@dataclass
class QualityIssue:
    """Detailed quality issue with fix recommendation"""
    issue_id: str
    category: IssueCategory
    severity: IssueSeverity
    title: str
    description: str
    location: Optional[str]  # Where in content (e.g., "paragraph 3", "heading 2")
    current_value: Optional[str]
    expected_value: Optional[str]
    fix_recommendation: str
    auto_fixable: bool = False
    estimated_fix_time: str = "5 min"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "current_value": self.current_value,
            "expected_value": self.expected_value,
            "fix_recommendation": self.fix_recommendation,
            "auto_fixable": self.auto_fixable,
            "estimated_fix_time": self.estimated_fix_time
        }


@dataclass
class SimilarityMatch:
    """Similarity detection result"""
    matched_content_id: str
    matched_url: Optional[str]
    overall_similarity: float
    algorithm_scores: Dict[str, float]
    matching_sections: List[Dict[str, Any]]
    is_duplicate: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "matched_content_id": self.matched_content_id,
            "matched_url": self.matched_url,
            "overall_similarity": round(self.overall_similarity * 100, 1),
            "algorithm_scores": {k: round(v * 100, 1) for k, v in self.algorithm_scores.items()},
            "matching_sections_count": len(self.matching_sections),
            "is_duplicate": self.is_duplicate
        }


@dataclass
class InformationAnalysis:
    """Information increment analysis result"""
    unique_facts_count: int
    total_facts_count: int
    unique_percentage: float
    unique_topics: List[str]
    repeated_topics: List[str]
    information_value_score: float
    passes_threshold: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "unique_facts_count": self.unique_facts_count,
            "total_facts_count": self.total_facts_count,
            "unique_percentage": round(self.unique_percentage, 1),
            "unique_topics": self.unique_topics[:5],
            "repeated_topics": self.repeated_topics[:5],
            "information_value_score": round(self.information_value_score, 1),
            "passes_threshold": self.passes_threshold
        }


@dataclass
class QualityDiagnostic:
    """Complete quality diagnostic report"""
    content_id: str
    overall_score: float
    grade: str  # A, B, C, D, F
    passed: bool
    can_publish: bool
    issues: List[QualityIssue]
    similarity_analysis: Optional[SimilarityMatch]
    information_analysis: Optional[InformationAnalysis]
    metrics: Dict[str, Any]
    summary: str
    top_recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_id": self.content_id,
            "overall_score": round(self.overall_score, 1),
            "grade": self.grade,
            "passed": self.passed,
            "can_publish": self.can_publish,
            "issues_count": len(self.issues),
            "issues_by_severity": self._count_by_severity(),
            "issues": [i.to_dict() for i in self.issues],
            "similarity_analysis": self.similarity_analysis.to_dict() if self.similarity_analysis else None,
            "information_analysis": self.information_analysis.to_dict() if self.information_analysis else None,
            "metrics": self.metrics,
            "summary": self.summary,
            "top_recommendations": self.top_recommendations
        }
    
    def _count_by_severity(self) -> Dict[str, int]:
        counts = {s.value: 0 for s in IssueSeverity}
        for issue in self.issues:
            counts[issue.severity.value] += 1
        return counts


class EnhancedQualityGate:
    """
    Enhanced Quality Gate Service
    
    Provides comprehensive content quality validation with:
    - Multi-algorithm similarity detection
    - Semantic information increment analysis
    - Detailed issue diagnostics
    - Actionable fix recommendations
    """
    
    # Thresholds
    DUPLICATE_THRESHOLD = 0.85  # 85% = duplicate
    HIGH_SIMILARITY_THRESHOLD = 0.70  # 70% = warning
    MIN_UNIQUE_INFO_PERCENTAGE = 30
    MIN_WORD_COUNT = 500
    MIN_READING_GRADE = 6  # Flesch-Kincaid grade level
    MAX_READING_GRADE = 14
    
    # Scoring weights
    SCORE_WEIGHTS = {
        "similarity": 0.25,
        "information": 0.20,
        "structure": 0.15,
        "seo": 0.15,
        "readability": 0.10,
        "completeness": 0.15
    }
    
    # Grade thresholds
    GRADE_THRESHOLDS = {
        "A": 90,
        "B": 80,
        "C": 70,
        "D": 60,
        "F": 0
    }
    
    def __init__(self):
        self.shingle_size = 5  # For w-shingling
    
    # ==================== Main Entry Point ====================
    
    async def full_diagnostic(
        self,
        content: str,
        content_id: str,
        existing_content: Optional[List[Dict[str, Any]]] = None,
        target_keyword: Optional[str] = None,
        components: Optional[List[str]] = None
    ) -> QualityDiagnostic:
        """
        Run comprehensive quality diagnostic
        
        Args:
            content: HTML/text content to analyze
            content_id: Unique identifier
            existing_content: List of existing content dicts with 'id', 'content', 'url'
            target_keyword: Target SEO keyword
            components: List of component types included
        
        Returns:
            Complete QualityDiagnostic with issues and recommendations
        """
        logger.info(f"Running quality diagnostic for: {content_id}")
        
        issues = []
        scores = {}
        
        # Clean content for analysis
        text_content = self._strip_html(content)
        
        # 1. Similarity Analysis
        similarity_result = None
        if existing_content:
            similarity_result, similarity_issues = await self._analyze_similarity(
                content, text_content, existing_content
            )
            issues.extend(similarity_issues)
            scores["similarity"] = 100 - (similarity_result.overall_similarity * 100) if similarity_result else 100
        else:
            scores["similarity"] = 100
        
        # 2. Information Increment Analysis
        info_result = None
        if existing_content:
            info_result, info_issues = self._analyze_information_increment(
                text_content, 
                [self._strip_html(e.get("content", "")) for e in existing_content]
            )
            issues.extend(info_issues)
            scores["information"] = info_result.information_value_score if info_result else 100
        else:
            scores["information"] = 100
        
        # 3. Structure Analysis
        structure_score, structure_issues = self._analyze_structure(content)
        issues.extend(structure_issues)
        scores["structure"] = structure_score
        
        # 4. SEO Analysis
        seo_score, seo_issues = self._analyze_seo(content, target_keyword)
        issues.extend(seo_issues)
        scores["seo"] = seo_score
        
        # 5. Readability Analysis
        readability_score, readability_issues = self._analyze_readability(text_content)
        issues.extend(readability_issues)
        scores["readability"] = readability_score
        
        # 6. Completeness Analysis
        completeness_score, completeness_issues = self._analyze_completeness(
            content, text_content, components or []
        )
        issues.extend(completeness_issues)
        scores["completeness"] = completeness_score
        
        # Calculate overall score
        overall_score = sum(
            scores[k] * self.SCORE_WEIGHTS[k] 
            for k in self.SCORE_WEIGHTS.keys()
        )
        
        # Determine grade
        grade = self._calculate_grade(overall_score)
        
        # Check if can publish
        critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        high_issues = [i for i in issues if i.severity == IssueSeverity.HIGH]
        
        can_publish = len(critical_issues) == 0 and overall_score >= 60
        passed = len(critical_issues) == 0 and len(high_issues) <= 2 and overall_score >= 70
        
        # Generate summary
        summary = self._generate_summary(overall_score, grade, issues, can_publish)
        
        # Top recommendations
        top_recommendations = self._generate_top_recommendations(issues)
        
        # Compile metrics
        metrics = {
            "word_count": len(text_content.split()),
            "character_count": len(text_content),
            "paragraph_count": len(re.findall(r'<p[>\s]', content, re.IGNORECASE)),
            "heading_count": len(re.findall(r'<h[1-6][>\s]', content, re.IGNORECASE)),
            "image_count": len(re.findall(r'<img', content, re.IGNORECASE)),
            "link_count": len(re.findall(r'<a\s', content, re.IGNORECASE)),
            "component_scores": scores
        }
        
        return QualityDiagnostic(
            content_id=content_id,
            overall_score=overall_score,
            grade=grade,
            passed=passed,
            can_publish=can_publish,
            issues=issues,
            similarity_analysis=similarity_result,
            information_analysis=info_result,
            metrics=metrics,
            summary=summary,
            top_recommendations=top_recommendations
        )
    
    # ==================== Similarity Detection ====================
    
    async def _analyze_similarity(
        self,
        content: str,
        text_content: str,
        existing_content: List[Dict[str, Any]]
    ) -> Tuple[Optional[SimilarityMatch], List[QualityIssue]]:
        """Analyze content similarity using multiple algorithms"""
        issues = []
        max_match = None
        max_similarity = 0.0
        
        for existing in existing_content:
            existing_text = self._strip_html(existing.get("content", ""))
            existing_id = existing.get("id", "unknown")
            existing_url = existing.get("url")
            
            # Multi-algorithm similarity
            algo_scores = {
                "sequence_matcher": self._sequence_matcher_similarity(text_content, existing_text),
                "jaccard": self._jaccard_similarity(text_content, existing_text),
                "shingle": self._shingle_similarity(text_content, existing_text)
            }
            
            # Weighted average (shingle is best for plagiarism detection)
            overall = (
                algo_scores["sequence_matcher"] * 0.3 +
                algo_scores["jaccard"] * 0.2 +
                algo_scores["shingle"] * 0.5
            )
            
            if overall > max_similarity:
                max_similarity = overall
                matching_sections = self._find_matching_sections(text_content, existing_text)
                
                max_match = SimilarityMatch(
                    matched_content_id=existing_id,
                    matched_url=existing_url,
                    overall_similarity=overall,
                    algorithm_scores=algo_scores,
                    matching_sections=matching_sections,
                    is_duplicate=overall >= self.DUPLICATE_THRESHOLD
                )
        
        # Generate issues based on similarity
        if max_match and max_match.is_duplicate:
            issues.append(QualityIssue(
                issue_id="SIM-001",
                category=IssueCategory.DUPLICATE,
                severity=IssueSeverity.CRITICAL,
                title="Duplicate Content Detected",
                description=f"Content is {round(max_match.overall_similarity * 100)}% similar to existing content",
                location="Entire document",
                current_value=f"{round(max_match.overall_similarity * 100)}% similarity",
                expected_value="< 85% similarity",
                fix_recommendation=(
                    f"This content is too similar to '{max_match.matched_content_id}'. "
                    f"Actions: 1) Rewrite at least 50% of the content with unique perspective. "
                    f"2) Add original research, data, or examples. "
                    f"3) Consider merging with the existing content instead."
                ),
                auto_fixable=False,
                estimated_fix_time="30-60 min"
            ))
        elif max_match and max_match.overall_similarity >= self.HIGH_SIMILARITY_THRESHOLD:
            issues.append(QualityIssue(
                issue_id="SIM-002",
                category=IssueCategory.DUPLICATE,
                severity=IssueSeverity.HIGH,
                title="High Content Similarity",
                description=f"Content has {round(max_match.overall_similarity * 100)}% similarity with existing content",
                location=f"Multiple sections match '{max_match.matched_content_id}'",
                current_value=f"{round(max_match.overall_similarity * 100)}% similarity",
                expected_value="< 70% similarity",
                fix_recommendation=(
                    f"Content overlaps significantly with '{max_match.matched_content_id}'. "
                    f"Differentiate by: 1) Adding 3+ unique sections with new information. "
                    f"2) Rewriting matching paragraphs in your own words. "
                    f"3) Including unique examples, case studies, or data points."
                ),
                auto_fixable=False,
                estimated_fix_time="20-30 min"
            ))
        
        return max_match, issues
    
    def _sequence_matcher_similarity(self, text1: str, text2: str) -> float:
        """Standard SequenceMatcher similarity"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Jaccard similarity based on word sets"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def _shingle_similarity(self, text1: str, text2: str) -> float:
        """W-shingling similarity (better for plagiarism detection)"""
        shingles1 = self._get_shingles(text1)
        shingles2 = self._get_shingles(text2)
        
        if not shingles1 or not shingles2:
            return 0.0
        
        intersection = shingles1 & shingles2
        union = shingles1 | shingles2
        
        return len(intersection) / len(union)
    
    def _get_shingles(self, text: str) -> Set[str]:
        """Generate w-shingles from text"""
        words = text.lower().split()
        if len(words) < self.shingle_size:
            return {" ".join(words)}
        
        shingles = set()
        for i in range(len(words) - self.shingle_size + 1):
            shingle = " ".join(words[i:i + self.shingle_size])
            shingles.add(shingle)
        
        return shingles
    
    def _find_matching_sections(self, text1: str, text2: str) -> List[Dict[str, Any]]:
        """Find specific matching sections between texts"""
        matches = []
        
        # Split into sentences
        sentences1 = [s.strip() for s in text1.split('.') if len(s.strip()) > 30]
        sentences2 = [s.strip() for s in text2.split('.') if len(s.strip()) > 30]
        
        for i, s1 in enumerate(sentences1[:20]):  # Limit to first 20 sentences
            for s2 in sentences2:
                sim = SequenceMatcher(None, s1.lower(), s2.lower()).ratio()
                if sim > 0.8:  # High match
                    matches.append({
                        "source_position": i,
                        "source_text": s1[:100] + "...",
                        "match_text": s2[:100] + "...",
                        "similarity": round(sim * 100, 1)
                    })
                    break
        
        return matches[:10]  # Top 10 matches
    
    # ==================== Information Increment ====================
    
    def _analyze_information_increment(
        self,
        content: str,
        existing_contents: List[str]
    ) -> Tuple[InformationAnalysis, List[QualityIssue]]:
        """Analyze unique information value"""
        issues = []
        
        # Extract facts/statements (sentences with factual indicators)
        content_facts = self._extract_facts(content)
        
        # Build corpus of existing facts
        existing_facts = set()
        for existing in existing_contents:
            existing_facts.update(self._extract_facts(existing))
        
        # Find unique facts
        unique_facts = []
        repeated_facts = []
        
        for fact in content_facts:
            is_unique = True
            fact_lower = fact.lower()
            
            for existing_fact in existing_facts:
                sim = SequenceMatcher(None, fact_lower, existing_fact.lower()).ratio()
                if sim > 0.7:  # Similar fact
                    is_unique = False
                    break
            
            if is_unique:
                unique_facts.append(fact)
            else:
                repeated_facts.append(fact)
        
        # Calculate metrics
        total_facts = len(content_facts)
        unique_count = len(unique_facts)
        unique_percentage = (unique_count / total_facts * 100) if total_facts > 0 else 0
        
        # Extract topic keywords
        unique_topics = self._extract_keywords(unique_facts)
        repeated_topics = self._extract_keywords(repeated_facts)
        
        # Information value score
        info_score = min(100, unique_percentage * 2)  # Scale up
        
        passes = unique_percentage >= self.MIN_UNIQUE_INFO_PERCENTAGE
        
        analysis = InformationAnalysis(
            unique_facts_count=unique_count,
            total_facts_count=total_facts,
            unique_percentage=unique_percentage,
            unique_topics=unique_topics,
            repeated_topics=repeated_topics,
            information_value_score=info_score,
            passes_threshold=passes
        )
        
        # Generate issues
        if not passes:
            issues.append(QualityIssue(
                issue_id="INFO-001",
                category=IssueCategory.THIN_CONTENT,
                severity=IssueSeverity.HIGH,
                title="Insufficient Unique Information",
                description=f"Only {round(unique_percentage)}% of content is unique (need {self.MIN_UNIQUE_INFO_PERCENTAGE}%)",
                location="Throughout content",
                current_value=f"{unique_count} unique facts out of {total_facts}",
                expected_value=f"At least {self.MIN_UNIQUE_INFO_PERCENTAGE}% unique information",
                fix_recommendation=(
                    f"Add more original content: "
                    f"1) Include {3 - len(unique_topics)} new topics not covered elsewhere. "
                    f"2) Add original data, statistics, or research. "
                    f"3) Provide unique insights, opinions, or analysis. "
                    f"4) Include case studies or real-world examples. "
                    f"Repeated topics to differentiate: {', '.join(repeated_topics[:3])}"
                ),
                auto_fixable=False,
                estimated_fix_time="20-40 min"
            ))
        
        return analysis, issues
    
    def _extract_facts(self, text: str) -> List[str]:
        """Extract factual statements from text"""
        # Factual indicators
        fact_patterns = [
            r'[A-Z][^.!?]*(?:is|are|was|were|has|have|can|will|should|must)[^.!?]*[.!?]',
            r'[A-Z][^.!?]*(?:\d+%|\d+ percent|\$\d+|\d+ million|\d+ billion)[^.!?]*[.!?]',
            r'[A-Z][^.!?]*(?:according to|research shows|studies indicate)[^.!?]*[.!?]',
        ]
        
        facts = []
        for pattern in fact_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            facts.extend(matches)
        
        # Also include simple sentences
        sentences = [s.strip() for s in text.split('.') if 20 < len(s.strip()) < 200]
        facts.extend(sentences[:30])  # Limit
        
        return list(set(facts))
    
    def _extract_keywords(self, texts: List[str]) -> List[str]:
        """Extract important keywords from text list"""
        words = []
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                      'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                      'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                      'can', 'need', 'to', 'of', 'in', 'for', 'on', 'with', 'at',
                      'by', 'from', 'as', 'into', 'through', 'during', 'before',
                      'after', 'above', 'below', 'between', 'under', 'again',
                      'further', 'then', 'once', 'and', 'but', 'or', 'nor', 'so',
                      'yet', 'both', 'each', 'few', 'more', 'most', 'other', 'some',
                      'such', 'no', 'not', 'only', 'own', 'same', 'than', 'too',
                      'very', 'just', 'also', 'now', 'that', 'this', 'these', 'those'}
        
        for text in texts:
            text_words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
            words.extend([w for w in text_words if w not in stop_words])
        
        # Get most common
        counter = Counter(words)
        return [word for word, _ in counter.most_common(10)]
    
    # ==================== Structure Analysis ====================
    
    def _analyze_structure(self, content: str) -> Tuple[float, List[QualityIssue]]:
        """Analyze content structure"""
        issues = []
        score = 100
        
        # Count structural elements
        h1_count = len(re.findall(r'<h1[>\s]', content, re.IGNORECASE))
        h2_count = len(re.findall(r'<h2[>\s]', content, re.IGNORECASE))
        h3_count = len(re.findall(r'<h3[>\s]', content, re.IGNORECASE))
        p_count = len(re.findall(r'<p[>\s]', content, re.IGNORECASE))
        list_count = len(re.findall(r'<[uo]l[>\s]', content, re.IGNORECASE))
        img_count = len(re.findall(r'<img', content, re.IGNORECASE))
        
        # H1 check
        if h1_count == 0:
            score -= 15
            issues.append(QualityIssue(
                issue_id="STR-001",
                category=IssueCategory.STRUCTURE,
                severity=IssueSeverity.HIGH,
                title="Missing H1 Heading",
                description="Content has no H1 heading",
                location="Beginning of content",
                current_value="0 H1 headings",
                expected_value="Exactly 1 H1 heading",
                fix_recommendation="Add a single H1 heading at the top that contains your primary keyword and clearly describes the page content.",
                auto_fixable=True,
                estimated_fix_time="2 min"
            ))
        elif h1_count > 1:
            score -= 10
            issues.append(QualityIssue(
                issue_id="STR-002",
                category=IssueCategory.STRUCTURE,
                severity=IssueSeverity.MEDIUM,
                title="Multiple H1 Headings",
                description=f"Content has {h1_count} H1 headings (should have 1)",
                location="Multiple locations",
                current_value=f"{h1_count} H1 headings",
                expected_value="1 H1 heading",
                fix_recommendation="Keep only one H1 heading. Convert others to H2 headings.",
                auto_fixable=True,
                estimated_fix_time="5 min"
            ))
        
        # H2 check
        if h2_count < 3:
            score -= 10
            issues.append(QualityIssue(
                issue_id="STR-003",
                category=IssueCategory.STRUCTURE,
                severity=IssueSeverity.MEDIUM,
                title="Insufficient Section Headings",
                description=f"Only {h2_count} H2 headings (recommend 3+)",
                location="Throughout content",
                current_value=f"{h2_count} H2 headings",
                expected_value="3+ H2 headings",
                fix_recommendation="Add more H2 section headings to break up content. Each major topic should have its own H2. This improves readability and SEO.",
                auto_fixable=False,
                estimated_fix_time="10 min"
            ))
        
        # Paragraph check
        if p_count < 5:
            score -= 10
            issues.append(QualityIssue(
                issue_id="STR-004",
                category=IssueCategory.STRUCTURE,
                severity=IssueSeverity.MEDIUM,
                title="Insufficient Paragraphs",
                description=f"Only {p_count} paragraphs found",
                location="Content body",
                current_value=f"{p_count} paragraphs",
                expected_value="5+ paragraphs",
                fix_recommendation="Break content into more paragraphs. Aim for 2-4 sentences per paragraph for better readability.",
                auto_fixable=False,
                estimated_fix_time="5 min"
            ))
        
        # List check
        if list_count == 0:
            score -= 5
            issues.append(QualityIssue(
                issue_id="STR-005",
                category=IssueCategory.STRUCTURE,
                severity=IssueSeverity.LOW,
                title="No Lists Used",
                description="Content has no bulleted or numbered lists",
                location="Content body",
                current_value="0 lists",
                expected_value="1+ lists",
                fix_recommendation="Add bulleted or numbered lists to present key points, steps, or features. Lists improve scannability and can trigger featured snippets.",
                auto_fixable=False,
                estimated_fix_time="5 min"
            ))
        
        # Image check
        if img_count == 0:
            score -= 10
            issues.append(QualityIssue(
                issue_id="STR-006",
                category=IssueCategory.STRUCTURE,
                severity=IssueSeverity.MEDIUM,
                title="No Images",
                description="Content has no images",
                location="Throughout content",
                current_value="0 images",
                expected_value="2+ images",
                fix_recommendation="Add relevant images with descriptive alt text. Include at least one hero image and one supporting image (chart, infographic, product photo).",
                auto_fixable=False,
                estimated_fix_time="10 min"
            ))
        
        return max(0, score), issues
    
    # ==================== SEO Analysis ====================
    
    def _analyze_seo(
        self, 
        content: str, 
        target_keyword: Optional[str]
    ) -> Tuple[float, List[QualityIssue]]:
        """Analyze SEO elements"""
        issues = []
        score = 100
        
        text_content = self._strip_html(content)
        
        # Schema markup check
        has_schema = 'application/ld+json' in content or 'itemtype=' in content
        if not has_schema:
            score -= 15
            issues.append(QualityIssue(
                issue_id="SEO-001",
                category=IssueCategory.SEO,
                severity=IssueSeverity.MEDIUM,
                title="Missing Schema Markup",
                description="No structured data (JSON-LD or Microdata) detected",
                location="Page head or content",
                current_value="No schema",
                expected_value="Article, FAQPage, or relevant schema",
                fix_recommendation=(
                    "Add JSON-LD schema markup. For blog posts, use Article schema. "
                    "For FAQs, use FAQPage schema. This helps search engines understand your content and can enable rich snippets."
                ),
                auto_fixable=True,
                estimated_fix_time="10 min"
            ))
        
        # Keyword optimization
        if target_keyword:
            keyword_lower = target_keyword.lower()
            content_lower = text_content.lower()
            
            # Keyword in content
            keyword_count = content_lower.count(keyword_lower)
            word_count = len(text_content.split())
            keyword_density = (keyword_count / word_count * 100) if word_count > 0 else 0
            
            if keyword_count == 0:
                score -= 20
                issues.append(QualityIssue(
                    issue_id="SEO-002",
                    category=IssueCategory.SEO,
                    severity=IssueSeverity.HIGH,
                    title="Target Keyword Missing",
                    description=f"Target keyword '{target_keyword}' not found in content",
                    location="Entire content",
                    current_value="0 occurrences",
                    expected_value="3-5 natural occurrences",
                    fix_recommendation=(
                        f"Include '{target_keyword}' naturally in: "
                        f"1) The first paragraph. 2) At least one H2 heading. "
                        f"3) 2-3 times in body content. Aim for 0.5-1.5% keyword density."
                    ),
                    auto_fixable=False,
                    estimated_fix_time="10 min"
                ))
            elif keyword_density > 3:
                score -= 10
                issues.append(QualityIssue(
                    issue_id="SEO-003",
                    category=IssueCategory.SEO,
                    severity=IssueSeverity.MEDIUM,
                    title="Keyword Stuffing Detected",
                    description=f"Keyword density too high: {round(keyword_density, 1)}%",
                    location="Throughout content",
                    current_value=f"{round(keyword_density, 1)}% density ({keyword_count} occurrences)",
                    expected_value="0.5-2.0% density",
                    fix_recommendation=(
                        f"Reduce keyword usage. Replace some instances of '{target_keyword}' with "
                        f"synonyms, related terms, or pronouns. High keyword density can trigger spam filters."
                    ),
                    auto_fixable=False,
                    estimated_fix_time="10 min"
                ))
        
        # Internal links check
        internal_links = len(re.findall(r'<a[^>]+href=["\'][^"\']*["\']', content))
        if internal_links < 3:
            score -= 10
            issues.append(QualityIssue(
                issue_id="SEO-004",
                category=IssueCategory.SEO,
                severity=IssueSeverity.MEDIUM,
                title="Insufficient Internal Links",
                description=f"Only {internal_links} links found",
                location="Content body",
                current_value=f"{internal_links} links",
                expected_value="3+ internal links",
                fix_recommendation=(
                    "Add internal links to related content on your site. "
                    "Link to: 1) Your pillar/hub page on this topic. "
                    "2) 2-3 related articles. 3) Relevant product or service pages. "
                    "Use descriptive anchor text."
                ),
                auto_fixable=False,
                estimated_fix_time="10 min"
            ))
        
        return max(0, score), issues
    
    # ==================== Readability Analysis ====================
    
    def _analyze_readability(self, text: str) -> Tuple[float, List[QualityIssue]]:
        """Analyze content readability"""
        issues = []
        score = 100
        
        # Calculate readability metrics
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if len(s.strip()) > 0]
        
        word_count = len(words)
        sentence_count = len(sentences)
        
        if sentence_count == 0:
            return 50, [QualityIssue(
                issue_id="READ-001",
                category=IssueCategory.READABILITY,
                severity=IssueSeverity.HIGH,
                title="No Sentences Detected",
                description="Content doesn't appear to have proper sentences",
                location="Entire content",
                current_value="0 sentences",
                expected_value="Proper sentence structure",
                fix_recommendation="Ensure content has proper punctuation with periods, question marks, or exclamation points.",
                auto_fixable=False,
                estimated_fix_time="15 min"
            )]
        
        # Average sentence length
        avg_sentence_length = word_count / sentence_count
        
        if avg_sentence_length > 25:
            score -= 15
            issues.append(QualityIssue(
                issue_id="READ-002",
                category=IssueCategory.READABILITY,
                severity=IssueSeverity.MEDIUM,
                title="Sentences Too Long",
                description=f"Average sentence length: {round(avg_sentence_length)} words",
                location="Throughout content",
                current_value=f"{round(avg_sentence_length)} words/sentence",
                expected_value="15-20 words/sentence",
                fix_recommendation=(
                    "Break long sentences into shorter ones. "
                    "Target 15-20 words per sentence for optimal readability. "
                    "Use periods instead of commas where possible."
                ),
                auto_fixable=False,
                estimated_fix_time="15 min"
            ))
        
        # Paragraph length (rough check)
        paragraphs = re.split(r'\n\n+', text)
        long_paragraphs = [p for p in paragraphs if len(p.split()) > 100]
        
        if len(long_paragraphs) > 2:
            score -= 10
            issues.append(QualityIssue(
                issue_id="READ-003",
                category=IssueCategory.READABILITY,
                severity=IssueSeverity.LOW,
                title="Long Paragraphs",
                description=f"{len(long_paragraphs)} paragraphs exceed 100 words",
                location="Multiple paragraphs",
                current_value=f"{len(long_paragraphs)} long paragraphs",
                expected_value="Paragraphs of 50-75 words",
                fix_recommendation=(
                    "Break long paragraphs into 2-3 shorter ones. "
                    "Each paragraph should focus on one idea. "
                    "This improves mobile readability and engagement."
                ),
                auto_fixable=False,
                estimated_fix_time="10 min"
            ))
        
        return max(0, score), issues
    
    # ==================== Completeness Analysis ====================
    
    def _analyze_completeness(
        self,
        content: str,
        text_content: str,
        components: List[str]
    ) -> Tuple[float, List[QualityIssue]]:
        """Analyze content completeness"""
        issues = []
        score = 100
        
        # Word count check
        word_count = len(text_content.split())
        if word_count < self.MIN_WORD_COUNT:
            score -= 25
            issues.append(QualityIssue(
                issue_id="COMP-001",
                category=IssueCategory.THIN_CONTENT,
                severity=IssueSeverity.CRITICAL,
                title="Content Too Short",
                description=f"Word count: {word_count} (minimum: {self.MIN_WORD_COUNT})",
                location="Entire content",
                current_value=f"{word_count} words",
                expected_value=f"{self.MIN_WORD_COUNT}+ words",
                fix_recommendation=(
                    f"Add {self.MIN_WORD_COUNT - word_count} more words. "
                    f"Expand by: 1) Adding more detailed explanations. "
                    f"2) Including examples or case studies. "
                    f"3) Answering related questions. "
                    f"4) Adding an FAQ section."
                ),
                auto_fixable=False,
                estimated_fix_time="30-60 min"
            ))
        
        # Component check
        component_set = set(c.lower() for c in components)
        required = {"summary", "faq"}
        
        missing_required = required - component_set
        if missing_required:
            score -= 15
            issues.append(QualityIssue(
                issue_id="COMP-002",
                category=IssueCategory.QUALITY,
                severity=IssueSeverity.MEDIUM,
                title="Missing Required Components",
                description=f"Missing: {', '.join(missing_required)}",
                location="Content sections",
                current_value=f"Components: {', '.join(components) or 'none'}",
                expected_value=f"Must include: {', '.join(required)}",
                fix_recommendation=(
                    f"Add missing components: "
                    + ("Include a summary/introduction section at the top. " if "summary" in missing_required else "")
                    + ("Add an FAQ section with 3-5 common questions. " if "faq" in missing_required else "")
                ),
                auto_fixable=False,
                estimated_fix_time="15 min"
            ))
        
        return max(0, score), issues
    
    # ==================== Utility Methods ====================
    
    def _strip_html(self, html: str) -> str:
        """Remove HTML tags and normalize whitespace"""
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score"""
        for grade, threshold in self.GRADE_THRESHOLDS.items():
            if score >= threshold:
                return grade
        return "F"
    
    def _generate_summary(
        self,
        score: float,
        grade: str,
        issues: List[QualityIssue],
        can_publish: bool
    ) -> str:
        """Generate human-readable summary"""
        critical = len([i for i in issues if i.severity == IssueSeverity.CRITICAL])
        high = len([i for i in issues if i.severity == IssueSeverity.HIGH])
        
        if score >= 90:
            return f"Excellent quality (Grade {grade}). Content is ready to publish."
        elif score >= 80:
            return f"Good quality (Grade {grade}). Minor improvements suggested."
        elif score >= 70:
            return f"Acceptable quality (Grade {grade}). Address {high} high-priority issues before publishing."
        elif score >= 60:
            if can_publish:
                return f"Below average (Grade {grade}). Can publish but should address {critical + high} issues soon."
            return f"Below average (Grade {grade}). Fix {critical} critical issues before publishing."
        else:
            return f"Poor quality (Grade {grade}). Requires significant revision. {critical} critical, {high} high-priority issues."
    
    def _generate_top_recommendations(self, issues: List[QualityIssue]) -> List[str]:
        """Generate top 5 actionable recommendations"""
        # Sort by severity
        severity_order = {
            IssueSeverity.CRITICAL: 0,
            IssueSeverity.HIGH: 1,
            IssueSeverity.MEDIUM: 2,
            IssueSeverity.LOW: 3,
            IssueSeverity.INFO: 4
        }
        
        sorted_issues = sorted(issues, key=lambda x: severity_order[x.severity])
        
        recommendations = []
        for issue in sorted_issues[:5]:
            prefix = "🔴" if issue.severity == IssueSeverity.CRITICAL else (
                "🟡" if issue.severity == IssueSeverity.HIGH else "🟢"
            )
            recommendations.append(f"{prefix} {issue.title}: {issue.fix_recommendation[:150]}...")
        
        return recommendations
