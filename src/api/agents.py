from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


class AgentTaskRequest(BaseModel):
    """Request model for agent tasks"""
    agent_name: str
    task_type: str
    data: Dict[str, Any]


class AgentTaskResponse(BaseModel):
    """Response model for agent tasks"""
    status: str
    result: Dict[str, Any]


@router.post("/execute", response_model=AgentTaskResponse)
async def execute_agent_task(request: AgentTaskRequest):
    """Execute a task with a specific agent"""
    # Agent execution logic would go here
    return {
        "status": "success",
        "result": {"message": f"Task executed by {request.agent_name}"}
    }


@router.get("/list")
async def list_agents():
    """List all available agents"""
    return {
        "agents": [
            "orchestrator",
            "market_researcher",
            "keyword_strategist",
            "content_creator",
            "media_creator",
            "publish_manager"
        ]
    }
