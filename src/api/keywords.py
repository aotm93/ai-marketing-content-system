"""
Keywords API Router

Provides endpoints for keyword research and management.
All endpoints require admin authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio

from src.core.auth import get_current_admin
from src.core.database import get_db
from src.integrations.keyword_client import KeywordClient
from src.services.keyword_strategy import ContentAwareKeywordGenerator
from src.models.keyword import Keyword

router = APIRouter(prefix="/api/v1/keywords", tags=["keywords"])


@router.get("/suggestions")
async def get_keyword_suggestions(
    seed: str = Query(..., description="Seed keyword to get suggestions for"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of suggestions"),
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get keyword suggestions based on a seed keyword.
    Uses DataForSEO API if configured, otherwise returns empty list.
    """
    try:
        client = KeywordClient(provider='dataforseo')
        opportunities = await client.get_keyword_suggestions(seed, limit=limit)
        
        return {
            "seed": seed,
            "suggestions": [
                {
                    "keyword": opp.keyword,
                    "volume": opp.volume,
                    "difficulty": opp.difficulty,
                    "cpc": opp.cpc,
                    "intent": opp.intent,
                    "source": opp.source
                }
                for opp in opportunities
            ],
            "count": len(opportunities)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching keyword suggestions: {str(e)}")


@router.get("/difficulty")
async def get_keyword_difficulty(
    keywords: str = Query(..., description="Comma-separated list of keywords"),
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get difficulty scores for multiple keywords.
    Input: comma-separated keywords (e.g., "seo tools,marketing software")
    """
    try:
        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
        
        if not keyword_list:
            raise HTTPException(status_code=400, detail="No keywords provided")
        
        if len(keyword_list) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 keywords allowed")
        
        # Use the first keyword as seed to get related data
        client = KeywordClient(provider='dataforseo')
        opportunities = await client.get_keyword_suggestions(keyword_list[0], limit=100)
        
        # Create lookup by keyword
        difficulty_map = {opp.keyword.lower(): opp for opp in opportunities}
        
        results = []
        for kw in keyword_list:
            kw_lower = kw.lower()
            if kw_lower in difficulty_map:
                opp = difficulty_map[kw_lower]
                results.append({
                    "keyword": kw,
                    "difficulty": opp.difficulty,
                    "volume": opp.volume,
                    "cpc": opp.cpc,
                    "found": True
                })
            else:
                # Keyword not found in API results
                results.append({
                    "keyword": kw,
                    "difficulty": None,
                    "volume": None,
                    "cpc": None,
                    "found": False
                })
        
        return {
            "keywords": results,
            "count": len(results)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching keyword difficulty: {str(e)}")


@router.get("/pool")
def get_keyword_pool(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of keywords to return"),
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get current keyword pool from database.
    Returns keywords stored in the Keyword model.
    """
    try:
        keywords = db.query(Keyword).order_by(Keyword.search_volume.desc().nullslast()).limit(limit).all()
        
        return {
            "keywords": [
                {
                    "id": kw.id,
                    "keyword": kw.keyword,
                    "search_volume": kw.search_volume,
                    "difficulty": kw.difficulty,
                    "category": kw.category,
                    "intent": kw.intent,
                    "created_at": kw.created_at.isoformat() if kw.created_at else None
                }
                for kw in keywords
            ],
            "count": len(keywords)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching keyword pool: {str(e)}")


@router.post("/refresh")
async def refresh_keyword_pool(
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Refresh the keyword pool by generating new keywords and enriching with API data.
    This triggers the ContentAwareKeywordGenerator and stores results in the database.
    """
    try:
        # Generate new keywords
        generator = ContentAwareKeywordGenerator()
        candidates = generator.generate_keyword_pool(limit=100)
        
        # Store/update keywords in database
        created_count = 0
        updated_count = 0
        
        for candidate in candidates:
            # Check if keyword already exists
            existing = db.query(Keyword).filter(Keyword.keyword == candidate.keyword).first()
            
            if existing:
                # Update existing keyword with new data
                if candidate.search_volume is not None:
                    existing.search_volume = candidate.search_volume
                if candidate.difficulty_score is not None:
                    existing.difficulty = candidate.difficulty_score
                updated_count += 1
            else:
                # Create new keyword
                new_keyword = Keyword(
                    keyword=candidate.keyword,
                    category=candidate.category,
                    intent=candidate.intent.value,
                    search_volume=candidate.search_volume,
                    difficulty=candidate.difficulty_score,
                    priority="medium",  # Default priority
                )
                db.add(new_keyword)
                created_count += 1
        
        db.commit()
        
        return {
            "message": "Keyword pool refreshed successfully",
            "created": created_count,
            "updated": updated_count,
            "total": len(candidates)
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error refreshing keyword pool: {str(e)}")
