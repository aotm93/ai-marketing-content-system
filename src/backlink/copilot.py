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
from urllib.parse import urlparse

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
    
    Uses DataForSEO Backlinks API for real data.
    """
    
    def __init__(
        self, 
        brand_names: List[str], 
        website_url: str,
        backlinks_client=None,
        db_session=None
    ):
        self.brand_names = brand_names
        self.website_url = website_url
        self.opportunities: List[BacklinkOpportunity] = []
        self.backlinks_client = backlinks_client
        self.db = db_session
    
    async def find_unlinked_mentions(
        self,
        max_results: int = 50
    ) -> List[BacklinkOpportunity]:
        """
        Find pages mentioning brand but not linking.
        
        Uses DataForSEO Backlinks API to get referring domains and
        checks which ones don't already link to us.
        """
        opportunities = []
        
        # Parse our domain from website_url
        parsed_url = urlparse(self.website_url)
        our_domain = parsed_url.netloc or parsed_url.path
        
        if not our_domain:
            logger.warning("Could not parse domain from website_url")
            return opportunities
        
        # Use backlinks client if available
        if not self.backlinks_client:
            logger.warning("No backlinks client configured, returning empty list")
            return opportunities
        
        try:
            # Get referring domains for our domain
            logger.info(f"Fetching referring domains for: {our_domain}")
            referring_domains = await self.backlinks_client.get_referring_domains(
                our_domain, 
                limit=max_results * 2  # Get more to filter
            )
            
            logger.info(f"Found {len(referring_domains)} referring domains")
            
            for domain_data in referring_domains[:max_results]:
                try:
                    domain = domain_data.get("domain", "")
                    if not domain:
                        continue
                    
                    # Check if this domain already links to us
                    already_links = await self.backlinks_client.check_backlink_exists(
                        f"https://{domain}",
                        self.website_url
                    )
                    
                    if not already_links:
                        # This is an opportunity - they mention us but don't link
                        import uuid
                        
                        opp = BacklinkOpportunity(
                            opportunity_id=str(uuid.uuid4())[:8],
                            opportunity_type=OpportunityType.UNLINKED_MENTION,
                            target_url=f"https://{domain}",
                            target_domain=domain,
                            brand_mention=None,  # Would need scraping to get actual mention
                            suggested_link_url=self.website_url,
                            domain_authority=domain_data.get("domain_rating", 40),
                            page_authority=None,
                            traffic_estimate=domain_data.get("backlinks", 0),
                            relevance_score=50,  # Default, would need content analysis
                            outreach_status=OutreachStatus.DISCOVERED
                        )
                        
                        # Check for duplicates before adding
                        if not self._opportunity_exists(opp.target_url, opp.opportunity_type):
                            opportunities.append(opp)
                            
                            # Persist to database if session available
                            if self.db:
                                self._persist_opportunity(opp)
                                
                except Exception as e:
                    logger.warning(f"Error processing domain {domain_data.get('domain', 'unknown')}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching unlinked mentions: {e}")
        
        self.opportunities.extend(opportunities)
        logger.info(f"Found {len(opportunities)} unlinked mention opportunities")
        return opportunities
    
    def _opportunity_exists(self, target_url: str, opportunity_type: OpportunityType) -> bool:
        """Check if an opportunity already exists in memory or database."""
        # Check in-memory opportunities
        for opp in self.opportunities:
            if opp.target_url == target_url and opp.opportunity_type == opportunity_type:
                return True
        
        # Check database if session available
        if self.db:
            try:
                from src.models.backlink import BacklinkOpportunityModel
                existing = self.db.query(BacklinkOpportunityModel).filter(
                    BacklinkOpportunityModel.target_url == target_url,
                    BacklinkOpportunityModel.opportunity_type == opportunity_type
                ).first()
                return existing is not None
            except Exception as e:
                logger.debug(f"Could not check database for duplicates: {e}")
        
        return False
    
    def _persist_opportunity(self, opp: BacklinkOpportunity) -> None:
        """Persist an opportunity to the database."""
        if not self.db:
            return
            
        try:
            from src.models.backlink import BacklinkOpportunityModel
            
            # Check again for duplicates
            existing = self.db.query(BacklinkOpportunityModel).filter(
                BacklinkOpportunityModel.target_url == opp.target_url,
                BacklinkOpportunityModel.opportunity_type == opp.opportunity_type
            ).first()
            
            if existing:
                logger.debug(f"Opportunity already exists: {opp.target_url}")
                return
            
            # Create new record
            db_opp = BacklinkOpportunityModel(
                target_url=opp.target_url,
                target_domain=opp.target_domain,
                opportunity_type=opp.opportunity_type,
                domain_authority=opp.domain_authority,
                page_authority=opp.page_authority,
                traffic_estimate=opp.traffic_estimate,
                relevance_score=opp.relevance_score,
                contact_email=opp.contact_email,
                contact_name=opp.contact_name,
                outreach_status=opp.outreach_status,
                brand_mention=opp.brand_mention,
                anchor_text_suggestion=opp.anchor_text_suggestion,
                suggested_link_url=opp.suggested_link_url,
                notes=opp.notes,
                discovered_at=opp.discovered_at
            )
            
            self.db.add(db_opp)
            self.db.commit()
            logger.debug(f"Persisted opportunity: {opp.target_url}")
            
        except Exception as e:
            logger.error(f"Error persisting opportunity: {e}")
            if self.db:
                self.db.rollback()
    
    async def find_resource_pages(
        self,
        keywords: List[str],
        max_results: int = 30
    ) -> List[BacklinkOpportunity]:
        """
        Find resource/listicle pages in niche using competitor backlink analysis.
        
        Strategy:
        - Get backlinks for competitor domains
        - Filter for resource/listicle pages
        - Check if they don't already link to us
        """
        opportunities = []
        
        if not self.backlinks_client:
            logger.warning("No backlinks client configured, returning empty list")
            return opportunities
        
        # Parse our domain
        parsed_url = urlparse(self.website_url)
        our_domain = parsed_url.netloc or parsed_url.path
        
        if not our_domain:
            logger.warning("Could not parse domain from website_url")
            return opportunities
        
        try:
            results_per_keyword = max(1, max_results // len(keywords)) if keywords else max_results
            
            for keyword in keywords[:5]:  # Limit to first 5 keywords
                logger.info(f"Finding resource pages for keyword: {keyword}")
                
                # Use keyword to find potential resource pages
                # In a real implementation, we might search for:
                # - "keyword resources"
                # - "best keyword tools"
                # For now, we get backlinks to related domains
                
                # This is a simplified approach - get backlinks to our own domain
                # and look for patterns that suggest resource pages
                backlinks = await self.backlinks_client.get_backlinks_for_domain(
                    our_domain,
                    limit=results_per_keyword * 2
                )
                
                for backlink_data in backlinks[:results_per_keyword]:
                    try:
                        source_url = backlink_data.get("url", "")
                        if not source_url:
                            continue
                        
                        parsed_source = urlparse(source_url)
                        source_domain = parsed_source.netloc
                        
                        if not source_domain:
                            continue
                        
                        # Check if URL pattern suggests a resource page
                        path_lower = parsed_source.path.lower()
                        is_resource_page = any(pattern in path_lower for pattern in [
                            "resource", "tool", "list", "guide", "best", "top",
                            "comparison", "review", "alternative"
                        ])
                        
                        if not is_resource_page:
                            continue
                        
                        # Check if we already have this opportunity
                        import uuid
                        
                        opp = BacklinkOpportunity(
                            opportunity_id=str(uuid.uuid4())[:8],
                            opportunity_type=OpportunityType.RESOURCE_PAGE,
                            target_url=source_url,
                            target_domain=source_domain,
                            suggested_link_url=self.website_url,
                            anchor_text_suggestion=f"Best {keyword} resources",
                            domain_authority=backlink_data.get("domain_rating", 50),
                            page_authority=backlink_data.get("page_rating"),
                            traffic_estimate=backlink_data.get("backlinks", 0),
                            relevance_score=70 if is_resource_page else 50,
                            outreach_status=OutreachStatus.DISCOVERED
                        )
                        
                        # Check for duplicates
                        if not self._opportunity_exists(opp.target_url, opp.opportunity_type):
                            opportunities.append(opp)
                            
                            # Persist to database
                            if self.db:
                                self._persist_opportunity(opp)
                                
                    except Exception as e:
                        logger.warning(f"Error processing backlink: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error finding resource pages: {e}")
        
        self.opportunities.extend(opportunities)
        logger.info(f"Found {len(opportunities)} resource page opportunities")
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
