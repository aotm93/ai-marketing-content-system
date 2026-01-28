"""
Backlink Copilot
Implements P3-4: Automated backlink opportunity discovery and outreach

Features:
- Brand mention detection (not linked)
- Resource page opportunity discovery
- Outreach email generation
- Status tracking
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class OpportunityType(str, Enum):
    """Types of backlink opportunities"""
    UNLINKED_MENTION = "unlinked_mention"  # Brand mentioned but not linked
    RESOURCE_PAGE = "resource_page"         # Resource/listicle page
    BROKEN_LINK = "broken_link"             # Broken link replacement
    COMPETITOR_BACKLINK = "competitor_backlink"  # Link to competitor
    GUEST_POST = "guest_post"               # Guest posting opportunity


class OutreachStatus(str, Enum):
    """Outreach campaign status"""
    DISCOVERED = "discovered"
    DRAFTED = "drafted"
    SENT = "sent"
    REPLIED = "replied"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    NO_RESPONSE = "no_response"


@dataclass
class BacklinkOpportunity:
    """Single backlink opportunity"""
    opportunity_id: str
    opportunity_type: OpportunityType
    target_url: str  # URL of page with opportunity
    target_domain: str
    
    # Opportunity details
    brand_mention: Optional[str] = None  # Text mentioning our brand
    anchor_text_suggestion: Optional[str] = None
    suggested_link_url: Optional[str] = None  # Our page to link to
    
    # Metrics
    domain_authority: Optional[int] = None  # 0-100
    page_authority: Optional[int] = None
    traffic_estimate: Optional[int] = None
    relevance_score: float = 0.0  # 0-100
    
    # Contact
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    
    # Status
    outreach_status: OutreachStatus = OutreachStatus.DISCOVERED
    discovered_at: datetime = field(default_factory=datetime.now)
    
    # Notes
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "opportunity_type": self.opportunity_type.value,
            "target_url": self.target_url,
            "target_domain": self.target_domain,
            "relevance_score": round(self.relevance_score, 1),
            "domain_authority": self.domain_authority,
            "outreach_status": self.outreach_status.value,
            "discovered_at": self.discovered_at.isoformat()
        }


class BacklinkDiscoveryEngine:
    """
    Backlink Opportunity Discovery
    
    Finds opportunities through:
    - Google search for brand mentions
    - Competitor backlink analysis
    - Resource page detection
    """
    
    def __init__(self, brand_names: List[str], website_url: str):
        self.brand_names = brand_names
        self.website_url = website_url
        self.opportunities: List[BacklinkOpportunity] = []
    
    async def find_unlinked_mentions(
        self,
        max_results: int = 50
    ) -> List[BacklinkOpportunity]:
        """
        Find pages mentioning brand but not linking
        
        Strategy:
        - Search: "brand name" -site:oursite.com
        - Check if page links to us
        - If not, create opportunity
        """
        opportunities = []
        
        for brand in self.brand_names:
            # In production, would use Google Custom Search API or similar
            # For demo, creating sample opportunities
            
            logger.info(f"Searching for unlinked mentions of: {brand}")
            
            # Placeholder: would make actual API calls
            sample_mentions = self._generate_sample_mentions(brand, max_results // len(self.brand_names))
            
            opportunities.extend(sample_mentions)
        
        self.opportunities.extend(opportunities)
        return opportunities
    
    def _generate_sample_mentions(self, brand: str, count: int) -> List[BacklinkOpportunity]:
        """Generate sample unlinked mentions (placeholder)"""
        import uuid
        
        opportunities = []
        
        for i in range(min(count, 5)):  # Limit to 5 samples
            opp = BacklinkOpportunity(
                opportunity_id=str(uuid.uuid4())[:8],
                opportunity_type=OpportunityType.UNLINKED_MENTION,
                target_url=f"https://example-blog-{i}.com/article-about-{brand.lower().replace(' ', '-')}",
                target_domain=f"example-blog-{i}.com",
                brand_mention=f"We recently tested {brand} and found it effective",
                suggested_link_url=self.website_url,
                domain_authority=40 + i * 5,
                relevance_score=60 + i * 5,
                outreach_status=OutreachStatus.DISCOVERED
            )
            opportunities.append(opp)
        
        return opportunities
    
    async def find_resource_pages(
        self,
        keywords: List[str],
        max_results: int = 30
    ) -> List[BacklinkOpportunity]:
        """
        Find resource/listicle pages in niche
        
        Search patterns:
        - "keyword + resources"
        - "keyword + links"
        - "best keyword tools"
        """
        opportunities = []
        
        for keyword in keywords:
            search_queries = [
                f"{keyword} resources",
                f"{keyword} tools list",
                f"best {keyword} websites"
            ]
            
            for query in search_queries:
                logger.info(f"Searching for resource pages: {query}")
                
                # Placeholder: would make actual searches
                sample_resources = self._generate_sample_resource_pages(keyword, max_results // len(keywords) // len(search_queries))
                opportunities.extend(sample_resources)
        
        self.opportunities.extend(opportunities)
        return opportunities
    
    def _generate_sample_resource_pages(self, keyword: str, count: int) -> List[BacklinkOpportunity]:
        """Generate sample resource pages (placeholder)"""
        import uuid
        
        opportunities = []
        
        for i in range(min(count, 3)):
            opp = BacklinkOpportunity(
                opportunity_id=str(uuid.uuid4())[:8],
                opportunity_type=OpportunityType.RESOURCE_PAGE,
                target_url=f"https://resource-site-{i}.com/best-{keyword.replace(' ', '-')}-tools",
                target_domain=f"resource-site-{i}.com",
                suggested_link_url=self.website_url,
                anchor_text_suggestion=f"Best {keyword} Solution",
                domain_authority=50 + i * 5,
                relevance_score=70 + i * 5,
                outreach_status=OutreachStatus.DISCOVERED
            )
            opportunities.append(opp)
        
        return opportunities
    
    def score_opportunity(self, opp: BacklinkOpportunity) -> float:
        """
        Score backlink opportunity (0-100)
        
        Factors:
        - Domain authority (40%)
        - Relevance (30%)
        - Traffic (20%)
        - Opportunity type (10%)
        """
        score = 0
        
        # Domain authority
        if opp.domain_authority:
            score += (opp.domain_authority / 100) * 40
        
        # Relevance
        score += (opp.relevance_score / 100) * 30
        
        # Traffic
        if opp.traffic_estimate:
            # Normalize to 0-100 scale (assume 10k = 100)
            traffic_score = min(opp.traffic_estimate / 10000 * 100, 100)
            score += (traffic_score / 100) * 20
        else:
            score += 10  # Default mid-range if unknown
        
        # Opportunity type bonus
        type_bonus = {
            OpportunityType.UNLINKED_MENTION: 10,
            OpportunityType.RESOURCE_PAGE: 8,
            OpportunityType.BROKEN_LINK: 9,
            OpportunityType.COMPETITOR_BACKLINK: 7,
            OpportunityType.GUEST_POST: 6
        }
        score += type_bonus.get(opp.opportunity_type, 5)
        
        return min(score, 100)
    
    def get_top_opportunities(
        self,
        count: int = 10,
        min_score: float = 50
    ) -> List[BacklinkOpportunity]:
        """Get top backlink opportunities"""
        # Score all opportunities
        for opp in self.opportunities:
            opp.relevance_score = self.score_opportunity(opp)
        
        # Filter and sort
        filtered = [o for o in self.opportunities if o.relevance_score >= min_score]
        filtered.sort(key=lambda o: o.relevance_score, reverse=True)
        
        return filtered[:count]


class OutreachGenerator:
    """
    Outreach Email Generator
    
    Generates personalized outreach emails for different opportunity types
    """
    
    # Email templates
    TEMPLATES = {
        OpportunityType.UNLINKED_MENTION: """
Subject: Quick question about your article on {article_topic}

Hi {contact_name},

I recently came across your article "{article_title}" and found it really valuable.

I noticed you mentioned {brand_name} in the piece. I'm reaching out from {our_company} to see if you'd be open to linking to our {relevant_page} when you mention us. It provides additional context that could be helpful for your readers.

Here's the link if you're interested: {link_url}

Thanks for considering, and keep up the great content!

Best regards,
{sender_name}
""",
        
        OpportunityType.RESOURCE_PAGE: """
Subject: Resource suggestion for "{article_title}"

Hi {contact_name},

I was browsing your excellent resource page "{article_title}" and thought it might be worth adding {our_product} to your list.

{our_product} is {value_proposition}. We've helped {social_proof}.

If you think it's a good fit, here's more information: {link_url}

Either way, thanks for curating such a helpful resource!

Best,
{sender_name}
""",
        
        OpportunityType.BROKEN_LINK: """
Subject: Broken link on "{article_title}"

Hi {contact_name},

I was reading your article "{article_title}" and noticed a broken link to {broken_url}.

I have a similar resource that might work as a replacement: {link_url}

It covers {topic} and could be helpful for your readers.

Let me know if you'd like to use it!

Thanks,
{sender_name}
"""
    }
    
    def generate_outreach_email(
        self,
        opportunity: BacklinkOpportunity,
        sender_name: str,
        company_name: str,
        custom_params: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate personalized outreach email
        
        Args:
            opportunity: Backlink opportunity
            sender_name: Name of sender
            company_name: Our company name
            custom_params: Additional template parameters
        """
        template = self.TEMPLATES.get(
            opportunity.opportunity_type,
            self.TEMPLATES[OpportunityType.UNLINKED_MENTION]
        )
        
        # Build parameters
        params = {
            "contact_name": opportunity.contact_name or "there",
            "brand_name": custom_params.get("brand_name", company_name) if custom_params else company_name,
            "our_company": company_name,
            "sender_name": sender_name,
            "link_url": opportunity.suggested_link_url or "",
            "article_topic": self._extract_topic(opportunity.target_url),
            "article_title": custom_params.get("article_title", "your article") if custom_params else "your article"
        }
        
        # Add custom params
        if custom_params:
            params.update(custom_params)
        
        # Generate email
        try:
            email = template.format(**params)
        except KeyError as e:
            logger.warning(f"Missing template parameter: {e}")
            email = template
        
        return email
    
    def _extract_topic(self, url: str) -> str:
        """Extract topic from URL"""
        # Simple extraction from URL path
        from urllib.parse import urlparse
        
        path = urlparse(url).path
        # Get last segment and clean it
        topic = path.rstrip('/').split('/')[-1]
        topic = topic.replace('-', ' ').replace('_', ' ').title()
        
        return topic or "your topic"


class OutreachTracker:
    """
    Outreach Campaign Tracker
    
    Tracks outreach status and responses
    """
    
    def __init__(self):
        self.campaigns: Dict[str, Dict[str, Any]] = {}
    
    def create_campaign(
        self,
        campaign_id: str,
        opportunity: BacklinkOpportunity,
        email_content: str
    ):
        """Create outreach campaign"""
        self.campaigns[campaign_id] = {
            "campaign_id": campaign_id,
            "opportunity_id": opportunity.opportunity_id,
            "target_domain": opportunity.target_domain,
            "target_url": opportunity.target_url,
            "email_content": email_content,
            "status": OutreachStatus.DRAFTED,
            "sent_at": None,
            "replied_at": None,
            "accepted_at": None,
            "follow_ups": [],
            "notes": []
        }
        
        logger.info(f"Campaign created: {campaign_id}")
    
    def mark_sent(self, campaign_id: str):
        """Mark campaign as sent"""
        if campaign_id in self.campaigns:
            self.campaigns[campaign_id]["status"] = OutreachStatus.SENT
            self.campaigns[campaign_id]["sent_at"] = datetime.now().isoformat()
            logger.info(f"Campaign sent: {campaign_id}")
    
    def mark_replied(self, campaign_id: str, reply_content: Optional[str] = None):
        """Mark campaign as replied"""
        if campaign_id in self.campaigns:
            self.campaigns[campaign_id]["status"] = OutreachStatus.REPLIED
            self.campaigns[campaign_id]["replied_at"] = datetime.now().isoformat()
            if reply_content:
                self.campaigns[campaign_id]["notes"].append({
                    "timestamp": datetime.now().isoformat(),
                    "content": reply_content
                })
            logger.info(f"Campaign replied: {campaign_id}")
    
    def mark_accepted(self, campaign_id: str):
        """Mark campaign as accepted"""
        if campaign_id in self.campaigns:
            self.campaigns[campaign_id]["status"] = OutreachStatus.ACCEPTED
            self.campaigns[campaign_id]["accepted_at"] = datetime.now().isoformat()
            logger.info(f"Campaign accepted: {campaign_id}")
    
    def get_campaign_stats(self) -> Dict[str, Any]:
        """Get campaign statistics"""
        total = len(self.campaigns)
        
        status_counts = {}
        for campaign in self.campaigns.values():
            status = campaign["status"].value if isinstance(campaign["status"], Enum) else campaign["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        accepted = status_counts.get(OutreachStatus.ACCEPTED.value, 0)
        sent = status_counts.get(OutreachStatus.SENT.value, 0)
        
        return {
            "total_campaigns": total,
            "status_breakdown": status_counts,
            "acceptance_rate": round(accepted / sent * 100, 2) if sent > 0 else 0,
            "sent_count": sent,
            "accepted_count": accepted
        }
