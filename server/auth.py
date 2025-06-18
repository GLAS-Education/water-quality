import os
import httpx
import jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request, Response, Cookie
from fastapi.responses import RedirectResponse
from typing import Optional, Dict, Any
import logging
from urllib.parse import urlencode
import secrets

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router for auth endpoints
router = APIRouter(prefix="/auth", tags=["auth"])

# Session storage (in production, use Redis or database)
_user_sessions = {}

def get_slack_config():
    """Get Slack OAuth2 configuration from environment"""
    client_id = os.getenv("SLACK_CLIENT_ID")
    client_secret = os.getenv("SLACK_CLIENT_SECRET")
    redirect_uri = os.getenv("SLACK_REDIRECT_URI")
    workspace = os.getenv("SLACK_WORKSPACE")
    
    if not all([client_id, client_secret, redirect_uri]):
        raise HTTPException(
            status_code=500,
            detail="Slack OAuth2 configuration incomplete"
        )
    
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "workspace": workspace
    }

def create_jwt_token(user_data: Dict[str, Any]) -> str:
    """Create JWT token for authenticated user"""
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret:
        raise HTTPException(status_code=500, detail="JWT secret not configured")
    
    # Token expires in 7 days
    expiration = datetime.utcnow() + timedelta(days=7)
    
    payload = {
        "user_id": user_data["user"]["id"],
        "team_id": user_data["team"]["id"],
        "team_domain": user_data["team"]["domain"],
        "user_name": user_data["user"]["name"],
        "exp": expiration.timestamp()
    }
    
    return jwt.encode(payload, jwt_secret, algorithm="HS256")

def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token"""
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret:
        return None
    
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid JWT token")
        return None

async def get_current_user(session_token: Optional[str] = Cookie(None)) -> Optional[Dict[str, Any]]:
    """Get current authenticated user from session token"""
    if not session_token:
        return None
    
    user_data = verify_jwt_token(session_token)
    if not user_data:
        return None
    
    # Verify the user belongs to the correct Slack workspace
    expected_workspace = os.getenv("SLACK_WORKSPACE", "glaseducation.slack.com")
    if user_data.get("team_domain") != expected_workspace.replace(".slack.com", ""):
        logger.warning(f"User from wrong workspace: {user_data.get('team_domain')}")
        return None
    
    return user_data

def require_auth(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Dependency that requires authentication"""
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    return current_user

@router.get("/login")
async def login():
    """Initiate Slack OAuth2 login flow"""
    try:
        config = get_slack_config()
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Store state temporarily (in production, use proper storage)
        _user_sessions[f"state_{state}"] = {"created_at": datetime.utcnow()}
        
        # Build Slack OAuth2 URL (legacy Sign in with Slack)
        slack_auth_url = "https://slack.com/oauth/v2/authorize"
        params = {
            "client_id": config["client_id"],
            "user_scope": "identity.basic,identity.email,identity.team",  # Legacy identity scopes
            "redirect_uri": config["redirect_uri"],
            "state": state
        }
        
        auth_url = f"{slack_auth_url}?{urlencode(params)}"
        
        logger.info("Redirecting to Slack OAuth2")
        return RedirectResponse(url=auth_url)
        
    except Exception as e:
        logger.error(f"Error initiating login: {e}")
        raise HTTPException(status_code=500, detail="Login initialization failed")

@router.get("/callback")
async def oauth_callback(request: Request, response: Response):
    """Handle Slack OAuth2 callback"""
    try:
        # Get parameters from callback
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")
        
        if error:
            logger.error(f"OAuth error: {error}")
            raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
        
        if not code or not state:
            raise HTTPException(status_code=400, detail="Missing code or state parameter")
        
        # Verify state (CSRF protection)
        if f"state_{state}" not in _user_sessions:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        # Clean up state
        del _user_sessions[f"state_{state}"]
        
        config = get_slack_config()
        
        # Exchange code for access token
        token_url = "https://slack.com/api/oauth.v2.access"
        token_data = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "redirect_uri": config["redirect_uri"]
        }
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=token_data)
            token_result = token_response.json()
        
        if not token_result.get("ok"):
            error_msg = token_result.get("error", "Unknown error")
            logger.error(f"Token exchange failed: {error_msg}")
            raise HTTPException(status_code=400, detail=f"Token exchange failed: {error_msg}")
        
        # For legacy Sign in with Slack, access token is under authed_user
        authed_user = token_result.get("authed_user", {})
        access_token = authed_user.get("access_token")
        
        if not access_token:
            logger.error(f"No access token in response: {token_result}")
            raise HTTPException(status_code=400, detail="No access token received")
        
        # Get user information
        user_url = "https://slack.com/api/users.identity"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            user_response = await client.get(user_url, headers=headers)
            user_result = user_response.json()
        
        if not user_result.get("ok"):
            error_msg = user_result.get("error", "Unknown error")
            logger.error(f"User info fetch failed: {error_msg}")
            raise HTTPException(status_code=400, detail=f"User info fetch failed: {error_msg}")
        
        # For legacy Sign in with Slack, user data is directly in the response
        user_data = user_result
        
        # Verify user belongs to correct workspace
        expected_workspace = os.getenv("SLACK_WORKSPACE", "glaseducation.slack.com")
        team_domain = user_data.get("team", {}).get("domain", "")
        if team_domain != expected_workspace.replace(".slack.com", ""):
            logger.warning(f"Unauthorized workspace: {team_domain}")
            raise HTTPException(
                status_code=403,
                detail="Access denied: Must be member of glaseducation.slack.com"
            )
        
        # Create JWT token
        jwt_token = create_jwt_token(user_data)

        # Get frontend URL for redirect
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        is_localhost = frontend_url.startswith("http://localhost")
        
        # Set secure HTTP-only cookie and redirect to frontend
        response = RedirectResponse(url=frontend_url, status_code=302)
        response.set_cookie(
            key="session_token",
            value=jwt_token,
            httponly=True,
            secure=True,
            samesite="none" if is_localhost else "lax",
            max_age=7 * 24 * 60 * 60  # 7 days
        )
        
        logger.info(f"User authenticated: {user_data.get('user', {}).get('name', 'Unknown')} from {user_data.get('team', {}).get('domain', 'Unknown')}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")

@router.get("/me")
async def get_user_info(current_user: Dict[str, Any] = Depends(require_auth)):
    """Get current authenticated user information"""
    return {
        "authenticated": True,
        "user_id": current_user["user_id"],
        "user_name": current_user["user_name"],
        "team_domain": current_user["team_domain"],
        "expires_at": current_user["exp"]
    }

@router.post("/logout")
async def logout(response: Response):
    """Logout current user"""
    # Determine if we're in localhost development or production
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    is_localhost = frontend_url.startswith("http://localhost")
    
    # Clear the session cookie
    response.delete_cookie(
        key="session_token",
        httponly=True,
        secure=True,
        samesite="none" if is_localhost else "lax"
    )
    
    return {"message": "Logged out successfully"}

@router.get("/status")
async def auth_status(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Check current authentication status"""
    if current_user:
        return {
            "authenticated": True,
            "user_name": current_user["user_name"],
            "team_domain": current_user["team_domain"]
        }
    else:
        return {"authenticated": False} 