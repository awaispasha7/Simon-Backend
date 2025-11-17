"""
Simplified User Management API
Clean user management using the simplified session manager
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from ..database.supabase import get_supabase_client

router = APIRouter()

@router.post("/users")
async def create_user(user_data: Dict[str, Any]):
    """
    Create or update a user (sync from Supabase Auth)
    This endpoint is called by the frontend when a user logs in to sync their Supabase Auth data
    
    IMPORTANT: This function prioritizes the backend database as the source of truth.
    If a user with the same email exists in the backend, we use that user's user_id,
    regardless of what Supabase Auth says. This prevents creating duplicate users.
    """
    try:
        supabase = get_supabase_client()
        
        user_id = user_data.get("user_id")
        email = user_data.get("email")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        # STEP 1: Check if user exists by EMAIL first (backend database is source of truth)
        # This prevents creating duplicate users when someone logs in with a different Supabase account
        if email:
            existing_by_email = supabase.table("users").select("*").eq("email", email).execute()
            if existing_by_email.data:
                existing_user = existing_by_email.data[0]
                existing_user_id = existing_user.get("user_id")
                
                # User exists in backend with this email - use that user_id (backend is source of truth)
                if existing_user_id != user_id:
                    print(f"🔍 [USERS] User with email {email} already exists in backend with user_id: {existing_user_id}")
                    print(f"📌 [USERS] Using existing backend user_id (ignoring Supabase Auth user_id {user_id})")
                    print(f"💡 [USERS] This means you're logged in with a different Supabase account than expected")
                    
                    # Update the existing user with latest info from Supabase Auth
                    update_data = {
                        "display_name": user_data.get("display_name") or existing_user.get("display_name"),
                        "avatar_url": user_data.get("avatar_url") or existing_user.get("avatar_url"),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                    update_data = {k: v for k, v in update_data.items() if v is not None}
                    
                    result = supabase.table("users").update(update_data).eq("user_id", existing_user_id).execute()
                    
                    # Return the EXISTING user_id so frontend can use it
                    return {
                        "success": True,
                        "message": "User exists in backend - using existing user_id",
                        "user": result.data[0] if result.data else existing_user,
                        "backend_user_id": existing_user_id,  # Tell frontend to use this instead
                        "supabase_auth_user_id": user_id  # For reference
                    }
                else:
                    # Same user_id - just update info
                    print(f"🔄 [USERS] User {user_id} already exists, updating with latest info...")
                    update_data = {
                        "email": email,
                        "display_name": user_data.get("display_name"),
                        "avatar_url": user_data.get("avatar_url"),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                    update_data = {k: v for k, v in update_data.items() if v is not None}
                    
                    result = supabase.table("users").update(update_data).eq("user_id", user_id).execute()
                    if result.data:
                        return {
                            "success": True,
                            "message": "User updated",
                            "user": result.data[0]
                        }
                    else:
                        return {
                            "success": True,
                            "message": "User already exists",
                            "user": existing_user
                        }
        
        # STEP 2: Check if user exists by user_id (in case email check didn't find it)
        existing_user = supabase.table("users").select("*").eq("user_id", user_id).execute()
        if existing_user.data:
            # User exists - update with latest info from Supabase Auth
            print(f"🔄 [USERS] User {user_id} already exists, updating with latest info...")
            update_data = {
                "email": email,
                "display_name": user_data.get("display_name"),
                "avatar_url": user_data.get("avatar_url"),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            # Remove None values
            update_data = {k: v for k, v in update_data.items() if v is not None}
            
            result = supabase.table("users").update(update_data).eq("user_id", user_id).execute()
            if result.data:
                return {
                    "success": True,
                    "message": "User updated",
                    "user": result.data[0]
                }
            else:
                # Return existing user if update failed
                return {
                    "success": True,
                    "message": "User already exists",
                    "user": existing_user.data[0]
                }
        
        # Create new user
        new_user_data = {
            "user_id": user_id,
            "email": user_data.get("email"),
            "display_name": user_data.get("display_name"),
            "avatar_url": user_data.get("avatar_url"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = supabase.table("users").insert(new_user_data).execute()
        
        if result.data:
            print(f"✅ [USERS] Created user: {user_id}")
            return {
                "success": True,
                "user": result.data[0]
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create user")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [USERS] Error creating/updating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/me")
async def get_current_user(user_id: Optional[str] = Header(None, alias="X-User-ID")):
    """Get current user information"""
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID required")
        
        supabase = get_supabase_client()
        result = supabase.table("users").select("*").eq("user_id", user_id).execute()
        
        if result.data:
            return {
                "success": True,
                "user": result.data[0]
            }
        else:
            raise HTTPException(status_code=404, detail="User not found")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching user: {e}")
        raise HTTPException(status_code=500, detail=str(e))
