"""
Indexing and Monitoring Service
Implements P2-8: Index monitoring and submission

Features:
- Sitemap generation
- IndexNow submission
- Google indexing status check
- Coverage monitoring
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class SitemapGenerator:
    """Generate XML sitemaps for pSEO pages"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
    
    def generate_sitemap(
        self,
        pages: List[Dict[str, Any]],
        change_freq: str = "weekly",
        priority: float = 0.8
    ) -> str:
        """
        Generate XML sitemap
        
        Args:
            pages: List of page dictionaries with 'slug', 'updated_at'
            change_freq: How frequently the page is likely to change
            priority: Priority relative to other pages
        """
        # Create root element
        urlset = ET.Element("urlset")
        urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
        
        for page in pages:
            url_elem = ET.SubElement(urlset, "url")
            
            # Location
            loc = ET.SubElement(url_elem, "loc")
            loc.text = f"{self.base_url}/{page['slug']}"
            
            # Last modified
            if "updated_at" in page:
                lastmod = ET.SubElement(url_elem, "lastmod")
                lastmod.text = page["updated_at"]
            
            # Change frequency
            changefreq = ET.SubElement(url_elem, "changefreq")
            changefreq.text = change_freq
            
            # Priority
            priority_elem = ET.SubElement(url_elem, "priority")
            priority_elem.text = str(priority)
        
        # Convert to string
        tree = ET.ElementTree(urlset)
        import io
        output = io.BytesIO()
        tree.write(output, encoding='utf-8', xml_declaration=True)
        
        return output.getvalue().decode('utf-8')
    
    def generate_sitemap_index(
        self,
        sitemap_urls: List[str]
    ) -> str:
        """
        Generate sitemap index for multiple sitemaps
        
        Used when you have too many URLs for a single sitemap (> 50,000)
        """
        sitemapindex = ET.Element("sitemapindex")
        sitemapindex.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
        
        for sitemap_url in sitemap_urls:
            sitemap = ET.SubElement(sitemapindex, "sitemap")
            
            loc = ET.SubElement(sitemap, "loc")
            loc.text = sitemap_url
            
            lastmod = ET.SubElement(sitemap, "lastmod")
            lastmod.text = datetime.now().strftime("%Y-%m-%d")
        
        tree = ET.ElementTree(sitemapindex)
        import io
        output = io.BytesIO()
        tree.write(output, encoding='utf-8', xml_declaration=True)
        
        return output.getvalue().decode('utf-8')


class IndexNowSubmitter:
    """
    Submit URLs to IndexNow API
    
    IndexNow is a protocol supported by Bing, Yandex, and others
    for instant URL submission.
    """
    
    INDEXNOW_ENDPOINTS = {
        "bing": "https://www.bing.com/indexnow",
        "yandex": "https://yandex.com/indexnow"
    }
    
    def __init__(self, api_key: str, host: str):
        self.api_key = api_key
        self.host = host
    
    async def submit_urls(
        self,
        urls: List[str],
        engine: str = "bing"
    ) -> Dict[str, Any]:
        """
        Submit URLs to IndexNow
        
        Args:
            urls: List of URLs to submit
            engine: Which search engine ('bing' or 'yandex')
        """
        endpoint = self.INDEXNOW_ENDPOINTS.get(engine)
        if not endpoint:
            raise ValueError(f"Unsupported engine: {engine}")
        
        # Build request payload
        payload = {
            "host": self.host,
            "key": self.api_key,
            "keyLocation": f"https://{self.host}/{self.api_key}.txt",
            "urlList": urls
        }
        
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json; charset=utf-8"}
                )
                
                # IndexNow returns 200 or 202 for success
                response.raise_for_status()
                
                logger.info(f"IndexNow submission successful: {len(urls)} URLs to {engine}")
                
                return {
                    "status": "success",
                    "engine": engine,
                    "http_code": response.status_code,
                    "urls_submitted": len(urls),
                    "timestamp": datetime.now().isoformat()
                }
                
        except httpx.HTTPError as e:
            logger.error(f"IndexNow submission failed: {e}")
            return {
                "status": "failed",
                "engine": engine,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


class IndexMonitor:
    """
    Monitor indexing status of pSEO pages
    
    Tracks:
    - Submission status
    - Indexing status
    - Coverage issues
    """
    
    def __init__(self):
        self.submissions: Dict[str, Dict[str, Any]] = {}
        self.index_status: Dict[str, Dict[str, Any]] = {}
    
    def record_submission(
        self,
        url: str,
        method: str,  # sitemap, indexnow, manual
        submitted_at: Optional[datetime] = None
    ):
        """Record URL submission"""
        self.submissions[url] = {
            "method": method,
            "submitted_at": (submitted_at or datetime.now()).isoformat(),
            "status": "submitted"
        }
        logger.info(f"Recorded submission: {url} via {method}")
    
    def update_index_status(
        self,
        url: str,
        indexed: bool,
        checked_at: Optional[datetime] = None
    ):
        """Update indexing status for a URL"""
        self.index_status[url] = {
            "indexed": indexed,
            "checked_at": (checked_at or datetime.now()).isoformat()
        }
        
        # Update submission status if exists
        if url in self.submissions:
            if indexed:
                self.submissions[url]["status"] = "indexed"
            else:
                days_since_submission = (
                    datetime.now() - 
                    datetime.fromisoformat(self.submissions[url]["submitted_at"])
                ).days
                
                if days_since_submission > 7:
                    self.submissions[url]["status"] = "pending_long"
    
    def get_coverage_report(self) -> Dict[str, Any]:
        """Generate coverage report"""
        total_submitted = len(self.submissions)
        total_indexed = sum(
            1 for status in self.index_status.values()
            if status.get("indexed")
        )
        
        pending = sum(
            1 for sub in self.submissions.values()
            if sub.get("status") == "submitted"
        )
        
        pending_long = sum(
            1 for sub in self.submissions.values()
            if sub.get("status") == "pending_long"
        )
        
        return {
            "total_submitted": total_submitted,
            "total_indexed": total_indexed,
            "index_rate": round(total_indexed / total_submitted * 100, 2) if total_submitted > 0 else 0,
            "pending": pending,
            "pending_long": pending_long,
            "last_updated": datetime.now().isoformat()
        }
    
    def get_urls_needing_resubmission(self, days: int = 14) -> List[str]:
        """Get URLs that haven't been indexed after N days"""
        cutoff = datetime.now() - timedelta(days=days)
        
        needing_resubmission = []
        
        for url, submission in self.submissions.items():
            submitted_at = datetime.fromisoformat(submission["submitted_at"])
            
            if submitted_at < cutoff:
                # Check if indexed
                is_indexed = self.index_status.get(url, {}).get("indexed", False)
                
                if not is_indexed:
                    needing_resubmission.append(url)
        
        return needing_resubmission


class IndexingService:
    """
    Unified indexing service
    
    Combines sitemap generation, IndexNow, and monitoring
    """
    
    def __init__(
        self,
        base_url: str,
        indexnow_api_key: Optional[str] = None
    ):
        self.sitemap_generator = SitemapGenerator(base_url)
        self.indexnow = IndexNowSubmitter(indexnow_api_key, base_url) if indexnow_api_key else None
        self.monitor = IndexMonitor()
    
    async def submit_new_pages(
        self,
        pages: List[Dict[str, Any]],
        use_indexnow: bool = True,
        update_sitemap: bool = True
    ) -> Dict[str, Any]:
        """
        Submit new pages for indexing
        
        Args:
            pages: List of page data with 'slug'
            use_indexnow: Submit via IndexNow
            update_sitemap: Update sitemap
        """
        results = {
            "pages_submitted": len(pages),
            "methods": [],
            "errors": []
        }
        
        urls = [f"{self.sitemap_generator.base_url}/{p['slug']}" for p in pages]
        
        # IndexNow submission
        if use_indexnow and self.indexnow:
            try:
                indexnow_result = await self.indexnow.submit_urls(urls)
                results["methods"].append("indexnow")
                results["indexnow"] = indexnow_result
                
                # Record submissions
                for url in urls:
                    self.monitor.record_submission(url, "indexnow")
                    
            except Exception as e:
                logger.error(f"IndexNow submission failed: {e}")
                results["errors"].append(f"IndexNow: {str(e)}")
        
        # Sitemap update
        if update_sitemap:
            try:
                sitemap_xml = self.sitemap_generator.generate_sitemap(pages)
                results["methods"].append("sitemap")
                results["sitemap_generated"] = True
                
                # Record submissions
                for url in urls:
                    self.monitor.record_submission(url, "sitemap")
                    
            except Exception as e:
                logger.error(f"Sitemap generation failed: {e}")
                results["errors"].append(f"Sitemap: {str(e)}")
        
        return results
    
    def get_indexing_dashboard(self) -> Dict[str, Any]:
        """Get complete indexing dashboard data"""
        return {
            "coverage": self.monitor.get_coverage_report(),
            "needs_resubmission": self.monitor.get_urls_needing_resubmission(),
            "recent_submissions": list(self.monitor.submissions.values())[-10:]
        }
