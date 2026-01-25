"""Admin API endpoints for configuration management"""
from fastapi import APIRouter, HTTPException, status, Depends, Response, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import timedelta
from src.core.auth import authenticate_admin, create_access_token, get_current_admin
from src.core.rate_limiter import check_rate_limit, login_rate_limiter, api_rate_limiter
from src.config import settings
import os
import json

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
        "primary_ai_provider": settings.primary_ai_provider,
        "primary_ai_base_url": settings.primary_ai_base_url,
        "primary_ai_text_model": settings.primary_ai_text_model,
        "primary_ai_image_model": settings.primary_ai_image_model,
        "fallback_ai_provider": settings.fallback_ai_provider,
        "fallback_ai_base_url": settings.fallback_ai_base_url,
        "fallback_ai_text_model": settings.fallback_ai_text_model,
        "wordpress_url": settings.wordpress_url,
        "wordpress_username": settings.wordpress_username,
        "seo_plugin": settings.seo_plugin,
        "keyword_api_provider": settings.keyword_api_provider,
        "environment": settings.environment,
        "log_level": settings.log_level,
        "max_concurrent_agents": settings.max_concurrent_agents,
        "content_generation_timeout": settings.content_generation_timeout,
    }

    return ConfigResponse(
        success=True,
        message="Configuration retrieved successfully",
        data=safe_config
    )


@router.put("/config", response_model=ConfigResponse)
async def update_config(request: ConfigUpdateRequest, admin: dict = Depends(get_current_admin)):
    """
    Update configuration value

    Updates environment variables and reloads settings
    """
    allowed_keys = [
        "PRIMARY_AI_PROVIDER", "PRIMARY_AI_BASE_URL", "PRIMARY_AI_API_KEY",
        "PRIMARY_AI_TEXT_MODEL", "PRIMARY_AI_IMAGE_MODEL",
        "FALLBACK_AI_PROVIDER", "FALLBACK_AI_BASE_URL", "FALLBACK_AI_API_KEY",
        "FALLBACK_AI_TEXT_MODEL", "FALLBACK_AI_IMAGE_MODEL",
        "WORDPRESS_URL", "WORDPRESS_USERNAME", "WORDPRESS_PASSWORD",
        "SEO_PLUGIN", "SEO_API_KEY",
        "KEYWORD_API_PROVIDER", "KEYWORD_API_KEY", "KEYWORD_API_BASE_URL",
        "LOG_LEVEL", "MAX_CONCURRENT_AGENTS", "CONTENT_GENERATION_TIMEOUT"
    ]

    if request.config_key not in allowed_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuration key '{request.config_key}' is not allowed to be modified"
        )

    try:
        # Read current .env file
        env_path = ".env"
        env_vars = {}

        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()

        # Update the value
        env_vars[request.config_key] = request.config_value

        # Write back to .env file
        with open(env_path, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")

        # Update environment variable
        os.environ[request.config_key] = request.config_value

        return ConfigResponse(
            success=True,
            message=f"Configuration '{request.config_key}' updated successfully. Restart required for full effect.",
            data={"key": request.config_key, "updated": True}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )
