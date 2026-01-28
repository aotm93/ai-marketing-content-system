"""
Internal Link Agent
Implements P1-11, P1-12: InternalLinkAgent for automatic internal linking

Features:
- Context-aware link insertion
- Topic cluster-based linking
- Anchor text optimization
- Orphan page detection
- Hub-spoke structure maintenance
"""

import logging
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from bs4 import BeautifulSoup

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class LinkOpportunity:
    """Internal linking opportunity"""
    source_page: str
    target_page: str
    target_url: str
    anchor_text: str
    context: str  # Surrounding text
    position: str  # Location in content
    relevance_score: float  # 0-100
    link_type: str  # hub_to_spoke, spoke_to_hub, spoke_to_spoke, related
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_page": self.source_page,
            "target_page": self.target_page,
            "target_url": self.target_url,
            "anchor_text": self.anchor_text,
            "context": self.context,
            "position": self.position,
            "relevance_score": round(self.relevance_score, 1),
            "link_type": self.link_type
        }


@dataclass
class LinkingStrategy:
    """Internal linking strategy for a topic cluster"""
    cluster_id: str
    hub_page: str
    spoke_pages: List[str]
    link_opportunities: List[LinkOpportunity]
    orphan_pages: List[str]
    over_linked_pages: List[str]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "hub_page": self.hub_page,
            "spoke_count": len(self.spoke_pages),
            "link_opportunities": [o.to_dict() for o in self.link_opportunities],
            "orphan_pages": self.orphan_pages,
            "over_linked_pages": self.over_linked_pages,
            "recommendations": self.recommendations
        }


class InternalLinkAgent(BaseAgent):
    """
    Internal Link Agent
    
    Automatically identifies and creates internal linking opportunities:
    - Hub-spoke linking within topic clusters
    - Contextual related content links
    - Orphan page recovery
    - Link distribution optimization
    """
    
    # Link limits
    MAX_LINKS_PER_PAGE = 100
    MIN_LINKS_PER_PAGE = 3
    IDEAL_LINKS_PER_1000_WORDS = 5
    
    # Relevance thresholds
    MIN_RELEVANCE_SCORE = 50
    HIGH_RELEVANCE_THRESHOLD = 80
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute internal linking task"""
        task_type = task.get("type", "find_opportunities")
        
        if task_type == "find_opportunities":
            return await self._find_link_opportunities(task)
        elif task_type == "analyze_cluster":
            return await self._analyze_cluster_links(task)
        elif task_type == "insert_links":
            return await self._insert_links(task)
        elif task_type == "find_orphans":
            return await self._find_orphan_pages(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _find_link_opportunities(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find internal linking opportunities
        
        Task params:
            source_content: HTML content to analyze
            source_page: Source page URL
            source_keyword: Main keyword of source page
            available_pages: List of pages that can be linked to
            topic_cluster: Optional topic cluster info
        """
        source_content = task.get("source_content", "")
        source_page = task.get("source_page", "")
        source_keyword = task.get("source_keyword", "")
        available_pages = task.get("available_pages", [])
        topic_cluster = task.get("topic_cluster")
        
        if not source_content:
            return {"status": "error", "error": "Source content required"}
        
        logger.info(f"Finding link opportunities for: {source_page}")
        
        # Parse content
        soup = BeautifulSoup(source_content, 'html.parser')
        text_content = soup.get_text()
        
        # Extract existing links to avoid duplicates
        existing_links = self._extract_existing_links(soup)
        
        opportunities = []
        
        # 1. Topic cluster links (if applicable)
        if topic_cluster:
            cluster_opps = self._find_cluster_opportunities(
                soup, source_page, topic_cluster, existing_links
            )
            opportunities.extend(cluster_opps)
        
        # 2. Contextual links to available pages
        contextual_opps = self._find_contextual_opportunities(
            soup, text_content, source_page, available_pages, existing_links
        )
        opportunities.extend(contextual_opps)
        
        # Sort by relevance
        opportunities.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Limit to reasonable number
        max_new_links = self._calculate_max_links(len(text_content.split()), len(existing_links))
        top_opportunities = opportunities[:max_new_links]
        
        # Publish event
        await self.publish_event("link_opportunities_found", {
            "source_page": source_page,
            "opportunities_found": len(opportunities),
            "top_opportunities": len(top_opportunities)
        })
        
        return {
            "status": "success",
            "source_page": source_page,
            "existing_links_count": len(existing_links),
            "opportunities_found": len(opportunities),
            "top_opportunities": [o.to_dict() for o in top_opportunities],
            "recommended_links_to_add": len(top_opportunities)
        }
    
    def _extract_existing_links(self, soup: BeautifulSoup) -> List[str]:
        """Extract existing internal links"""
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Filter for internal links
            if not href.startswith('http') or 'yourdomain.com' in href:
                links.append(href)
        return links
    
    def _find_cluster_opportunities(
        self,
        soup: BeautifulSoup,
        source_page: str,
        topic_cluster: Dict[str, Any],
        existing_links: List[str]
    ) -> List[LinkOpportunity]:
        """Find linking opportunities within a topic cluster"""
        opportunities = []
        
        hub_url = topic_cluster.get("hub_url")
        hub_keyword = topic_cluster.get("hub_keyword", "")
        spoke_pages = topic_cluster.get("spoke_pages", [])
        
        # If this is a spoke page, link to hub
        if source_page != hub_url and hub_url not in existing_links:
            # Find best place to link to hub
            anchor_text = hub_keyword or "main guide"
            context, position = self._find_best_link_position(soup, hub_keyword)
            
            if context:
                opportunities.append(LinkOpportunity(
                    source_page=source_page,
                    target_page=hub_url,
                    target_url=hub_url,
                    anchor_text=anchor_text,
                    context=context,
                    position=position,
                    relevance_score=95,  # High relevance for cluster linking
                    link_type="spoke_to_hub"
                ))
        
        # If this is the hub, link to relevant spokes
        if source_page == hub_url:
            for spoke in spoke_pages[:5]:  # Limit to top 5 spokes
                spoke_url = spoke.get("url", "")
                spoke_keyword = spoke.get("keyword", "")
                
                if spoke_url not in existing_links:
                    context, position = self._find_best_link_position(soup, spoke_keyword)
                    if context:
                        opportunities.append(LinkOpportunity(
                            source_page=source_page,
                            target_page=spoke_url,
                            target_url=spoke_url,
                            anchor_text=spoke_keyword,
                            context=context,
                            position=position,
                            relevance_score=90,
                            link_type="hub_to_spoke"
                        ))
        
        return opportunities
    
    def _find_contextual_opportunities(
        self,
        soup: BeautifulSoup,
        text_content: str,
        source_page: str,
        available_pages: List[Dict],
        existing_links: List[str]
    ) -> List[LinkOpportunity]:
        """Find contextual linking opportunities"""
        opportunities = []
        
        for page in available_pages:
            target_url = page.get("url", "")
            target_keyword = page.get("keyword", "")
            target_title = page.get("title", "")
            
            # Skip if already linked
            if target_url in existing_links or target_url == source_page:
                continue
            
            # Calculate relevance
            relevance = self._calculate_relevance(text_content, target_keyword, target_title)
            
            if relevance < self.MIN_RELEVANCE_SCORE:
                continue
            
            # Find best anchor text and position
            anchor_text, context, position = self._find_best_anchor(
                soup, target_keyword, target_title
            )
            
            if context:
                opportunities.append(LinkOpportunity(
                    source_page=source_page,
                    target_page=target_title,
                    target_url=target_url,
                    anchor_text=anchor_text,
                    context=context,
                    position=position,
                    relevance_score=relevance,
                    link_type="related"
                ))
        
        return opportunities
    
    def _find_best_link_position(
        self,
        soup: BeautifulSoup,
        keyword: str
    ) -> Tuple[str, str]:
        """Find the best position to insert a link"""
        # Look for keyword mentions in content
        paragraphs = soup.find_all(['p', 'li'])
        
        for i, p in enumerate(paragraphs):
            text = p.get_text().lower()
            if keyword.lower() in text:
                # Found keyword mention - this is a good spot
                context = p.get_text()[:200]
                position = f"paragraph_{i}"
                return context, position
        
        # If no keyword found, suggest intro or early content
        if paragraphs:
            context = paragraphs[0].get_text()[:200] if paragraphs else ""
            return context, "intro"
        
        return "", "unknown"
    
    def _find_best_anchor(
        self,
        soup: BeautifulSoup,
        keyword: str,
        title: str
    ) -> Tuple[str, str, str]:
        """Find best anchor text and position for a link"""
        # Try exact keyword match first
        paragraphs = soup.find_all(['p', 'li'])
        
        keyword_lower = keyword.lower()
        
        for i, p in enumerate(paragraphs):
            text = p.get_text()
            text_lower = text.lower()
            
            # Look for exact keyword match
            if keyword_lower in text_lower:
                # Extract sentence containing keyword
                sentences = text.split('.')
                for sentence in sentences:
                    if keyword_lower in sentence.lower():
                        context = sentence.strip()[:200]
                        return keyword, context, f"paragraph_{i}"
        
        # Fallback to title-based anchor
        if paragraphs:
            context = paragraphs[0].get_text()[:200]
            return title[:50], context, "intro"
        
        return keyword, "", "unknown"
    
    def _calculate_relevance(
        self,
        source_text: str,
        target_keyword: str,
        target_title: str
    ) -> float:
        """Calculate relevance score between source and target"""
        source_lower = source_text.lower()
        keyword_lower = target_keyword.lower()
        
        score = 50  # Base score
        
        # Keyword presence
        keyword_count = source_lower.count(keyword_lower)
        if keyword_count > 0:
            score += min(keyword_count * 10, 30)
        
        # Title words presence
        title_words = set(target_title.lower().split())
        source_words = set(source_lower.split())
        overlap = len(title_words & source_words)
        
        if overlap > 0:
            score += min(overlap * 5, 20)
        
        return min(score, 100)
    
    def _calculate_max_links(self, word_count: int, existing_links: int) -> int:
        """Calculate maximum new links to add"""
        # Ideal: 5 links per 1000 words
        ideal_total = max(self.MIN_LINKS_PER_PAGE, int(word_count / 1000 * self.IDEAL_LINKS_PER_1000_WORDS))
        ideal_total = min(ideal_total, self.MAX_LINKS_PER_PAGE)
        
        max_new = max(0, ideal_total - existing_links)
        return min(max_new, 10)  # Cap at 10 new links per batch
    
    async def _analyze_cluster_links(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze internal linking health for a topic cluster
        
        Task params:
            cluster: Topic cluster data
            pages_content: Dict of page URLs to content
        """
        cluster = task.get("cluster", {})
        pages_content = task.get("pages_content", {})
        
        cluster_id = cluster.get("cluster_id", "")
        hub_url = cluster.get("hub_url", "")
        spoke_urls = cluster.get("spoke_urls", [])
        
        logger.info(f"Analyzing cluster links: {cluster_id}")
        
        # Analyze each page's linking
        hub_analysis = self._analyze_page_links(pages_content.get(hub_url, ""), hub_url)
        
        spoke_analyses = []
        orphan_pages = []
        
        for spoke_url in spoke_urls:
            content = pages_content.get(spoke_url, "")
            analysis = self._analyze_page_links(content, spoke_url)
            spoke_analyses.append(analysis)
            
            # Check if orphan (no links to it)
            is_orphan = not any(hub_url in a.get("outbound_links", []) for a in spoke_analyses)
            if is_orphan:
                orphan_pages.append(spoke_url)
        
        # Generate recommendations
        recommendations = []
        
        if orphan_pages:
            recommendations.append(f"Link {len(orphan_pages)} orphan pages to the hub")
        
        if hub_analysis.get("outbound_count", 0) < len(spoke_urls) * 0.5:
            recommendations.append("Add more links from hub to spoke pages")
        
        strategy = LinkingStrategy(
            cluster_id=cluster_id,
            hub_page=hub_url,
            spoke_pages=spoke_urls,
            link_opportunities=[],
            orphan_pages=orphan_pages,
            over_linked_pages=[],
            recommendations=recommendations
        )
        
        return {
            "status": "success",
            "cluster_id": cluster_id,
            "hub_analysis": hub_analysis,
            "spoke_count": len(spoke_urls),
            "orphan_count": len(orphan_pages),
            "strategy": strategy.to_dict()
        }
    
    def _analyze_page_links(self, content: str, page_url: str) -> Dict[str, Any]:
        """Analyze links on a single page"""
        if not content:
            return {
                "page_url": page_url,
                "has_content": False,
                "outbound_count": 0
            }
        
        soup = BeautifulSoup(content, 'html.parser')
        links = soup.find_all('a', href=True)
        
        internal_links = [a['href'] for a in links if not a['href'].startswith('http://') or 'yourdomain' in a['href']]
        external_links = [a['href'] for a in links if a['href'].startswith('http') and 'yourdomain' not in a['href']]
        
        word_count = len(soup.get_text().split())
        
        return {
            "page_url": page_url,
            "has_content": True,
            "word_count": word_count,
            "total_links": len(links),
            "internal_links": len(internal_links),
            "external_links": len(external_links),
            "outbound_links": internal_links[:10],  # Sample
            "link_density": round(len(internal_links) / max(word_count / 100, 1), 2)
        }
    
    async def _insert_links(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert internal links into content
        
        Task params:
            content: HTML content
            opportunities: List of link opportunities to apply
            post_id: WordPress post ID
        """
        content = task.get("content", "")
        opportunities = task.get("opportunities", [])
        post_id = task.get("post_id")
        
        if not content or not opportunities:
            return {"status": "error", "error": "Content and opportunities required"}
        
        soup = BeautifulSoup(content, 'html.parser')
        links_added = 0
        
        for opp in opportunities[:5]:  # Limit to top 5
            target_url = opp.get("target_url", "")
            anchor_text = opp.get("anchor_text", "")
            
            # Find the anchor text in content and wrap it with a link
            # This is simplified - production version would be more sophisticated
            paragraphs = soup.find_all('p')
            
            for p in paragraphs:
                text = p.get_text()
                if anchor_text.lower() in text.lower():
                    # Replace text with link
                    new_html = text.replace(
                        anchor_text,
                        f'<a href="{target_url}">{anchor_text}</a>',
                        1  # Only first occurrence
                    )
                    p.string = ''
                    p.append(BeautifulSoup(new_html, 'html.parser'))
                    links_added += 1
                    break
        
        updated_content = str(soup)
        
        return {
            "status": "success",
            "post_id": post_id,
            "links_added": links_added,
            "updated_content": updated_content
        }
    
    async def _find_orphan_pages(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find orphan pages (pages with no internal links pointing to them)
        
        Task params:
            all_pages: List of all pages
            sitemap_data: Optional sitemap data
        """
        all_pages = task.get("all_pages", [])
        
        # This would typically query the database for actual link data
        # For now, return placeholder
        
        orphans = []
        # Simplified logic - would check actual internal links in DB
        
        return {
            "status": "success",
            "total_pages": len(all_pages),
            "orphan_pages": orphans,
            "orphan_count": len(orphans)
        }
