from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio

# Import routes with error handling
ROUTES_AVAILABLE = True
AUTH_AVAILABLE = True

# Import individual routes with error handling
chat = None
transcribe = None
auth = None
upload = None

# Old chat router removed - using new simplified system

try:
    from app.api import transcribe
    print("SUCCESS: Transcribe router imported")
except Exception as e:
    print(f"ERROR: Error importing transcribe router: {e}")
    transcribe = None

# Using simplified session and chat system

try:
    from app.api import simple_session_manager
    print("SUCCESS: Simple session manager imported")
except Exception as e:
    print(f"ERROR: Error importing simple_session_manager: {e}")
    simple_session_manager = None

try:
    from app.api import simple_chat
    print("SUCCESS: Simple chat imported")
except Exception as e:
    print(f"ERROR: Error importing simple_chat: {e}")
    simple_chat = None

try:
    from app.api import simple_users
    print("SUCCESS: Simple users imported")
except Exception as e:
    print(f"ERROR: Error importing simple_users: {e}")
    simple_users = None

try:
    from app.api import auth
    print("SUCCESS: Auth router imported")
except Exception as e:
    print(f"ERROR: Error importing auth router: {e}")
    auth = None

try:
    from app.api import upload
    print("SUCCESS: Upload router imported")
except Exception as e:
    print(f"ERROR: Error importing upload router: {e}")
    upload = None


# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware with comprehensive configuration
# Note: When allow_credentials=True, we cannot use allow_origins=["*"]
# We must explicitly list allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://chatbot-simon.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers to the client
    max_age=3600,  # Cache preflight response for 1 hour
)

# Include routes with individual error handling
# Using new simplified session and chat system

if auth:
    try:
        app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
        print("SUCCESS: Auth router included")
    except Exception as e:
        print(f"ERROR: Error including auth router: {e}")

if transcribe:
    try:
        app.include_router(transcribe.router)
        print("SUCCESS: Transcribe router included")
    except Exception as e:
        print(f"ERROR: Error including transcribe router: {e}")

if upload:
    try:
        app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
        print("SUCCESS: Upload router included")
    except Exception as e:
        print(f"ERROR: Error including upload router: {e}")

# Include new simplified routers
if simple_session_manager:
    try:
        app.include_router(simple_session_manager.router, prefix="/api/v1", tags=["session"])
        print("SUCCESS: Simple session manager router included")
        # Debug: Print all routes in the router
        print(f"🔍 [DEBUG] Session router routes:")
        for route in simple_session_manager.router.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                print(f"  - {list(route.methods)} {route.path}")
    except Exception as e:
        print(f"ERROR: Error including simple session manager router: {e}")
        import traceback
        print(f"ERROR: Traceback: {traceback.format_exc()}")

if simple_chat:
    try:
        app.include_router(simple_chat.router, prefix="/api/v1", tags=["chat"])
        print("SUCCESS: Simple chat router included")
    except Exception as e:
        print(f"ERROR: Error including simple chat router: {e}")

if simple_users:
    try:
        app.include_router(simple_users.router, prefix="/api/v1", tags=["users"])
        print("SUCCESS: Simple users router included")
    except Exception as e:
        print(f"ERROR: Error including simple users router: {e}")


# Add root route
@app.get("/")
async def root():
    return {
        "message": "Simon's Chatbot Backend API",
        "status": "running",
        "version": "2.0",
        "description": "Fitness coaching chatbot API with session-based chat system",
        "endpoints": {
            "root": "/",
            "health": "/health",
            "api_docs": "/docs",
            "chat": "/api/v1/chat",
            "sessions": "/api/v1/sessions",
            "session": "/api/v1/session",
            "users": "/api/v1/users",
            "auth": "/api/v1/auth",
            "upload": "/api/v1/upload",
            "transcribe": "/transcribe"
        }
    }

# Add health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "Backend is running",
        "timestamp": datetime.now().isoformat(),
        "cors_enabled": True,
        "allowed_origins": ["*"],
        "routes_available": {
            "session_management": simple_session_manager is not None,
            "chat": simple_chat is not None,
            "users": simple_users is not None,
            "auth": auth is not None,
            "transcribe": transcribe is not None,
            "upload": upload is not None,
        },
        "api_endpoints": {
            "session": [
                "POST /api/v1/session - Create or get session",
                "GET /api/v1/sessions - Get user sessions",
                "GET /api/v1/sessions/{session_id}/messages - Get session messages",
                "PUT /api/v1/sessions/{session_id}/title - Update session title",
                "DELETE /api/v1/sessions/{session_id} - Delete session",
                "DELETE /api/v1/sessions - Delete all sessions"
            ],
            "chat": [
                "POST /api/v1/chat - Send chat message (streaming)"
            ],
            "users": [
                "POST /api/v1/users - Create or update user",
                "GET /api/v1/users/me - Get current user"
            ],
            "auth": [
                "POST /api/v1/auth/login - User login",
                "POST /api/v1/auth/signup - User signup"
            ]
        },
        "background_workers": {
            "knowledge_extraction": True
        },
        "features": {
            "authentication_required": True,
            "anonymous_sessions": False,
            "projects": False,
            "dossier": False
        }
    }

# Add API info endpoint
@app.get("/api")
async def api_info():
    """Get API information and available endpoints"""
    return {
        "name": "Simon's Chatbot API",
        "version": "2.0",
        "description": "Fitness coaching chatbot API",
        "base_url": "/api/v1",
        "authentication": "Required for all endpoints (except /health, /, /api)",
        "endpoints": {
            "session": {
                "create_or_get": "POST /api/v1/session",
                "list": "GET /api/v1/sessions",
                "get_messages": "GET /api/v1/sessions/{session_id}/messages",
                "update_title": "PUT /api/v1/sessions/{session_id}/title",
                "delete": "DELETE /api/v1/sessions/{session_id}",
                "delete_all": "DELETE /api/v1/sessions"
            },
            "chat": {
                "send_message": "POST /api/v1/chat (streaming response)"
            },
            "users": {
                "create_or_update": "POST /api/v1/users",
                "get_current": "GET /api/v1/users/me"
            },
            "auth": {
                "login": "POST /api/v1/auth/login",
                "signup": "POST /api/v1/auth/signup"
            },
            "upload": {
                "upload_file": "POST /api/v1/upload"
            },
            "transcribe": {
                "transcribe_audio": "POST /transcribe"
            }
        },
        "headers": {
            "required": ["X-User-ID"],
            "optional": ["X-Session-ID", "Authorization"]
        }
    }

# Add simple test endpoint
@app.get("/test")
async def test_endpoint():
    return {"message": "Test endpoint working", "status": "ok"}

# Admin endpoint removed - no longer needed


# CORS is handled by the middleware above

@app.get("/cors-test")
async def cors_test():
    """Test endpoint to verify CORS is working"""
    return {
        "message": "CORS test successful",
        "timestamp": datetime.now().isoformat(),
        "cors_headers": "Should be set by middleware"
    }

# Add favicon routes to handle 404 errors
@app.get("/favicon.ico")
async def favicon():
    return {"message": "Favicon not found"}

@app.get("/favicon.png")
async def favicon_png():
    return {"message": "Favicon not found"}

@app.on_event("startup")
async def startup():
    """
    This function runs when the FastAPI application starts.
    """
    print("Starting up FastAPI application...")
    print("CORS middleware configured")
    print("Application ready to serve requests")

    # Anonymous session cleanup removed - authentication required, no anonymous sessions

    # Start knowledge extraction worker
    try:
        from app.workers.knowledge_extractor import knowledge_extractor

        async def knowledge_extraction_worker():
            while True:
                try:
                    # Run knowledge extraction every 2 hours
                    await knowledge_extractor.extract_knowledge_from_conversations(limit=5)
                    print("SUCCESS: Knowledge extraction completed")
                except Exception as extraction_error:
                    print(f"WARNING: Knowledge extraction error: {extraction_error}")
                
                # Run every 2 hours (7200 seconds)
                await asyncio.sleep(7200)

        asyncio.create_task(knowledge_extraction_worker())
        print("SUCCESS: Started knowledge extraction worker")
    except Exception as worker_error:
        print(f"WARNING: Failed to start knowledge extraction worker: {worker_error}")

@app.on_event("shutdown")
async def shutdown():
    """
    This function runs when the FastAPI application shuts down.
    You can add cleanup tasks here if needed.
    """
    print("Shutting down FastAPI application...")

