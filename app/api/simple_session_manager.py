"""
Simplified Session Manager
Clean, single-system approach for session management
"""

from fastapi import APIRouter, HTTPException, Header, Body
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
import time

from ..database.supabase import get_supabase_client

router = APIRouter()

class SessionCreateRequest(BaseModel):
    session_id: Optional[str] = None

# Anonymous sessions are no longer supported - authentication required

class SimpleSessionManager:
    """Simplified session manager - one system for all users"""
    
    @staticmethod
    async def get_or_create_session(
        session_id: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get or create a session. REQUIRES AUTHENTICATION.
        
        Flow:
        1. If user_id provided (authenticated) -> use that user
        2. If session_id provided -> check if session exists and belongs to authenticated user
        3. If no user_id -> raise error (authentication required)
        """
        supabase = get_supabase_client()
        
        # REQUIRE AUTHENTICATION - no anonymous users allowed
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Please sign in to use the application."
            )
        
        # Case 1: Authenticated user with existing session
        if session_id:
            return await SimpleSessionManager._handle_authenticated_user(
                user_id, session_id
            )
        
        # Case 2: Authenticated user creating new session
        return await SimpleSessionManager._handle_authenticated_user(
            user_id, None
        )
    
    @staticmethod
    async def _handle_authenticated_user(
        user_id: UUID, 
        session_id: Optional[str]
    ) -> Dict[str, Any]:
        """Handle authenticated user session"""
        supabase = get_supabase_client()
        
        # Verify user exists in database
        # Users should be synced from Supabase Auth by the frontend on login
        user_result = supabase.table("users").select("*").eq("user_id", str(user_id)).execute()
        if not user_result.data:
            # User doesn't exist - they need to be synced from Supabase Auth
            print(f"❌ [SESSION] User {user_id} not found in database")
            print(f"⚠️ [SESSION] User must be synced from Supabase Auth. Frontend should call /api/v1/users endpoint on login.")
            raise HTTPException(
                status_code=404,
                detail=f"User not found. Please ensure your user account is properly synced. User ID: {user_id}"
            )
        
        user = user_result.data[0]
        
        # Get or create session
        if session_id:
            # Check if session exists and belongs to user
            session_result = supabase.table("sessions").select("*").eq("session_id", session_id).eq("user_id", str(user_id)).execute()
            if session_result.data:
                session = session_result.data[0]
                return {
                    "session_id": session["session_id"],
                    "user_id": str(user_id),
                    "is_authenticated": True,
                    "user": user
                }
        
        # Create new session for authenticated user
        new_session_id = str(uuid4())
        
        session_data = {
            "session_id": new_session_id,
            "user_id": str(user_id),
            "title": "New Chat",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "last_message_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True
        }
        
        supabase.table("sessions").insert(session_data).execute()
        
        return {
            "session_id": new_session_id,
            "user_id": str(user_id),
            "is_authenticated": True,
            "user": user
        }
    
    

# API Endpoints
# Test endpoint to verify router is accessible
@router.get("/session/test")
async def test_session_endpoint():
    """Test endpoint to verify the session router is accessible"""
    return {"message": "Session router is working", "status": "ok"}

@router.post("/session")
async def get_or_create_session(
    request: SessionCreateRequest,
    user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Get or create a session - REQUIRES AUTHENTICATION"""
    print(f"🔍 [SESSION API] POST /session endpoint called")
    print(f"🔍 [SESSION API] Request body: {request}")
    print(f"🔍 [SESSION API] X-User-ID header: {user_id}")
    
    try:
        # REQUIRE AUTHENTICATION
        if not user_id:
            print("❌ [SESSION API] No user_id provided")
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Please sign in to use the application."
            )
        
        try:
            parsed_user_id = UUID(user_id)
            print(f"✅ [SESSION API] Parsed user_id: {parsed_user_id}")
        except (ValueError, TypeError) as e:
            print(f"❌ [SESSION API] Invalid user_id format: {user_id} - {e}")
            raise HTTPException(status_code=400, detail=f"Invalid user_id format: {user_id}")
        
        print(f"🔍 [SESSION API] Calling SimpleSessionManager.get_or_create_session with session_id={request.session_id}, user_id={parsed_user_id}")
        result = await SimpleSessionManager.get_or_create_session(
            session_id=request.session_id,
            user_id=parsed_user_id
        )
        
        print(f"✅ [SESSION API] Session created/retrieved: {result.get('session_id')}")
        
        # Ensure all UUID objects are converted to strings for JSON serialization
        response_data = {
            "success": True,
            "session_id": str(result["session_id"]),
            "user_id": str(result["user_id"]),
            "is_authenticated": True,  # Always true now - no anonymous users
            "user": result["user"]
        }
        
        print(f"✅ [SESSION API] Returning response: {response_data}")
        return response_data
        
    except HTTPException:
        # Re-raise HTTPExceptions (400, 404, etc.)
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ [SESSION API] Error in get_or_create_session: {e}")
        print(f"❌ [SESSION API] Traceback: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

# Anonymous session migration and cleanup endpoints removed - authentication required

@router.get("/sessions")
async def get_user_sessions(
    limit: int = 10,
    user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Get user sessions"""
    try:
        print(f"🔍 Sessions API called - user_id: {user_id}")
        print(f"🔍 Sessions API called - limit: {limit}")
        
        if not user_id:
            print("❌ No user_id provided to sessions API")
            return {"success": True, "sessions": []}
        
        supabase = get_supabase_client()
        result = supabase.table("sessions").select("*").eq("user_id", user_id).order("updated_at", desc=True).limit(limit).execute()
        
        print(f"🔍 Found {len(result.data or [])} sessions for user {user_id}")
        
        return {
            "success": True,
            "sessions": result.data or []
        }
    except Exception as e:
        print(f"Error getting user sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: int = 50,
    user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Get messages for a specific session"""
    try:
        print(f"🔍 Session messages API called - session_id: {session_id}, user_id: {user_id}")
        supabase = get_supabase_client()
        
        # Verify session exists and user has access
        session_result = supabase.table("sessions").select("*").eq("session_id", session_id).execute()
        if not session_result.data:
            print(f"❌ Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_result.data[0]
        print(f"🔍 Session found - session_user_id: {session['user_id']}, request_user_id: {user_id}")
        
        if user_id and session["user_id"] != user_id:
            print(f"❌ Access denied - session belongs to {session['user_id']}, but user is {user_id}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get messages
        messages_result = supabase.table("chat_messages").select("*").eq("session_id", session_id).order("created_at", desc=False).limit(limit).execute()
        
        return {
            "success": True,
            "messages": messages_result.data or []
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting session messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and all its messages"""
    try:
        print(f"🔍 Delete session API called - session_id: {session_id}")
        supabase = get_supabase_client()
        
        # Delete all messages for this session first
        supabase.table("chat_messages").delete().eq("session_id", session_id).execute()
        
        # Delete the session
        result = supabase.table("sessions").delete().eq("session_id", session_id).execute()
        
        print(f"✅ Deleted session {session_id}")
        return {"success": True, "message": "Session deleted successfully"}
    except Exception as e:
        print(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions")
async def delete_all_sessions(
    user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Delete all sessions for a user"""
    try:
        print(f"🔍 Delete all sessions API called - user_id: {user_id}")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID required")
        
        supabase = get_supabase_client()
        
        # Get all sessions for the user
        sessions_result = supabase.table("sessions").select("session_id").eq("user_id", user_id).execute()
        
        if not sessions_result.data:
            return {"success": True, "message": "No sessions to delete", "deleted_count": 0}
        
        session_ids = [session["session_id"] for session in sessions_result.data]
        print(f"🔍 Found {len(session_ids)} sessions to delete for user {user_id}")
        
        # Delete all messages for these sessions
        for session_id in session_ids:
            supabase.table("chat_messages").delete().eq("session_id", session_id).execute()
        
        # Delete all sessions for the user
        result = supabase.table("sessions").delete().eq("user_id", user_id).execute()
        
        deleted_count = len(session_ids)
        print(f"✅ Deleted {deleted_count} sessions for user {user_id}")
        
        return {
            "success": True, 
            "message": f"Deleted {deleted_count} sessions successfully",
            "deleted_count": deleted_count
        }
    except Exception as e:
        print(f"Error deleting all sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
