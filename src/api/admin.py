"""Admin API endpoints for configuration management"""
from fastapi import APIRouter, HTTPException, status, Depends, Response, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import timedelta
from src.core.auth import authenticate_admin, create_access_token, get_current_admin
from src.core.rate_limiter import check_rate_limit, login_rate_limiter
from src.config import settings
from src.core.database import get_db
from sqlalchemy.orm import Session
from src.config.utils import update_config_value

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class LoginRequest(BaseModel):
    """Login request model"""
    password: str


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    token_type: str = "bearer"
    message: str


class ConfigUpdateRequest(BaseModel):
    """Configuration update request"""
    config_key: str
    config_value: str


class ConfigResponse(BaseModel):
    """Configuration response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


@router.post("/login", response_model=LoginResponse)
async def login(req: Request, request: LoginRequest, response: Response):
    """
    Admin login endpoint

    Authenticates admin with password and returns JWT token
    """
    # Apply rate limiting to prevent brute force attacks
    await check_rate_limit(req, login_rate_limiter)

    if not authenticate_admin(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.admin_session_expire_minutes)
    access_token = create_access_token(
        data={"role": "admin", "authenticated": True},
        expires_delta=access_token_expires
    )

    # Set cookie for browser-based access
    response.set_cookie(
        key="session_token",
        value=access_token,
        httponly=True,
        max_age=settings.admin_session_expire_minutes * 60,
        samesite="lax"
    )

    return LoginResponse(
        access_token=access_token,
        message="Login successful"
    )


@router.post("/logout")
async def logout(response: Response, admin: dict = Depends(get_current_admin)):
    """
    Admin logout endpoint

    Clears the session cookie
    """
    response.delete_cookie(key="session_token")
    return {"message": "Logout successful"}


@router.get("/verify")
async def verify_session(admin: dict = Depends(get_current_admin)):
    """
    Verify admin session

    Returns admin info if session is valid
    """
    return {
        "authenticated": True,
        "role": admin.get("role"),
        "message": "Session is valid"
    }


@router.get("/config", response_model=ConfigResponse)
async def get_config(admin: dict = Depends(get_current_admin)):
    """
    Get current configuration (safe values only)

    Returns non-sensitive configuration values
    """
    safe_config = {
        # Primary AI Provider
        "primary_ai_provider": settings.primary_ai_provider,
        "primary_ai_base_url": settings.primary_ai_base_url,
        "primary_ai_text_model": settings.primary_ai_text_model,
        "primary_ai_image_model": settings.primary_ai_image_model,
        
        # Fallback AI Provider
        "fallback_ai_provider": settings.fallback_ai_provider or "",
        "fallback_ai_base_url": settings.fallback_ai_base_url or "",
        "fallback_ai_text_model": settings.fallback_ai_text_model or "",
        
        # WordPress
        "wordpress_url": settings.wordpress_url,
        "wordpress_username": settings.wordpress_username,
        "seo_plugin": settings.seo_plugin,
        
        # Keyword Research
        "keyword_api_provider": settings.keyword_api_provider or "",
        "keyword_api_username": settings.keyword_api_username or "",
        "keyword_api_key": settings.keyword_api_key or "", # Explicitly included for UI population check
        
        # System
        "environment": settings.environment,
        "log_level": settings.log_level,
        "max_concurrent_agents": str(settings.max_concurrent_agents),
        "content_generation_timeout": str(settings.content_generation_timeout),
        
        # P0-13: Autopilot - Return as strings for select/input compatibility
        "autopilot_enabled": "True" if settings.autopilot_enabled else "False",
        "autopilot_mode": settings.autopilot_mode,
        "publish_interval_minutes": str(settings.publish_interval_minutes),
        "max_posts_per_day": str(settings.max_posts_per_day),
        "max_concurrent_jobs": str(settings.max_concurrent_jobs),
        
        # P1: GSC
        "gsc_site_url": settings.gsc_site_url or "",
        "gsc_auth_method": settings.gsc_auth_method,
        "gsc_credentials_json": settings.gsc_credentials_json or "",
    }

    return ConfigResponse(
        success=True,
        message="Configuration retrieved successfully",
        data=safe_config
    )


@router.put("/config", response_model=ConfigResponse)
async def update_config(
    request: ConfigUpdateRequest, 
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update configuration value

    Persists change to Database (SystemConfig) and reloads settings
    """
    allowed_keys = [
        "PRIMARY_AI_PROVIDER", "PRIMARY_AI_BASE_URL", "PRIMARY_AI_API_KEY",
        "PRIMARY_AI_TEXT_MODEL", "PRIMARY_AI_IMAGE_MODEL",
        "FALLBACK_AI_PROVIDER", "FALLBACK_AI_BASE_URL", "FALLBACK_AI_API_KEY",
        "FALLBACK_AI_TEXT_MODEL", "FALLBACK_AI_IMAGE_MODEL",
        "WORDPRESS_URL", "WORDPRESS_USERNAME", "WORDPRESS_PASSWORD",
        "SEO_PLUGIN", "SEO_API_KEY",
        "KEYWORD_API_PROVIDER", "KEYWORD_API_KEY", "KEYWORD_API_USERNAME", "KEYWORD_API_BASE_URL",
        "LOG_LEVEL", "MAX_CONCURRENT_AGENTS", "CONTENT_GENERATION_TIMEOUT",
        # P0-13: Autopilot
        "AUTOPILOT_ENABLED", "AUTOPILOT_MODE", "PUBLISH_INTERVAL_MINUTES",
        "MAX_POSTS_PER_DAY", "MAX_CONCURRENT_JOBS",
        # P1: GSC
        "GSC_SITE_URL", "GSC_AUTH_METHOD", "GSC_CREDENTIALS_JSON", "GSC_CREDENTIALS_PATH"
    ]

    if request.config_key not in allowed_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuration key '{request.config_key}' is not allowed to be modified"
        )

    try:
        # Determine data type
        data_type = "string"
        key_upper = request.config_key.upper()
        
        if key_upper in ["AUTOPILOT_ENABLED", "WORDPRESS_API_ENABLED", "ENABLE_METRICS"]:
            data_type = "bool"
        elif any(x in key_upper for x in ["_PORT", "_TIMEOUT", "_MINUTES", "_COUNT", "_MAX", "_ID"]):
            data_type = "int"
            
        # Update in database and refresh settings
        success = update_config_value(db, request.config_key, request.config_value, data_type)

        if not success:
             raise Exception("Database update failed")

        return ConfigResponse(
            success=True,
            message=f"Configuration '{request.config_key}' updated successfully.",
            data={"key": request.config_key, "updated": True}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )
