from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.config import settings
from src.api.admin import router as admin_router
import logging

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Marketing Content System",
    description="Autonomous multi-agent system for generating marketing content",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(admin_router)

# Mount static files for admin interface
import os
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "static")
if os.path.exists(static_path):
    app.mount("/admin", StaticFiles(directory=os.path.join(static_path, "admin"), html=True), name="admin")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Marketing Content System API",
        "version": "1.0.0",
        "status": "running",
        "admin_panel": "/admin"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
