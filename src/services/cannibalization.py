"""
Enhanced Cannibalization Detector Service
Implements BUG-013: Advanced keyword cannibalization detection

Features:
- Semantic similarity-based detection (TF-IDF, keyword overlap, topic modeling)
- URL structure pattern analysis
- Ranking fluctuation analysis over time
- Intelligent merge/redirect recommendations
- Cannibalization health scoring
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from difflib import SequenceMatcher
import math

logger = logging.getLogger(__name__)


class CannibalizationSeverity(str, Enum):
    """Cannibalization severity levels"""
    CRITICAL = "critical"    # Immediate action required
    HIGH = "high"            # Should fix soon
    MEDIUM = "medium"        # Monitor and optimize
    LOW = "low"              # Minor overlap
    NONE = "none"            # No cannibalization


class CannibalizationType(str, Enum):
    """Types of cannibalization"""
    KEYWORD_OVERLAP = "keyword_overlap"      # Same keyword, different pages
    CONTENT_DUPLICATE = "content_duplicate"   # Very similar content
    URL_CONFLICT = "url_conflict"             # URL structure suggests same topic
    INTENT_MISMATCH = "intent_mismatch"       # Same intent, competing pages
    RANKING_SPLIT = "ranking_split"           # Both ranking for same query


class RecommendedAction(str, Enum):
    """Recommended actions for cannibalization"""
    MERGE_CONTENT = "merge_content"           # Combine into one page
    REDIRECT_301 = "redirect_301"             # Redirect weaker to stronger
    DIFFERENTIATE = "differentiate"           # Make pages more distinct
    CANONICAL = "canonical"                   # Add canonical tag
    NOINDEX = "noindex"                       # Remove from index
    INTERNAL_LINK = "internal_link"           # Link to consolidate authority
    MONITOR = "monitor"                       # Watch but no action yet
    RETARGET = "retarget"                     # Change target keyword


@dataclass
class CompetingPage:
    """A page competing for the same keyword"""
    page_url: str
    page_id: Optional[int]
    title: str
    target_keyword: str
    word_count: int
    # GSC metrics
    impressions: int
    clicks: int
    position: float
    ctr: float
    # Trends
    position_trend: float  # Negative = improving
    impressions_trend: float
    # Content analysis
    content_quality_score: float
    internal_links_count: int
    last_updated: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_url": self.page_url,
            "page_id": self.page_id,
            "title": self.title,
            "target_keyword": self.target_keyword,
            "word_count": self.word_count,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "position": round(self.position, 1),
            "ctr": round(self.ctr * 100, 2),
            "position_trend": round(self.position_trend, 2),
            "impressions_trend": round(self.impressions_trend, 2),
            "content_quality_score": round(self.content_quality_score, 1),
            "internal_links_count": self.internal_links_count
        }


@dataclass
class CannibalizationIssue:
    """Detailed cannibalization issue"""
    issue_id: str
    query: str
    cannibalization_type: CannibalizationType
    severity: CannibalizationSeverity
    competing_pages: List[CompetingPage]
    # Analysis
    semantic_similarity: float
    url_similarity: float
    ranking_volatility: float
    estimated_traffic_loss: int
    # Recommendations
    recommended_action: RecommendedAction
    winner_page: Optional[str]
    action_details: str
    implementation_steps: List[str]
    expected_improvement: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "query": self.query,
            "type": self.cannibalization_type.value,
            "severity": self.severity.value,
            "competing_pages": [p.to_dict() for p in self.competing_pages],
            "analysis": {
                "semantic_similarity": round(self.semantic_similarity * 100, 1),
                "url_similarity": round(self.url_similarity * 100, 1),
                "ranking_volatility": round(self.ranking_volatility, 2),
                "estimated_traffic_loss": self.estimated_traffic_loss
            },
            "recommendation": {
                "action": self.recommended_action.value,
                "winner_page": self.winner_page,
                "details": self.action_details,
                "steps": self.implementation_steps,
                "expected_improvement": self.expected_improvement
            }
        }


@dataclass
class CannibalizationReport:
    """Complete cannibalization analysis report"""
    analyzed_queries: int
    total_issues: int
    issues_by_severity: Dict[str, int]
    issues: List[CannibalizationIssue]
    health_score: float  # 0-100
    estimated_total_traffic_loss: int
    top_priorities: List[str]
    summary: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "analyzed_queries": self.analyzed_queries,
            "total_issues": self.total_issues,
            "issues_by_severity": self.issues_by_severity,
            "issues": [i.to_dict() for i in self.issues],
            "health_score": round(self.health_score, 1),
            "estimated_total_traffic_loss": self.estimated_total_traffic_loss,
            "top_priorities": self.top_priorities,
            "summary": self.summary
        }


class CannibalizationDetector:
    """
    Enhanced Cannibalization Detector
    
    Detects and analyzes keyword cannibalization using:
    - Semantic similarity analysis
    - URL structure patterns
    - Ranking fluctuation tracking
    - Content comparison
    """
    
    # Thresholds
    SEMANTIC_SIMILARITY_THRESHOLD = 0.6  # Pages with > 60% similarity
    URL_SIMILARITY_THRESHOLD = 0.5
    MIN_IMPRESSIONS = 50  # Minimum impressions to consider
    POSITION_VOLATILITY_THRESHOLD = 3.0  # More than 3 position change = volatile
    RANKING_CLOSE_THRESHOLD = 5  # Pages within 5 positions
    
    def __init__(self):
        self.stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'to', 'of',
            'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through',
            'during', 'before', 'after', 'above', 'below', 'between', 'under',
            'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'each', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'not', 'only', 'own', 'same',
            'than', 'too', 'very', 'just', 'also', 'now', 'how', 'what', 'which',
            'who', 'where', 'when', 'why', 'all', 'any', 'this', 'that', 'these'
        }
    
    # ==================== Main Entry Point ====================
    
    async def analyze(
        self,
        gsc_data: List[Dict[str, Any]],
        page_content: Optional[Dict[str, str]] = None,
        historical_data: Optional[List[Dict[str, Any]]] = None,
        min_impressions: int = 50
    ) -> CannibalizationReport:
        """
        Perform comprehensive cannibalization analysis
        
        Args:
            gsc_data: GSC query performance data with page, query, metrics
            page_content: Optional dict of page URL -> content for semantic analysis
            historical_data: Optional historical GSC data for trend analysis
            min_impressions: Minimum impressions threshold
        
        Returns:
            Complete CannibalizationReport with issues and recommendations
        """
        logger.info(f"Analyzing cannibalization for {len(gsc_data)} data points")
        
        # Group data by query
        query_pages = self._group_by_query(gsc_data, min_impressions)
        
        # Find potential cannibalization
        issues = []
        issue_counter = 0
        
        for query, pages in query_pages.items():
            if len(pages) < 2:
                continue
            
            # Analyze this query's pages
            issue = await self._analyze_query_cannibalization(
                query=query,
                pages=pages,
                page_content=page_content,
                historical_data=historical_data,
                issue_id=f"CANN-{issue_counter:04d}"
            )
            
            if issue:
                issues.append(issue)
                issue_counter += 1
        
        # Calculate summary metrics
        issues_by_severity = self._count_by_severity(issues)
        total_traffic_loss = sum(i.estimated_traffic_loss for i in issues)
        health_score = self._calculate_health_score(issues, len(query_pages))
        
        # Sort by severity and traffic loss
        issues.sort(key=lambda x: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}[x.severity.value],
            -x.estimated_traffic_loss
        ))
        
        # Generate top priorities
        top_priorities = self._generate_priorities(issues[:5])
        
        # Generate summary
        summary = self._generate_summary(issues, health_score)
        
        return CannibalizationReport(
            analyzed_queries=len(query_pages),
            total_issues=len(issues),
            issues_by_severity=issues_by_severity,
            issues=issues,
            health_score=health_score,
            estimated_total_traffic_loss=total_traffic_loss,
            top_priorities=top_priorities,
            summary=summary
        )
    
    # ==================== Query Grouping ====================
    
    def _group_by_query(
        self,
        gsc_data: List[Dict[str, Any]],
        min_impressions: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group GSC data by query"""
        query_pages = defaultdict(list)
        
        for row in gsc_data:
            query = row.get("query", "").lower().strip()
            impressions = row.get("impressions", 0)
            
            if impressions >= min_impressions and query:
                query_pages[query].append(row)
        
        return query_pages
    
    # ==================== Individual Query Analysis ====================
    
    async def _analyze_query_cannibalization(
        self,
        query: str,
        pages: List[Dict[str, Any]],
        page_content: Optional[Dict[str, str]],
        historical_data: Optional[List[Dict[str, Any]]],
        issue_id: str
    ) -> Optional[CannibalizationIssue]:
        """Analyze cannibalization for a single query"""
        
        if len(pages) < 2:
            return None
        
        # Sort by impressions (most important first)
        pages.sort(key=lambda x: x.get("impressions", 0), reverse=True)
        
        # Get top 2 competing pages
        page1_data = pages[0]
        page2_data = pages[1]
        
        page1_url = page1_data.get("page", "")
        page2_url = page2_data.get("page", "")
        
        # Check if this is true cannibalization
        # Criteria: Both pages get significant impressions
        page2_impressions = page2_data.get("impressions", 0)
        page1_impressions = page1_data.get("impressions", 0)
        
        if page2_impressions < page1_impressions * 0.15:
            # Page 2 has < 15% of page 1's impressions - not true cannibalization
            return None
        
        # Calculate similarity scores
        semantic_sim = 0.0
        if page_content:
            content1 = page_content.get(page1_url, "")
            content2 = page_content.get(page2_url, "")
            if content1 and content2:
                semantic_sim = self._calculate_semantic_similarity(content1, content2)
        
        url_sim = self._calculate_url_similarity(page1_url, page2_url)
        
        # Calculate ranking volatility
        ranking_volatility = self._calculate_ranking_volatility(
            page1_url, page2_url, historical_data
        )
        
        # Determine severity
        severity = self._determine_severity(
            page1_data, page2_data, semantic_sim, url_sim, ranking_volatility
        )
        
        if severity == CannibalizationSeverity.NONE:
            return None
        
        # Determine cannibalization type
        cann_type = self._determine_type(semantic_sim, url_sim, page1_data, page2_data)
        
        # Create competing page objects
        competing_pages = self._create_competing_pages(pages[:5], historical_data)
        
        # Calculate estimated traffic loss
        traffic_loss = self._estimate_traffic_loss(pages)
        
        # Generate recommendation
        winner, action, action_details, steps, expected = self._generate_recommendation(
            query, competing_pages, severity, cann_type
        )
        
        return CannibalizationIssue(
            issue_id=issue_id,
            query=query,
            cannibalization_type=cann_type,
            severity=severity,
            competing_pages=competing_pages,
            semantic_similarity=semantic_sim,
            url_similarity=url_sim,
            ranking_volatility=ranking_volatility,
            estimated_traffic_loss=traffic_loss,
            recommended_action=action,
            winner_page=winner,
            action_details=action_details,
            implementation_steps=steps,
            expected_improvement=expected
        )
    
    # ==================== Semantic Similarity ====================
    
    def _calculate_semantic_similarity(self, content1: str, content2: str) -> float:
        """Calculate semantic similarity between two contents using TF-IDF like approach"""
        
        # Clean and tokenize
        words1 = self._tokenize(content1)
        words2 = self._tokenize(content2)
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate TF for both documents
        tf1 = Counter(words1)
        tf2 = Counter(words2)
        
        # Get all unique words
        all_words = set(words1) | set(words2)
        
        # Calculate cosine similarity
        dot_product = sum(tf1.get(w, 0) * tf2.get(w, 0) for w in all_words)
        magnitude1 = math.sqrt(sum(c ** 2 for c in tf1.values()))
        magnitude2 = math.sqrt(sum(c ** 2 for c in tf2.values()))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        cosine_sim = dot_product / (magnitude1 * magnitude2)
        
        # Also calculate Jaccard for phrases
        phrases1 = self._get_phrases(content1)
        phrases2 = self._get_phrases(content2)
        
        if phrases1 and phrases2:
            jaccard = len(phrases1 & phrases2) / len(phrases1 | phrases2)
            # Weighted average
            return cosine_sim * 0.6 + jaccard * 0.4
        
        return cosine_sim
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize and clean text"""
        text = text.lower()
        words = re.findall(r'\b[a-z]{3,}\b', text)
        return [w for w in words if w not in self.stop_words]
    
    def _get_phrases(self, text: str, n: int = 3) -> Set[str]:
        """Extract n-gram phrases"""
        words = self._tokenize(text)
        if len(words) < n:
            return set()
        
        phrases = set()
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i:i+n])
            phrases.add(phrase)
        
        return phrases
    
    # ==================== URL Similarity ====================
    
    def _calculate_url_similarity(self, url1: str, url2: str) -> float:
        """Calculate URL structure similarity"""
        
        # Normalize URLs
        path1 = self._get_url_path(url1)
        path2 = self._get_url_path(url2)
        
        # Direct sequence match
        seq_sim = SequenceMatcher(None, path1, path2).ratio()
        
        # Segment analysis
        segments1 = set(path1.split('/'))
        segments2 = set(path2.split('/'))
        
        segments1.discard('')
        segments2.discard('')
        
        if not segments1 or not segments2:
            return seq_sim
        
        segment_overlap = len(segments1 & segments2) / max(len(segments1), len(segments2))
        
        # Word analysis in URL
        words1 = set(re.findall(r'[a-z]+', path1.lower()))
        words2 = set(re.findall(r'[a-z]+', path2.lower()))
        
        if words1 and words2:
            word_overlap = len(words1 & words2) / max(len(words1), len(words2))
        else:
            word_overlap = 0
        
        # Weighted combination
        return seq_sim * 0.3 + segment_overlap * 0.3 + word_overlap * 0.4
    
    def _get_url_path(self, url: str) -> str:
        """Extract path from URL"""
        # Remove protocol and domain
        if '://' in url:
            url = url.split('://', 1)[1]
        if '/' in url:
            url = url.split('/', 1)[1]
        else:
            url = ''
        # Remove query string
        if '?' in url:
            url = url.split('?')[0]
        return url
    
    # ==================== Ranking Volatility ====================
    
    def _calculate_ranking_volatility(
        self,
        url1: str,
        url2: str,
        historical_data: Optional[List[Dict[str, Any]]]
    ) -> float:
        """Calculate ranking volatility between two pages"""
        
        if not historical_data:
            return 0.0
        
        # Group historical data by date
        daily_positions = defaultdict(lambda: {"url1": [], "url2": []})
        
        for row in historical_data:
            page = row.get("page", "")
            date = row.get("date", "")
            position = row.get("position", 0)
            
            if date:
                if url1 in page:
                    daily_positions[date]["url1"].append(position)
                elif url2 in page:
                    daily_positions[date]["url2"].append(position)
        
        # Calculate position swaps and volatility
        position_changes = []
        prev_winner = None
        
        for date in sorted(daily_positions.keys()):
            data = daily_positions[date]
            pos1 = sum(data["url1"]) / len(data["url1"]) if data["url1"] else 100
            pos2 = sum(data["url2"]) / len(data["url2"]) if data["url2"] else 100
            
            current_winner = "url1" if pos1 < pos2 else "url2"
            
            if prev_winner and current_winner != prev_winner:
                position_changes.append(abs(pos1 - pos2))
            
            prev_winner = current_winner
        
        if not position_changes:
            return 0.0
        
        # Higher volatility = more swaps with larger position differences
        return sum(position_changes) / len(position_changes)
    
    # ==================== Severity Determination ====================
    
    def _determine_severity(
        self,
        page1: Dict,
        page2: Dict,
        semantic_sim: float,
        url_sim: float,
        volatility: float
    ) -> CannibalizationSeverity:
        """Determine cannibalization severity"""
        
        total_impressions = page1.get("impressions", 0) + page2.get("impressions", 0)
        position1 = page1.get("position", 100)
        position2 = page2.get("position", 100)
        position_diff = abs(position1 - position2)
        
        # Critical: High impressions, close positions, high similarity
        if (total_impressions > 1000 and 
            position_diff < 3 and 
            (semantic_sim > 0.7 or url_sim > 0.6)):
            return CannibalizationSeverity.CRITICAL
        
        # High: Significant traffic, similar content
        if (total_impressions > 500 and 
            position_diff < 5 and
            (semantic_sim > 0.5 or url_sim > 0.4)):
            return CannibalizationSeverity.HIGH
        
        # Medium: Some overlap
        if (total_impressions > 200 and
            position_diff < 10):
            return CannibalizationSeverity.MEDIUM
        
        # Low: Minor overlap
        if total_impressions > 100:
            return CannibalizationSeverity.LOW
        
        return CannibalizationSeverity.NONE
    
    # ==================== Type Determination ====================
    
    def _determine_type(
        self,
        semantic_sim: float,
        url_sim: float,
        page1: Dict,
        page2: Dict
    ) -> CannibalizationType:
        """Determine the type of cannibalization"""
        
        if semantic_sim > 0.8:
            return CannibalizationType.CONTENT_DUPLICATE
        
        if url_sim > 0.7:
            return CannibalizationType.URL_CONFLICT
        
        # Check if rankings are very close (split)
        pos1 = page1.get("position", 100)
        pos2 = page2.get("position", 100)
        if abs(pos1 - pos2) < 3:
            return CannibalizationType.RANKING_SPLIT
        
        return CannibalizationType.KEYWORD_OVERLAP
    
    # ==================== Competing Pages Creation ====================
    
    def _create_competing_pages(
        self,
        pages: List[Dict],
        historical_data: Optional[List[Dict]]
    ) -> List[CompetingPage]:
        """Create CompetingPage objects"""
        competing = []
        
        for page_data in pages[:5]:  # Top 5
            url = page_data.get("page", "")
            
            # Calculate trends
            pos_trend = 0.0
            imp_trend = 0.0
            
            if historical_data:
                pos_trend, imp_trend = self._calculate_trends(url, historical_data)
            
            competing.append(CompetingPage(
                page_url=url,
                page_id=page_data.get("page_id"),
                title=page_data.get("title", url.split('/')[-1]),
                target_keyword=page_data.get("query", ""),
                word_count=page_data.get("word_count", 0),
                impressions=page_data.get("impressions", 0),
                clicks=page_data.get("clicks", 0),
                position=page_data.get("position", 0),
                ctr=page_data.get("ctr", 0),
                position_trend=pos_trend,
                impressions_trend=imp_trend,
                content_quality_score=page_data.get("quality_score", 70),
                internal_links_count=page_data.get("internal_links", 0),
                last_updated=page_data.get("last_updated")
            ))
        
        return competing
    
    def _calculate_trends(
        self,
        url: str,
        historical_data: List[Dict]
    ) -> Tuple[float, float]:
        """Calculate position and impression trends for a URL"""
        
        # Filter data for this URL
        url_data = [d for d in historical_data if url in d.get("page", "")]
        
        if len(url_data) < 2:
            return 0.0, 0.0
        
        # Sort by date
        url_data.sort(key=lambda x: x.get("date", ""))
        
        # Compare first half to second half
        mid = len(url_data) // 2
        first_half = url_data[:mid]
        second_half = url_data[mid:]
        
        avg_pos_first = sum(d.get("position", 0) for d in first_half) / len(first_half)
        avg_pos_second = sum(d.get("position", 0) for d in second_half) / len(second_half)
        
        avg_imp_first = sum(d.get("impressions", 0) for d in first_half) / len(first_half)
        avg_imp_second = sum(d.get("impressions", 0) for d in second_half) / len(second_half)
        
        pos_trend = avg_pos_second - avg_pos_first  # Negative = improving
        imp_trend = ((avg_imp_second - avg_imp_first) / avg_imp_first * 100) if avg_imp_first > 0 else 0
        
        return pos_trend, imp_trend
    
    # ==================== Traffic Loss Estimation ====================
    
    def _estimate_traffic_loss(self, pages: List[Dict]) -> int:
        """Estimate potential traffic loss from cannibalization"""
        
        if len(pages) < 2:
            return 0
        
        total_impressions = sum(p.get("impressions", 0) for p in pages)
        avg_ctr = sum(p.get("ctr", 0) for p in pages) / len(pages)
        
        # Estimate: If consolidated, would get 15-20% more clicks
        # due to stronger ranking and clearer signals
        estimated_additional_ctr = avg_ctr * 0.15
        estimated_loss = int(total_impressions * estimated_additional_ctr)
        
        return estimated_loss
    
    # ==================== Recommendation Generation ====================
    
    def _generate_recommendation(
        self,
        query: str,
        pages: List[CompetingPage],
        severity: CannibalizationSeverity,
        cann_type: CannibalizationType
    ) -> Tuple[str, RecommendedAction, str, List[str], str]:
        """Generate actionable recommendation"""
        
        if len(pages) < 2:
            return None, RecommendedAction.MONITOR, "", [], ""
        
        # Determine winner (best overall page)
        winner = self._determine_winner(pages)
        loser = pages[1] if pages[0] == winner else pages[0]
        
        # Generate recommendation based on type and severity
        if cann_type == CannibalizationType.CONTENT_DUPLICATE:
            action = RecommendedAction.MERGE_CONTENT
            details = f"Merge content from '{loser.page_url}' into '{winner.page_url}'"
            steps = [
                f"1. Review both pages: {winner.page_url} and {loser.page_url}",
                f"2. Copy unique sections from {loser.page_url} to {winner.page_url}",
                "3. Update internal links to point to the winner page",
                f"4. Set up 301 redirect from {loser.page_url} to {winner.page_url}",
                "5. Request re-indexing in Google Search Console"
            ]
            expected = f"Expected 20-30% increase in rankings for '{query}'"
        
        elif severity == CannibalizationSeverity.CRITICAL:
            action = RecommendedAction.REDIRECT_301
            details = f"Redirect '{loser.page_url}' to '{winner.page_url}'"
            steps = [
                f"1. Set up 301 redirect from {loser.page_url} to {winner.page_url}",
                "2. Update all internal links pointing to the redirected page",
                "3. Update sitemap to remove the redirected URL",
                "4. Request removal of old URL in GSC"
            ]
            expected = f"Expected immediate improvement in '{query}' rankings"
        
        elif severity == CannibalizationSeverity.HIGH:
            action = RecommendedAction.DIFFERENTIATE
            details = f"Differentiate content focus between pages"
            steps = [
                f"1. Choose a more specific keyword for {loser.page_url}",
                f"2. Rewrite title and meta description to target different intent",
                "3. Update H1 and main content to focus on the new keyword",
                f"4. Add internal link from {loser.page_url} to {winner.page_url}",
                "5. Monitor for 2-4 weeks"
            ]
            expected = f"Each page will rank for distinct keywords without competition"
        
        elif cann_type == CannibalizationType.URL_CONFLICT:
            action = RecommendedAction.CANONICAL
            details = f"Add canonical tag from '{loser.page_url}' to '{winner.page_url}'"
            steps = [
                f"1. Add <link rel='canonical' href='{winner.page_url}'> to {loser.page_url}",
                "2. Consider adding noindex if the loser page has minimal unique value",
                "3. Add internal link to strengthen the canonical signal"
            ]
            expected = "Google will consolidate ranking signals to the canonical page"
        
        else:
            action = RecommendedAction.INTERNAL_LINK
            details = f"Strengthen winner page with internal links"
            steps = [
                f"1. Add internal link from {loser.page_url} to {winner.page_url}",
                f"2. Use '{query}' or related term as anchor text",
                "3. Review other pages that could link to the winner",
                "4. Monitor rankings over 2-4 weeks"
            ]
            expected = "Gradual consolidation of ranking signals"
        
        return winner.page_url, action, details, steps, expected
    
    def _determine_winner(self, pages: List[CompetingPage]) -> CompetingPage:
        """Determine the best page to keep"""
        
        # Score each page
        scores = []
        for page in pages:
            score = 0
            
            # Clicks (most important)
            score += page.clicks * 3
            
            # Lower position is better (invert)
            score += max(0, 50 - page.position) * 2
            
            # Impressions
            score += page.impressions * 0.01
            
            # CTR
            score += page.ctr * 1000
            
            # Word count (longer = more comprehensive)
            score += page.word_count * 0.01
            
            # Internal links (more = more authority)
            score += page.internal_links_count * 5
            
            # Improving trend is better
            if page.position_trend < 0:
                score += 10
            
            scores.append((page, score))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[0][0]
    
    # ==================== Summary Generation ====================
    
    def _count_by_severity(self, issues: List[CannibalizationIssue]) -> Dict[str, int]:
        """Count issues by severity"""
        counts = {s.value: 0 for s in CannibalizationSeverity}
        for issue in issues:
            counts[issue.severity.value] += 1
        return counts
    
    def _calculate_health_score(
        self,
        issues: List[CannibalizationIssue],
        total_queries: int
    ) -> float:
        """Calculate overall cannibalization health score"""
        if total_queries == 0:
            return 100.0
        
        score = 100.0
        
        # Deduct based on issues
        for issue in issues:
            if issue.severity == CannibalizationSeverity.CRITICAL:
                score -= 15
            elif issue.severity == CannibalizationSeverity.HIGH:
                score -= 8
            elif issue.severity == CannibalizationSeverity.MEDIUM:
                score -= 4
            elif issue.severity == CannibalizationSeverity.LOW:
                score -= 1
        
        return max(0, min(100, score))
    
    def _generate_priorities(self, top_issues: List[CannibalizationIssue]) -> List[str]:
        """Generate priority list"""
        priorities = []
        for i, issue in enumerate(top_issues, 1):
            priority = (
                f"{i}. [{issue.severity.value.upper()}] '{issue.query}': "
                f"{issue.recommended_action.value.replace('_', ' ').title()} - "
                f"Est. traffic loss: {issue.estimated_traffic_loss}"
            )
            priorities.append(priority)
        return priorities
    
    def _generate_summary(
        self,
        issues: List[CannibalizationIssue],
        health_score: float
    ) -> str:
        """Generate human-readable summary"""
        
        if not issues:
            return "No significant cannibalization detected. Your content structure is healthy."
        
        critical = len([i for i in issues if i.severity == CannibalizationSeverity.CRITICAL])
        high = len([i for i in issues if i.severity == CannibalizationSeverity.HIGH])
        total_loss = sum(i.estimated_traffic_loss for i in issues)
        
        if critical > 0:
            return (
                f"⚠️ URGENT: {critical} critical cannibalization issues detected! "
                f"Estimated traffic loss: {total_loss}. "
                f"Health score: {round(health_score)}/100. "
                f"Immediate action required on {critical} critical and {high} high-priority issues."
            )
        elif high > 0:
            return (
                f"⚡ {high} high-priority cannibalization issues found. "
                f"Health score: {round(health_score)}/100. "
                f"Address these issues to recover an estimated {total_loss} potential clicks."
            )
        else:
            return (
                f"📊 {len(issues)} minor cannibalization issues detected. "
                f"Health score: {round(health_score)}/100. "
                f"Consider addressing for optimal performance."
            )
