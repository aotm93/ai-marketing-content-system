"""
Google Search Console Integration
Implements P1-1, P1-2: GSC OAuth/Service Account access and data retrieval

Features:
- Service Account authentication (recommended for automation)
- OAuth2 authentication (for manual setup)
- Query/Page performance data retrieval
- Automatic data sync to database
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    service_account = None
    build = None

logger = logging.getLogger(__name__)


class GSCAuthMethod(str, Enum):
    """Authentication method for GSC"""
    SERVICE_ACCOUNT = "service_account"
    OAUTH = "oauth"


@dataclass
class GSCQuery:
    """
    Google Search Console query data
    
    Represents performance data for a query/page combination
    """
    date: str
    query: str
    page: str
    country: Optional[str] = None
    device: Optional[str] = None
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    position: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "query": self.query,
            "page": self.page,
            "country": self.country,
            "device": self.device,
            "clicks": self.clicks,
            "impressions": self.impressions,
            "ctr": round(self.ctr * 100, 2),  # Convert to percentage
            "position": round(self.position, 1)
        }
    
    @property
    def is_low_hanging_fruit(self) -> bool:
        """Check if this is a low-hanging fruit opportunity"""
        # High impressions but position 4-20 = opportunity
        return self.impressions >= 100 and 4 <= self.position <= 20


@dataclass 
class GSCSyncResult:
    """Result of a GSC data sync operation"""
    success: bool
    rows_fetched: int = 0
    rows_stored: int = 0
    date_range: Optional[str] = None
    error: Optional[str] = None
    sync_time: datetime = field(default_factory=datetime.now)


class GSCClient:
    """
    Google Search Console API Client
    
    Supports both Service Account (for automation) and OAuth (for manual setup)
    """
    
    # API scopes
    SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
    
    def __init__(
        self,
        site_url: str,
        auth_method: GSCAuthMethod = GSCAuthMethod.SERVICE_ACCOUNT,
        credentials_path: Optional[str] = None,
        credentials_json: Optional[str] = None
    ):
        """
        Initialize GSC client
        
        Args:
            site_url: The site URL in GSC (e.g., 'https://example.com/' or 'sc-domain:example.com')
            auth_method: Authentication method to use
            credentials_path: Path to credentials JSON file
            credentials_json: Credentials as JSON string (for env vars)
        """
        if not GOOGLE_API_AVAILABLE:
            raise ImportError(
                "Google API libraries not installed. "
                "Install with: pip install google-api-python-client google-auth-oauthlib"
            )
        
        self.site_url = site_url
        self.auth_method = auth_method
        self._service = None
        self._credentials = None
        
        # Initialize credentials
        if auth_method == GSCAuthMethod.SERVICE_ACCOUNT:
            self._init_service_account(credentials_path, credentials_json)
        else:
            self._init_oauth(credentials_path)
        
        logger.info(f"GSC client initialized for {site_url}")
    
    def _init_service_account(self, credentials_path: Optional[str], credentials_json: Optional[str]):
        """Initialize with Service Account credentials"""
        try:
            if credentials_json:
                info = json.loads(credentials_json)
                self._credentials = service_account.Credentials.from_service_account_info(
                    info, scopes=self.SCOPES
                )
            elif credentials_path:
                self._credentials = service_account.Credentials.from_service_account_file(
                    credentials_path, scopes=self.SCOPES
                )
            else:
                raise ValueError("Either credentials_path or credentials_json required")
            
            self._service = build('searchconsole', 'v1', credentials=self._credentials)
            logger.info("GSC Service Account authentication successful")
            
        except Exception as e:
            logger.error(f"GSC Service Account auth failed: {e}")
            raise
    
    def _init_oauth(self, credentials_path: Optional[str]):
        """Initialize with OAuth credentials"""
        # OAuth would require user interaction - placeholder
        logger.warning("OAuth authentication requires user interaction - not fully implemented")
        raise NotImplementedError("OAuth flow requires interactive setup")
    
    def get_search_analytics(
        self,
        start_date: str,
        end_date: str,
        dimensions: List[str] = None,
        row_limit: int = 25000,
        start_row: int = 0,
        filters: List[Dict] = None
    ) -> List[GSCQuery]:
        """
        Get search analytics data from GSC
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            dimensions: Dimensions to include (query, page, country, device, date)
            row_limit: Maximum rows to return (max 25000)
            start_row: Starting row for pagination
            filters: Optional dimension filters
            
        Returns:
            List of GSCQuery objects
        """
        if not self._service:
            raise RuntimeError("GSC service not initialized")
        
        dimensions = dimensions or ['query', 'page']
        
        request_body = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': dimensions,
            'rowLimit': min(row_limit, 25000),
            'startRow': start_row,
            'dataState': 'final'  # Use finalized data
        }
        
        if filters:
            request_body['dimensionFilterGroups'] = [{
                'filters': filters
            }]
        
        try:
            response = self._service.searchanalytics().query(
                siteUrl=self.site_url,
                body=request_body
            ).execute()
            
            rows = response.get('rows', [])
            logger.info(f"Retrieved {len(rows)} rows from GSC")
            
            queries = []
            for row in rows:
                keys = row.get('keys', [])
                
                # Parse dimensions based on requested dimensions
                query_data = {}
                for i, dim in enumerate(dimensions):
                    if i < len(keys):
                        query_data[dim] = keys[i]
                
                queries.append(GSCQuery(
                    date=query_data.get('date', start_date),
                    query=query_data.get('query', ''),
                    page=query_data.get('page', ''),
                    country=query_data.get('country'),
                    device=query_data.get('device'),
                    clicks=row.get('clicks', 0),
                    impressions=row.get('impressions', 0),
                    ctr=row.get('ctr', 0.0),
                    position=row.get('position', 0.0)
                ))
            
            return queries
            
        except Exception as e:
            logger.error(f"GSC query failed: {e}")
            raise
    
    def get_low_hanging_fruits(
        self,
        days: int = 28,
        min_impressions: int = 100,
        position_min: float = 4.0,
        position_max: float = 20.0,
        limit: int = 100
    ) -> List[GSCQuery]:
        """
        Get low-hanging fruit opportunities
        
        These are queries with:
        - High impressions (visibility)
        - Position 4-20 (on page 1-2, room to improve)
        
        Args:
            days: Number of days to analyze
            min_impressions: Minimum impressions threshold
            position_min: Minimum position (closer to 1 = higher rank)
            position_max: Maximum position
            limit: Max results to return
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Get all query data
        queries = self.get_search_analytics(
            start_date=start_date,
            end_date=end_date,
            dimensions=['query', 'page'],
            row_limit=25000
        )
        
        # Filter for low-hanging fruits
        opportunities = [
            q for q in queries
            if q.impressions >= min_impressions
            and position_min <= q.position <= position_max
        ]
        
        # Sort by potential (impressions * (20 - position) as proxy for opportunity)
        opportunities.sort(
            key=lambda x: x.impressions * (20 - x.position),
            reverse=True
        )
        
        return opportunities[:limit]
    
    def get_declining_pages(
        self,
        compare_days: int = 28,
        decline_threshold: float = 0.2  # 20% decline
    ) -> List[Dict[str, Any]]:
        """
        Find pages with declining performance
        
        Compares recent period with previous period to identify
        pages that need content refresh
        """
        now = datetime.now()
        
        # Recent period
        recent_end = now.strftime('%Y-%m-%d')
        recent_start = (now - timedelta(days=compare_days)).strftime('%Y-%m-%d')
        
        # Previous period
        prev_end = (now - timedelta(days=compare_days)).strftime('%Y-%m-%d')
        prev_start = (now - timedelta(days=compare_days * 2)).strftime('%Y-%m-%d')
        
        # Get data for both periods
        recent_data = self.get_search_analytics(
            start_date=recent_start,
            end_date=recent_end,
            dimensions=['page']
        )
        
        prev_data = self.get_search_analytics(
            start_date=prev_start,
            end_date=prev_end,
            dimensions=['page']
        )
        
        # Create lookup for previous data
        prev_lookup = {q.page: q for q in prev_data}
        
        declining = []
        for current in recent_data:
            prev = prev_lookup.get(current.page)
            if not prev:
                continue
            
            # Calculate click decline
            if prev.clicks > 0:
                click_change = (current.clicks - prev.clicks) / prev.clicks
                if click_change < -decline_threshold:
                    declining.append({
                        'page': current.page,
                        'current_clicks': current.clicks,
                        'previous_clicks': prev.clicks,
                        'change_percent': round(click_change * 100, 1),
                        'current_position': current.position,
                        'previous_position': prev.position,
                        'position_change': round(current.position - prev.position, 1)
                    })
        
        # Sort by severity of decline
        declining.sort(key=lambda x: x['change_percent'])
        
        return declining
    
    def health_check(self) -> Dict[str, Any]:
        """Check GSC connection status"""
        try:
            # Try to list sites to verify connection
            sites = self._service.sites().list().execute()
            site_list = sites.get('siteEntry', [])
            
            # Check if our site is in the list
            site_found = any(s.get('siteUrl') == self.site_url for s in site_list)
            
            return {
                'status': 'connected' if site_found else 'site_not_found',
                'site_url': self.site_url,
                'accessible_sites': [s.get('siteUrl') for s in site_list],
                'permission_level': next(
                    (s.get('permissionLevel') for s in site_list if s.get('siteUrl') == self.site_url),
                    None
                )
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }


class GSCDataSync:
    """
    GSC Data Synchronization Service
    
    Handles periodic sync of GSC data to local database
    """
    
    def __init__(self, gsc_client: GSCClient, db_session=None):
        self.client = gsc_client
        self.db_session = db_session
        self._last_sync: Optional[datetime] = None
    
    async def sync_queries(
        self,
        days_back: int = 28,
        dimensions: List[str] = None
    ) -> GSCSyncResult:
        """
        Sync GSC query data to database
        
        Args:
            days_back: Number of days to sync
            dimensions: Dimensions to include
        """
        dimensions = dimensions or ['query', 'page', 'date']
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        try:
            queries = self.client.get_search_analytics(
                start_date=start_date,
                end_date=end_date,
                dimensions=dimensions
            )
            
            # Store in database (implementation depends on your ORM setup)
            stored = 0
            if self.db_session:
                stored = await self._store_queries(queries)
            
            self._last_sync = datetime.now()
            
            return GSCSyncResult(
                success=True,
                rows_fetched=len(queries),
                rows_stored=stored,
                date_range=f"{start_date} to {end_date}"
            )
            
        except Exception as e:
            logger.error(f"GSC sync failed: {e}")
            return GSCSyncResult(
                success=False,
                error=str(e)
            )
    

    async def _store_queries(self, queries: List[GSCQuery]) -> int:
        """Store queries in database"""
        if not self.db_session:
            return 0
            
        from src.models.gsc_data import GSCQuery as GSCQueryDB
        
        stored = 0
        try:
            # We use a simple merge loop for compatibility (SQLite/PG)
            # For high volume, we should switch to bulk methods
            for q in queries:
                date_obj = datetime.strptime(q.date, '%Y-%m-%d').date()
                
                # Check for existing record to update or insert
                existing = self.db_session.query(GSCQueryDB).filter(
                    GSCQueryDB.query_date == date_obj,
                    GSCQueryDB.query == q.query,
                    GSCQueryDB.page == q.page
                ).first()
                
                if existing:
                    # Update
                    existing.clicks = q.clicks
                    existing.impressions = q.impressions
                    existing.ctr = q.ctr
                    existing.position = q.position
                    existing.country = q.country
                    existing.device = q.device
                else:
                    # Insert
                    new_rec = GSCQueryDB(
                        query_date=date_obj,
                        query=q.query,
                        page=q.page,
                        clicks=q.clicks,
                        impressions=q.impressions,
                        ctr=q.ctr,
                        position=q.position,
                        country=q.country,
                        device=q.device
                    )
                    self.db_session.add(new_rec)
                
                stored += 1
                
                # Commit in batches of 100
                if stored % 100 == 0:
                    self.db_session.commit()
            
            self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Failed to store queries: {e}")
            print(f"DEBUG ERROR: {e}") 
            self.db_session.rollback()
            return 0
        
        return stored

    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        return {
            'last_sync': self._last_sync.isoformat() if self._last_sync else None,
            'client_status': self.client.health_check()
        }
