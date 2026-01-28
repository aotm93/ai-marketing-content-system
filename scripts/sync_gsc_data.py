#!/usr/bin/env python3
"""
GSC Data Sync Script
====================
Synchronize Google Search Console data to local database.

Usage:
    python scripts/sync_gsc_data.py --days 28
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import get_db, init_db
from src.config.settings import settings
from src.integrations.gsc_client import GSCClient, GSCDataSync, GSCAuthMethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser(description="Sync GSC data")
    parser.add_argument("--days", type=int, default=3, help="Number of days to sync (default: 3)")
    parser.add_argument("--site", type=str, default=settings.gsc_site_url, help="Site URL")
    parser.add_argument("--sa-json", type=str, default=None, help="Path to Service Account JSON")
    args = parser.parse_args()

    if not args.site:
        logger.error("Site URL not provided. Set GSC_SITE_URL in .env or pass --site")
        sys.exit(1)

    logger.info(f"Starting GSC Sync for {args.site} (Last {args.days} days)")

    # Initialize DB
    await init_db()

    # Initialize Client
    try:
        # Check for SA Key in env or args
        sa_info = settings.gsc_credentials_json
        sa_path = args.sa_json
        
        client = None
        
        if sa_info:
             client = GSCClient(
                site_url=args.site,
                auth_method=GSCAuthMethod.SERVICE_ACCOUNT,
                credentials_json=sa_info
            )
        elif sa_path:
            client = GSCClient(
                site_url=args.site,
                auth_method=GSCAuthMethod.SERVICE_ACCOUNT,
                credentials_path=sa_path
            )
        else:
            logger.error("No credentials found. Set GSC_SA_KEY in .env or pass --sa-json")
            sys.exit(1)

        # Sync
        async for session in get_db():
            syncer = GSCDataSync(client, db_session=session)
            result = await syncer.sync_queries(days_back=args.days)
            
            if result.success:
                logger.info(f"Sync Success! Fetched: {result.rows_fetched}, Stored: {result.rows_stored}")
            else:
                logger.error(f"Sync Failed: {result.error}")
                
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
