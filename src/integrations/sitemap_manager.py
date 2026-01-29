"""
Sitemap Manager
Generates and submits sitemaps
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger(__name__)


class SitemapManager:
    """Sitemap Manager"""
    
    def __init__(self, site_url: str):
        self.site_url = site_url.rstrip('/')
    
    def generate_sitemap_xml(self, urls: List[Dict[str, Any]]) -> str:
        """
        Generate Sitemap XML
        
        Args:
            urls: List of dicts with 'loc', 'lastmod', 'changefreq', 'priority'
        """
        urlset = ET.Element('urlset')
        urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
        
        for url_data in urls:
            url_elem = ET.SubElement(urlset, 'url')
            
            loc = ET.SubElement(url_elem, 'loc')
            loc.text = url_data['loc']
            
            if 'lastmod' in url_data:
                lastmod = ET.SubElement(url_elem, 'lastmod')
                val = url_data['lastmod']
                if isinstance(val, datetime):
                    lastmod.text = val.strftime('%Y-%m-%d')
                else:
                    lastmod.text = val
            
            if 'changefreq' in url_data:
                changefreq = ET.SubElement(url_elem, 'changefreq')
                changefreq.text = url_data['changefreq']
            
            if 'priority' in url_data:
                priority = ET.SubElement(url_elem, 'priority')
                priority.text = str(url_data['priority'])
        
        xml_str = ET.tostring(urlset, encoding='unicode', method='xml')
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'
    
    async def submit_to_gsc(self, sitemap_url: str, gsc_client) -> Dict[str, Any]:
        """Submit sitemap to Google Search Console"""
        try:
            # Assuming gsc_client has submit_sitemap method
            result = await gsc_client.submit_sitemap(sitemap_url)
            
            return {
                "success": True,
                "sitemap_url": sitemap_url,
                "message": "Sitemap submitted to GSC successfully"
            }
        except Exception as e:
            logger.error(f"Failed to submit sitemap to GSC: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def submit_to_bing(self, sitemap_url: str, api_key: str) -> Dict[str, Any]:
        """Submit sitemap to Bing Webmaster Tools"""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://ssl.bing.com/webmaster/api.svc/json/SubmitUrlbatch?apikey={api_key}",
                    json={
                        "siteUrl": self.site_url,
                        "urlList": [sitemap_url]
                    }
                )
                
                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "response": response.json() if response.status_code == 200 else response.text
                }
        except Exception as e:
            logger.error(f"Failed to submit sitemap to Bing: {e}")
            return {
                "success": False,
                "error": str(e)
            }
