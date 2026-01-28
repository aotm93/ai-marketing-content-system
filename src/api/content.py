from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/v1/content", tags=["content"])


class ContentCreateRequest(BaseModel):
    """Request model for content creation"""
    keyword: str
    products: List[str]
    content_type: str = "blog_post"


class ContentResponse(BaseModel):
    """Response model for content"""
    id: int
    title: str
    status: str
    created_at: str


@router.post("/create", response_model=ContentResponse)
async def create_content(request: ContentCreateRequest):
    """Create new content"""
    return {
        "id": 1,
        "title": f"Content for {request.keyword}",
        "status": "draft",
        "created_at": "2026-01-25T00:00:00Z"
    }


@router.get("/list")
async def list_content():
    """List all content"""
    return {"content": [], "total": 0}
