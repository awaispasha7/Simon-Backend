from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

# User and Session Models
class User(BaseModel):
    user_id: UUID
    email: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    password_hash: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class UserCreate(BaseModel):
    user_id: Optional[str] = None  # Supabase auth user ID
    email: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    password_hash: Optional[str] = None

class Session(BaseModel):
    session_id: UUID
    user_id: UUID
    title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    is_active: bool = True

class SessionCreate(BaseModel):
    user_id: UUID
    title: Optional[str] = None

class SessionSummary(BaseModel):
    session_id: UUID
    title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    message_count: int = 0
    last_message_preview: Optional[str] = None

# Chat Message Models
class ChatMessage(BaseModel):
    message_id: UUID
    session_id: UUID
    turn_id: Optional[UUID] = None
    role: str  # 'user', 'assistant', 'system'
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ChatMessageCreate(BaseModel):
    session_id: UUID
    role: str
    content: str
    turn_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    text: str
    session_id: Optional[UUID] = None  # If provided, continue existing session
    attached_files: Optional[List[Dict[str, Any]]] = None  # Attached files with metadata
    edit_from_message_id: Optional[UUID] = None  # If provided, delete this message and all subsequent messages before creating new message
    enable_web_search: Optional[bool] = None  # If True, enable web search; if False, disable; if None, use default behavior

class ChatResponse(BaseModel):
    reply: str
    metadata_json: Dict[str, Any]  # The structured metadata JSON returned by the assistant
    session_id: UUID
    message_id: UUID

# Migration Request
class MigrationRequest(BaseModel):
    anonymous_session_id: str
    user_id: str
