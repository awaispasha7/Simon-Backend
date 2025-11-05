"""
Simple Authentication API for single-client personal AI assistant.
Uses hardcoded credentials from environment variables.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Removed unused imports for single-client system

router = APIRouter()
security = HTTPBearer()

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days for personal assistant

# Single client credentials from environment variables
CLIENT_USERNAME = os.getenv("CLIENT_USERNAME", "admin")
CLIENT_PASSWORD = os.getenv("CLIENT_PASSWORD", "admin123")

# Debug: Print loaded credentials (remove in production)
print(f"🔐 Auth loaded - CLIENT_USERNAME: {CLIENT_USERNAME}, CLIENT_PASSWORD: {'*' * len(CLIENT_PASSWORD) if CLIENT_PASSWORD else 'NOT SET'}")

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict  # Simple user dict for single client

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get the current authenticated user from JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username", CLIENT_USERNAME)
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Ensure user_id is a valid UUID (use SINGLE_USER_ID if not)
        from .simple_session_manager import SINGLE_USER_ID
        try:
            # Validate it's a UUID
            UUID(user_id)
        except (ValueError, TypeError):
            # If not a valid UUID, use the single user ID
            user_id = str(SINGLE_USER_ID)
        
        # Return simple user dict for single client
        return {
            "user_id": user_id,
            "username": username,
            "display_name": "Personal Assistant User",
            "email": None
        }
    except (jwt.PyJWTError, jwt.InvalidTokenError, jwt.ExpiredSignatureError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate single client with username and password"""
    # Debug logging (remove in production)
    print(f"🔐 Login attempt - Username: {request.username}, Password provided: {'Yes' if request.password else 'No'}")
    print(f"🔐 Expected - Username: {CLIENT_USERNAME}, Password set: {'Yes' if CLIENT_PASSWORD else 'No'}")
    
    # Verify credentials against environment variables
    if request.username != CLIENT_USERNAME or request.password != CLIENT_PASSWORD:
        print(f"❌ Login failed - Username match: {request.username == CLIENT_USERNAME}, Password match: {request.password == CLIENT_PASSWORD}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Use the same UUID as session manager for consistency
    from .simple_session_manager import SINGLE_USER_ID
    user_id_str = str(SINGLE_USER_ID)
    
    # Create access token for single client
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id_str, "username": CLIENT_USERNAME}, 
        expires_delta=access_token_expires
    )
    
    # Return simple user object for single client with proper UUID
    user_data = {
        "user_id": user_id_str,
        "username": CLIENT_USERNAME,
        "display_name": "Personal Assistant User",
        "email": None
    }
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_data
    )


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.post("/logout")
async def logout():
    """Logout user (client should discard the token)"""
    return {"message": "Successfully logged out"}

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """Refresh access token"""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user["user_id"], "username": current_user.get("username", CLIENT_USERNAME)}, 
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=current_user
    )
