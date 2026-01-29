"""
TopicMap Service
Implements BUG-008: Enhanced Topic Mapping with Hub-Spoke Structure

Features:
- Automatic Hub/Spoke relationship detection
- Intent-based page grouping (informational, commercial, transactional)
- Keyword cannibalization detection
- Smart internal link recommendations with semantic similarity
"""

import logging
import uuid
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from collections import defaultdict
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SearchIntent(str, Enum):
    """Search intent classification"""
    INFORMATIONAL = "informational"  # What, How, Why, Guide
    COMMERCIAL = "commercial"        # Best, Review, Compare, Top
    TRANSACTIONAL = "transactional"  # Buy, Order, Price, Discount
    NAVIGATIONAL = "navigational"    # Brand-specific
    

@dataclass
class SemanticPage:
    """Page with semantic analysis"""
    page_id: int
    url: str
    title: str
    keyword: str
    intent: SearchIntent
    word_count: int
    internal_links_in: int = 0
    internal_links_out: int = 0
    gsc_impressions: int = 0
    gsc_clicks: int = 0
    gsc_position: float = 0.0
    content_fingerprint: Optional[str] = None  # For similarity detection
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_id": self.page_id,
            "url": self.url,
            "title": self.title,
            "keyword": self.keyword,
            "intent": self.intent.value,
            "word_count": self.word_count,
            "internal_links_in": self.internal_links_in,
            "internal_links_out": self.internal_links_out,
            "gsc_impressions": self.gsc_impressions,
            "gsc_clicks": self.gsc_clicks,
            "gsc_position": round(self.gsc_position, 1)
        }


@dataclass
class CannibalizationIssue:
    """Keyword cannibalization detection"""
    query: str
    competing_pages: List[Dict[str, Any]]
    severity: str  # low, medium, high, critical
    estimated_traffic_loss: int
    recommendation: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "competing_pages": self.competing_pages,
            "severity": self.severity,
            "estimated_traffic_loss": self.estimated_traffic_loss,
            "recommendation": self.recommendation
        }


@dataclass
class SmartLinkRecommendation:
    """AI-powered link recommendation"""
    source_page_id: int
    source_url: str
    target_page_id: int
    target_url: str
    anchor_text: str
    relevance_score: float
    link_type: str  # hub_to_spoke, spoke_to_hub, semantic_related, intent_match
    reason: str
    priority: str  # low, medium, high
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_page_id": self.source_page_id,
            "source_url": self.source_url,
            "target_page_id": self.target_page_id,
            "target_url": self.target_url,
            "anchor_text": self.anchor_text,
            "relevance_score": round(self.relevance_score, 1),
            "link_type": self.link_type,
            "reason": self.reason,
            "priority": self.priority
        }


@dataclass
class TopicClusterAnalysis:
    """Complete topic cluster analysis"""
    cluster_id: str
    cluster_name: str
    hub_page: Optional[SemanticPage]
    spoke_pages: List[SemanticPage]
    intent_groups: Dict[str, List[SemanticPage]]
    orphan_pages: List[SemanticPage]
    cannibalization_issues: List[CannibalizationIssue]
    link_recommendations: List[SmartLinkRecommendation]
    health_score: float  # 0-100
    metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "cluster_name": self.cluster_name,
            "hub_page": self.hub_page.to_dict() if self.hub_page else None,
            "spoke_count": len(self.spoke_pages),
            "intent_groups": {k: [p.to_dict() for p in v] for k, v in self.intent_groups.items()},
            "orphan_count": len(self.orphan_pages),
            "cannibalization_count": len(self.cannibalization_issues),
            "recommendations_count": len(self.link_recommendations),
            "health_score": round(self.health_score, 1),
            "metrics": self.metrics
        }


class TopicMapService:
    """
    Enhanced TopicMap Service
    
    Core service for managing topic clusters, detecting cannibalization,
    and generating smart internal link recommendations.
    """
    
    # Intent detection keywords
    INTENT_SIGNALS = {
        SearchIntent.INFORMATIONAL: [
            "what is", "how to", "guide", "tutorial", "learn", "understanding",
            "tips", "steps", "basics", "introduction", "explained", "definition"
        ],
        SearchIntent.COMMERCIAL: [
            "best", "top", "review", "compare", "vs", "versus", "alternatives",
            "pros and cons", "buying guide", "which", "recommended"
        ],
        SearchIntent.TRANSACTIONAL: [
            "buy", "purchase", "price", "cost", "discount", "deal", "order",
            "shop", "cheap", "affordable", "for sale", "coupon"
        ],
        SearchIntent.NAVIGATIONAL: [
            "login", "sign in", "official", "website", "contact", "support"
        ]
    }
    
    # Similarity thresholds
    HIGH_SIMILARITY_THRESHOLD = 0.8
    CANNIBALIZATION_THRESHOLD = 0.7
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== Hub/Spoke Detection ====================
    
    def detect_hub_spoke_structure(
        self,
        pages: List[Dict[str, Any]],
        root_keyword: str
    ) -> Dict[str, Any]:
        """
        Automatically detect hub and spoke pages from a list of pages
        
        A Hub page is typically:
        - Longer content (pillar content)
        - Targets head keyword
        - Has more internal links
        - Higher impressions/broader topic
        
        Spoke pages are:
        - More focused/specific
        - Target long-tail keywords
        - Should link to hub
        """
        if not pages:
            return {"error": "No pages provided"}
        
        # Score each page for "hub potential"
        scored_pages = []
        
        for page in pages:
            hub_score = self._calculate_hub_score(page, root_keyword)
            scored_pages.append({
                "page": page,
                "hub_score": hub_score
            })
        
        # Sort by hub score
        scored_pages.sort(key=lambda x: x["hub_score"], reverse=True)
        
        # Top scorer is likely the hub
        hub_candidate = scored_pages[0]["page"] if scored_pages else None
        spoke_candidates = [sp["page"] for sp in scored_pages[1:]]
        
        # Verify hub has sufficient authority
        hub_verified = False
        if hub_candidate:
            hub_word_count = hub_candidate.get("word_count", 0)
            hub_impressions = hub_candidate.get("impressions", 0)
            
            # Hub should be substantial
            if hub_word_count >= 1500 or hub_impressions >= 500:
                hub_verified = True
        
        return {
            "status": "success",
            "hub_detected": hub_verified,
            "hub_page": hub_candidate if hub_verified else None,
            "hub_score": scored_pages[0]["hub_score"] if scored_pages else 0,
            "spoke_pages": spoke_candidates,
            "spoke_count": len(spoke_candidates),
            "recommendation": self._get_hub_recommendation(hub_verified, hub_candidate, spoke_candidates)
        }
    
    def _calculate_hub_score(self, page: Dict[str, Any], root_keyword: str) -> float:
        """Calculate how likely a page is to be a hub"""
        score = 0.0
        
        # Word count (longer = more likely hub)
        word_count = page.get("word_count", 0)
        if word_count >= 3000:
            score += 30
        elif word_count >= 2000:
            score += 20
        elif word_count >= 1500:
            score += 10
        
        # Keyword match (exact root keyword match = hub)
        page_keyword = page.get("keyword", "").lower()
        root_lower = root_keyword.lower()
        
        if page_keyword == root_lower:
            score += 25
        elif root_lower in page_keyword:
            score += 15
        elif page_keyword in root_lower:
            score += 10
        
        # Impressions (higher = more authoritative)
        impressions = page.get("impressions", 0)
        if impressions >= 10000:
            score += 25
        elif impressions >= 5000:
            score += 20
        elif impressions >= 1000:
            score += 15
        elif impressions >= 500:
            score += 10
        
        # Internal links out (hubs link to many spokes)
        links_out = page.get("internal_links_out", 0)
        if links_out >= 10:
            score += 15
        elif links_out >= 5:
            score += 10
        
        # Title indicators
        title = page.get("title", "").lower()
        hub_indicators = ["complete guide", "ultimate guide", "everything about", 
                         "comprehensive", "a to z", "101", "pillar"]
        for indicator in hub_indicators:
            if indicator in title:
                score += 10
                break
        
        return min(score, 100)
    
    def _get_hub_recommendation(
        self, 
        hub_verified: bool, 
        hub_candidate: Optional[Dict], 
        spokes: List[Dict]
    ) -> str:
        """Generate recommendation for hub/spoke structure"""
        if hub_verified:
            return f"Hub page identified. Link all {len(spokes)} spoke pages to the hub."
        elif hub_candidate:
            word_count = hub_candidate.get("word_count", 0)
            if word_count < 1500:
                return f"Potential hub needs expansion. Current: {word_count} words. Recommend: 2000+ words."
            return "Hub candidate needs more internal links from spoke pages."
        return "No clear hub. Consider creating a pillar content page."
    
    # ==================== Intent Classification ====================
    
    def classify_intent(self, keyword: str, title: str = "") -> SearchIntent:
        """Classify search intent from keyword and title"""
        text = f"{keyword} {title}".lower()
        
        # Score each intent
        intent_scores = defaultdict(int)
        
        for intent, signals in self.INTENT_SIGNALS.items():
            for signal in signals:
                if signal in text:
                    intent_scores[intent] += 1
        
        if intent_scores:
            best_intent = max(intent_scores.keys(), key=lambda k: intent_scores[k])
            return best_intent
        
        # Default to informational
        return SearchIntent.INFORMATIONAL
    
    def group_pages_by_intent(
        self, 
        pages: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group pages by their search intent"""
        groups = {
            SearchIntent.INFORMATIONAL.value: [],
            SearchIntent.COMMERCIAL.value: [],
            SearchIntent.TRANSACTIONAL.value: [],
            SearchIntent.NAVIGATIONAL.value: []
        }
        
        for page in pages:
            keyword = page.get("keyword", "")
            title = page.get("title", "")
            intent = self.classify_intent(keyword, title)
            groups[intent.value].append(page)
        
        return groups
    
    # ==================== Cannibalization Detection ====================
    
    def detect_cannibalization(
        self,
        gsc_data: List[Dict[str, Any]],
        min_impressions: int = 100
    ) -> List[CannibalizationIssue]:
        """
        Detect keyword cannibalization from GSC data
        
        Cannibalization occurs when multiple pages compete for the same query,
        causing confusion for search engines and diluted rankings.
        """
        issues = []
        
        # Group by query
        query_pages = defaultdict(list)
        
        for row in gsc_data:
            query = row.get("query", "")
            impressions = row.get("impressions", 0)
            
            if impressions >= min_impressions:
                query_pages[query].append({
                    "page": row.get("page", ""),
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "position": row.get("position", 0),
                    "ctr": row.get("ctr", 0)
                })
        
        # Find queries with multiple pages
        for query, pages in query_pages.items():
            if len(pages) >= 2:
                # Sort by impressions
                pages.sort(key=lambda x: x["impressions"], reverse=True)
                
                # Check if it's true cannibalization
                issue = self._analyze_cannibalization(query, pages)
                if issue:
                    issues.append(issue)
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        issues.sort(key=lambda x: severity_order.get(x.severity, 4))
        
        return issues
    
    def _analyze_cannibalization(
        self, 
        query: str, 
        pages: List[Dict[str, Any]]
    ) -> Optional[CannibalizationIssue]:
        """Analyze if multiple pages are truly cannibalizing each other"""
        if len(pages) < 2:
            return None
        
        # Get top 2 pages
        page1, page2 = pages[0], pages[1]
        
        # Both pages should have significant impressions
        if page2["impressions"] < page1["impressions"] * 0.2:
            # Secondary page has very low impressions - not true cannibalization
            return None
        
        # Calculate severity
        total_impressions = sum(p["impressions"] for p in pages)
        position_variance = abs(page1["position"] - page2["position"])
        
        # Estimate traffic loss (rough calculation)
        # If pages were consolidated, position would improve
        estimated_loss = int(total_impressions * 0.1)  # Conservative 10% loss
        
        if position_variance < 3 and total_impressions > 1000:
            severity = "critical"
            estimated_loss = int(total_impressions * 0.2)
        elif position_variance < 5:
            severity = "high"
            estimated_loss = int(total_impressions * 0.15)
        elif len(pages) >= 3:
            severity = "medium"
        else:
            severity = "low"
        
        # Generate recommendation
        recommendation = self._get_cannibalization_recommendation(
            query, pages, page1, page2, severity
        )
        
        return CannibalizationIssue(
            query=query,
            competing_pages=pages[:5],  # Top 5
            severity=severity,
            estimated_traffic_loss=estimated_loss,
            recommendation=recommendation
        )
    
    def _get_cannibalization_recommendation(
        self,
        query: str,
        pages: List[Dict],
        primary: Dict,
        secondary: Dict,
        severity: str
    ) -> str:
        """Generate recommendation for fixing cannibalization"""
        if severity == "critical":
            return (
                f"URGENT: Merge content from '{secondary['page']}' into '{primary['page']}' "
                f"and redirect. Potential to recover {int(sum(p['impressions'] for p in pages) * 0.15)} impressions."
            )
        elif severity == "high":
            return (
                f"Differentiate content: Make '{primary['page']}' the definitive page for '{query}'. "
                f"Consider redirecting or re-targeting '{secondary['page']}' to a related query."
            )
        elif severity == "medium":
            return (
                f"Add internal links from secondary pages to '{primary['page']}' "
                f"to consolidate authority for '{query}'."
            )
        else:
            return (
                f"Monitor closely. Current pages may be serving different intents. "
                f"Consider adding canonical tags if overlap persists."
            )
    
    # ==================== Smart Link Recommendations ====================
    
    def generate_smart_recommendations(
        self,
        cluster_pages: List[Dict[str, Any]],
        hub_page: Optional[Dict[str, Any]] = None,
        existing_links: Optional[List[Tuple[int, int]]] = None
    ) -> List[SmartLinkRecommendation]:
        """
        Generate intelligent internal link recommendations
        
        Uses multiple signals:
        - Hub/Spoke structure (structural linking)
        - Intent matching (link similar intent pages)
        - Semantic relatedness (keyword/topic overlap)
        - GSC performance (link to high-performing pages)
        """
        recommendations = []
        existing_links = existing_links or []
        existing_set = set(existing_links)
        
        # 1. Hub-Spoke links (highest priority)
        if hub_page:
            hub_recs = self._generate_hub_spoke_recommendations(
                hub_page, cluster_pages, existing_set
            )
            recommendations.extend(hub_recs)
        
        # 2. Intent-based links
        intent_groups = self.group_pages_by_intent(cluster_pages)
        intent_recs = self._generate_intent_recommendations(
            intent_groups, existing_set
        )
        recommendations.extend(intent_recs)
        
        # 3. Performance-based links
        perf_recs = self._generate_performance_recommendations(
            cluster_pages, existing_set
        )
        recommendations.extend(perf_recs)
        
        # Deduplicate
        seen = set()
        unique_recs = []
        for rec in recommendations:
            key = (rec.source_page_id, rec.target_page_id)
            if key not in seen:
                seen.add(key)
                unique_recs.append(rec)
        
        # Sort by priority and relevance
        priority_order = {"high": 0, "medium": 1, "low": 2}
        unique_recs.sort(
            key=lambda x: (priority_order.get(x.priority, 3), -x.relevance_score)
        )
        
        return unique_recs[:20]  # Top 20 recommendations
    
    def _generate_hub_spoke_recommendations(
        self,
        hub_page: Dict[str, Any],
        spoke_pages: List[Dict[str, Any]],
        existing: set
    ) -> List[SmartLinkRecommendation]:
        """Generate hub to spoke and spoke to hub recommendations"""
        recs = []
        hub_id = hub_page.get("page_id", 0)
        hub_url = hub_page.get("url", "")
        hub_keyword = hub_page.get("keyword", "")
        
        for spoke in spoke_pages:
            spoke_id = spoke.get("page_id", 0)
            spoke_url = spoke.get("url", "")
            spoke_keyword = spoke.get("keyword", "")
            
            if spoke_id == hub_id:
                continue
            
            # Spoke -> Hub (always recommended)
            if (spoke_id, hub_id) not in existing:
                recs.append(SmartLinkRecommendation(
                    source_page_id=spoke_id,
                    source_url=spoke_url,
                    target_page_id=hub_id,
                    target_url=hub_url,
                    anchor_text=hub_keyword or "main guide",
                    relevance_score=95,
                    link_type="spoke_to_hub",
                    reason="Essential hub link for topic cluster structure",
                    priority="high"
                ))
            
            # Hub -> Spoke (for top spokes)
            if (hub_id, spoke_id) not in existing:
                spoke_impressions = spoke.get("impressions", 0)
                priority = "high" if spoke_impressions > 500 else "medium"
                
                recs.append(SmartLinkRecommendation(
                    source_page_id=hub_id,
                    source_url=hub_url,
                    target_page_id=spoke_id,
                    target_url=spoke_url,
                    anchor_text=spoke_keyword,
                    relevance_score=90,
                    link_type="hub_to_spoke",
                    reason=f"Link to spoke page ({spoke_impressions} impressions)",
                    priority=priority
                ))
        
        return recs
    
    def _generate_intent_recommendations(
        self,
        intent_groups: Dict[str, List[Dict]],
        existing: set
    ) -> List[SmartLinkRecommendation]:
        """Generate recommendations based on intent matching"""
        recs = []
        
        # Link informational to commercial (natural user journey)
        info_pages = intent_groups.get(SearchIntent.INFORMATIONAL.value, [])
        comm_pages = intent_groups.get(SearchIntent.COMMERCIAL.value, [])
        
        for info_page in info_pages[:5]:
            for comm_page in comm_pages[:3]:
                info_id = info_page.get("page_id", 0)
                comm_id = comm_page.get("page_id", 0)
                
                if (info_id, comm_id) not in existing:
                    recs.append(SmartLinkRecommendation(
                        source_page_id=info_id,
                        source_url=info_page.get("url", ""),
                        target_page_id=comm_id,
                        target_url=comm_page.get("url", ""),
                        anchor_text=comm_page.get("keyword", ""),
                        relevance_score=75,
                        link_type="intent_match",
                        reason="Informational → Commercial user journey",
                        priority="medium"
                    ))
        
        # Link commercial to transactional
        trans_pages = intent_groups.get(SearchIntent.TRANSACTIONAL.value, [])
        
        for comm_page in comm_pages[:5]:
            for trans_page in trans_pages[:3]:
                comm_id = comm_page.get("page_id", 0)
                trans_id = trans_page.get("page_id", 0)
                
                if (comm_id, trans_id) not in existing:
                    recs.append(SmartLinkRecommendation(
                        source_page_id=comm_id,
                        source_url=comm_page.get("url", ""),
                        target_page_id=trans_id,
                        target_url=trans_page.get("url", ""),
                        anchor_text=trans_page.get("keyword", ""),
                        relevance_score=80,
                        link_type="intent_match",
                        reason="Commercial → Transactional conversion path",
                        priority="medium"
                    ))
        
        return recs
    
    def _generate_performance_recommendations(
        self,
        pages: List[Dict[str, Any]],
        existing: set
    ) -> List[SmartLinkRecommendation]:
        """Generate recommendations to boost high-impression/low-click pages"""
        recs = []
        
        # Find pages with high impressions but low CTR
        underperforming = []
        high_performers = []
        
        for page in pages:
            impressions = page.get("impressions", 0)
            ctr = page.get("ctr", 0)
            
            if impressions > 1000 and ctr < 0.02:  # High impressions, low CTR
                underperforming.append(page)
            elif impressions > 500 and ctr > 0.05:  # Good performers
                high_performers.append(page)
        
        # Link from high performers to underperformers (authority boost)
        for high_page in high_performers[:3]:
            for under_page in underperforming[:3]:
                high_id = high_page.get("page_id", 0)
                under_id = under_page.get("page_id", 0)
                
                if high_id != under_id and (high_id, under_id) not in existing:
                    recs.append(SmartLinkRecommendation(
                        source_page_id=high_id,
                        source_url=high_page.get("url", ""),
                        target_page_id=under_id,
                        target_url=under_page.get("url", ""),
                        anchor_text=under_page.get("keyword", ""),
                        relevance_score=70,
                        link_type="semantic_related",
                        reason=f"Boost underperforming page ({under_page.get('impressions', 0)} impressions, {round(under_page.get('ctr', 0)*100, 1)}% CTR)",
                        priority="low"
                    ))
        
        return recs
    
    # ==================== Full Cluster Analysis ====================
    
    async def analyze_cluster(
        self,
        cluster_name: str,
        pages: List[Dict[str, Any]],
        gsc_data: Optional[List[Dict[str, Any]]] = None,
        root_keyword: Optional[str] = None
    ) -> TopicClusterAnalysis:
        """
        Perform complete topic cluster analysis
        
        This is the main entry point that combines all features:
        - Hub/Spoke detection
        - Intent grouping
        - Cannibalization detection
        - Smart recommendations
        """
        cluster_id = str(uuid.uuid4())[:8]
        
        logger.info(f"Analyzing cluster: {cluster_name} with {len(pages)} pages")
        
        # 1. Detect Hub/Spoke structure
        hub_result = self.detect_hub_spoke_structure(
            pages, 
            root_keyword or cluster_name
        )
        
        hub_page = None
        spoke_pages = []
        
        if hub_result.get("hub_detected"):
            hub_data = hub_result.get("hub_page", {})
            hub_page = SemanticPage(
                page_id=hub_data.get("page_id", 0),
                url=hub_data.get("url", ""),
                title=hub_data.get("title", ""),
                keyword=hub_data.get("keyword", ""),
                intent=self.classify_intent(hub_data.get("keyword", ""), hub_data.get("title", "")),
                word_count=hub_data.get("word_count", 0),
                internal_links_out=hub_data.get("internal_links_out", 0),
                gsc_impressions=hub_data.get("impressions", 0),
                gsc_clicks=hub_data.get("clicks", 0),
                gsc_position=hub_data.get("position", 0)
            )
            
            for sp in hub_result.get("spoke_pages", []):
                spoke_pages.append(SemanticPage(
                    page_id=sp.get("page_id", 0),
                    url=sp.get("url", ""),
                    title=sp.get("title", ""),
                    keyword=sp.get("keyword", ""),
                    intent=self.classify_intent(sp.get("keyword", ""), sp.get("title", "")),
                    word_count=sp.get("word_count", 0),
                    gsc_impressions=sp.get("impressions", 0),
                    gsc_clicks=sp.get("clicks", 0),
                    gsc_position=sp.get("position", 0)
                ))
        
        # 2. Group by intent
        intent_groups = {}
        all_semantic_pages = spoke_pages + ([hub_page] if hub_page else [])
        
        for intent in SearchIntent:
            intent_groups[intent.value] = [
                p for p in all_semantic_pages if p.intent == intent
            ]
        
        # 3. Find orphan pages (no inbound links and not the hub)
        orphan_pages = [
            p for p in spoke_pages 
            if p.internal_links_in == 0
        ]
        
        # 4. Detect cannibalization
        cannibalization_issues = []
        if gsc_data:
            cannibalization_issues = self.detect_cannibalization(gsc_data)
        
        # 5. Generate smart recommendations
        link_recommendations = self.generate_smart_recommendations(
            pages,
            hub_result.get("hub_page") if hub_result.get("hub_detected") else None
        )
        
        # 6. Calculate health score
        health_score = self._calculate_cluster_health(
            hub_page=hub_page,
            spoke_pages=spoke_pages,
            orphan_pages=orphan_pages,
            cannibalization_issues=cannibalization_issues
        )
        
        # 7. Compile metrics
        metrics = {
            "total_pages": len(pages),
            "hub_detected": hub_page is not None,
            "spoke_count": len(spoke_pages),
            "orphan_count": len(orphan_pages),
            "cannibalization_count": len(cannibalization_issues),
            "recommendations_count": len(link_recommendations),
            "total_impressions": sum(p.gsc_impressions for p in all_semantic_pages),
            "total_clicks": sum(p.gsc_clicks for p in all_semantic_pages),
            "avg_position": (
                sum(p.gsc_position for p in all_semantic_pages) / len(all_semantic_pages)
                if all_semantic_pages else 0
            ),
            "intent_distribution": {
                k: len(v) for k, v in intent_groups.items()
            }
        }
        
        return TopicClusterAnalysis(
            cluster_id=cluster_id,
            cluster_name=cluster_name,
            hub_page=hub_page,
            spoke_pages=spoke_pages,
            intent_groups=intent_groups,
            orphan_pages=orphan_pages,
            cannibalization_issues=cannibalization_issues,
            link_recommendations=link_recommendations,
            health_score=health_score,
            metrics=metrics
        )
    
    def _calculate_cluster_health(
        self,
        hub_page: Optional[SemanticPage],
        spoke_pages: List[SemanticPage],
        orphan_pages: List[SemanticPage],
        cannibalization_issues: List[CannibalizationIssue]
    ) -> float:
        """Calculate overall cluster health score (0-100)"""
        score = 100.0
        
        # No hub = major issue
        if not hub_page:
            score -= 30
        
        # Orphan penalty
        if spoke_pages:
            orphan_ratio = len(orphan_pages) / len(spoke_pages)
            score -= orphan_ratio * 25
        
        # Cannibalization penalty
        for issue in cannibalization_issues:
            if issue.severity == "critical":
                score -= 15
            elif issue.severity == "high":
                score -= 10
            elif issue.severity == "medium":
                score -= 5
            else:
                score -= 2
        
        # Bonus for good structure
        if hub_page and len(spoke_pages) >= 5:
            score += 5  # Good cluster size
        
        return max(0, min(100, score))
