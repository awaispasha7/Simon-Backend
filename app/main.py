from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio

# Lazy import routes - only import when needed to reduce cold start time
# Initialize FastAPI app first (minimal startup)
app = FastAPI()

# Route modules will be imported lazily in the router inclusion section
transcribe = None
simple_session_manager = None
simple_chat = None
simple_users = None
auth = None
dossier = None
projects = None
upload = None
coach_tools = None
ingest = None

# Add CORS middleware with comprehensive configuration for production
# Allow all origins in development, but restrict in production
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://*.vercel.app",  # Allow all Vercel deployments
]

# Add CORS middleware with comprehensive configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now - can be restricted later
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers to the client
    max_age=3600,  # Cache preflight response for 1 hour
)

# Lazy load routes only when needed (reduces cold start time)
def _load_routes():
    """Load routes lazily to reduce startup time"""
    import traceback
    
    # Load essential routes first
    try:
        print("🔄 Loading auth router...")
        from app.api import auth
        app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
        print("✅ Auth router loaded successfully")
    except Exception as e:
        print(f"❌ ERROR: Auth router failed to load: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")
    
    try:
        print("🔄 Loading session manager router...")
        from app.api import simple_session_manager
        app.include_router(simple_session_manager.router, prefix="/api/v1", tags=["session"])
        print("✅ Session manager router loaded successfully")
    except Exception as e:
        print(f"❌ ERROR: Session manager router failed to load: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")
    
    try:
        print("🔄 Loading chat router...")
        from app.api import simple_chat
        app.include_router(simple_chat.router, prefix="/api/v1", tags=["chat"])
        print("✅ Chat router loaded successfully")
    except Exception as e:
        print(f"❌ ERROR: Chat router failed to load: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")
    
    # Load optional routes
    try:
        print("🔄 Loading transcribe router...")
        from app.api import transcribe
        app.include_router(transcribe.router, prefix="/api/v1", tags=["transcribe"])
        print("✅ Transcribe router loaded successfully")
    except Exception as e:
        print(f"⚠️ WARNING: Transcribe router not loaded: {e}")
    
    try:
        print("🔄 Loading upload router...")
        from app.api import upload
        app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
        print("✅ Upload router loaded successfully")
    except Exception as e:
        print(f"⚠️ WARNING: Upload router not loaded: {e}")
    
    try:
        print("🔄 Loading coach tools router...")
        from app.api import coach_tools
        app.include_router(coach_tools.router, prefix="/api/v1", tags=["coach"])
        print("✅ Coach tools router loaded successfully")
    except Exception as e:
        print(f"⚠️ WARNING: Coach tools not loaded: {e}")
    
    try:
        print("🔄 Loading ingestion router...")
        from app.api import ingest
        app.include_router(ingest.router, prefix="/api/v1", tags=["ingestion"])
        print("✅ Ingestion router loaded successfully")
    except Exception as e:
        print(f"⚠️ WARNING: Ingestion router not loaded: {e}")

# Load routes lazily - only when first request comes in
# This prevents crashes during import time
routes_loaded = False

@app.middleware("http")
async def load_routes_middleware(request, call_next):
    """Middleware to load routes on first request"""
    global routes_loaded
    if not routes_loaded:
        try:
            print("🚀 Loading routes on first request...")
            _load_routes()
            routes_loaded = True
            print("✅ Routes loaded successfully")
        except Exception as e:
            print(f"❌ ERROR loading routes: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            # Don't crash - just log the error
    return await call_next(request)

# Add root route to handle 404 errors
@app.get("/")
async def root():
    return {
        "message": "Simon Chatbot Backend API", 
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "auth": "/api/v1/auth/login",
            "me": "/api/v1/auth/me"
        }
    }

# Add health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint - no auth required"""
    return {
        "status": "healthy",
        "message": "Backend is running",
        "timestamp": datetime.now().isoformat(),
        "cors_enabled": True
    }

# Add simple test endpoint
@app.get("/test")
async def test_endpoint():
    return {"message": "Test endpoint working", "status": "ok"}

# Add manual knowledge extraction trigger endpoint
@app.post("/api/v1/admin/extract-knowledge")
async def trigger_knowledge_extraction():
    """Manually trigger knowledge extraction (admin endpoint)"""
    try:
        from app.workers.knowledge_extractor import knowledge_extractor
        
        # Run knowledge extraction
        await knowledge_extractor.extract_knowledge_from_conversations(limit=10)
        
        return {
            "success": True,
            "message": "Knowledge extraction completed successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Knowledge extraction failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


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
    Optimized for serverless: no background workers in serverless environments.
    """
    try:
        print("=" * 50)
        print("🚀 Starting FastAPI application...")
        print("=" * 50)
        print("✅ CORS middleware configured")
        print("✅ Application ready to serve requests")
        print("=" * 50)
        # Note: Background workers disabled for serverless deployment
        # Periodic cleanup and knowledge extraction should be handled via scheduled tasks
        # or external cron jobs in production serverless environments
    except Exception as e:
        print(f"❌ ERROR during startup: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise

@app.on_event("shutdown")
async def shutdown():
    """
    This function runs when the FastAPI application shuts down.
    You can add cleanup tasks here if needed.
    """
    print("Shutting down FastAPI application...")

