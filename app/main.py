from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import sys
import traceback

# Initialize FastAPI app FIRST with minimal setup
app = FastAPI(
    title="Simon Chatbot API",
    version="1.0.0",
    description="Personal AI Assistant Backend"
)

# Add CORS middleware - this should never fail
try:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=3600,
    )
    print("✅ CORS middleware configured")
except Exception as e:
    print(f"⚠️ CORS middleware warning: {e}")

# Basic endpoints that work without any dependencies
@app.get("/")
async def root():
    """Root endpoint - always works"""
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

@app.get("/health")
async def health_check():
    """Health check endpoint - always works"""
    return {
        "status": "healthy",
        "message": "Backend is running",
        "timestamp": datetime.now().isoformat(),
        "cors_enabled": True
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint - always works"""
    return {"message": "Test endpoint working", "status": "ok"}

# Load routes ONLY when needed - with maximum error handling
def _safe_load_routes():
    """Safely load routes with maximum error tolerance"""
    import traceback
    
    # Load auth router
    try:
        print("🔄 Attempting to load auth router...")
        from app.api import auth
        app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
        print("✅ Auth router loaded")
    except Exception as e:
        print(f"⚠️ Auth router skipped: {type(e).__name__}: {e}")
        # Don't print full traceback for optional routes
    
    # Load session manager
    try:
        print("🔄 Attempting to load session manager...")
        from app.api import simple_session_manager
        app.include_router(simple_session_manager.router, prefix="/api/v1", tags=["session"])
        print("✅ Session manager loaded")
    except Exception as e:
        print(f"⚠️ Session manager skipped: {type(e).__name__}: {e}")
    
    # Load chat router
    try:
        print("🔄 Attempting to load chat router...")
        from app.api import simple_chat
        app.include_router(simple_chat.router, prefix="/api/v1", tags=["chat"])
        print("✅ Chat router loaded")
    except Exception as e:
        print(f"⚠️ Chat router skipped: {type(e).__name__}: {e}")
    
    # Optional routes - fail silently
    for route_name, module_path, prefix in [
        ("transcribe", "app.api.transcribe", "/api/v1"),
        ("upload", "app.api.upload", "/api/v1"),
        ("coach_tools", "app.api.coach_tools", "/api/v1"),
        ("ingest", "app.api.ingest", "/api/v1"),
    ]:
        try:
            module = __import__(module_path, fromlist=["router"])
            app.include_router(module.router, prefix=prefix, tags=[route_name])
            print(f"✅ {route_name} router loaded")
        except Exception as e:
            print(f"⚠️ {route_name} router skipped: {type(e).__name__}")

# Load routes on first request ONLY
routes_loaded = False

@app.middleware("http")
async def load_routes_middleware(request, call_next):
    """Load routes lazily on first request"""
    global routes_loaded
    if not routes_loaded:
        try:
            print("=" * 60)
            print("🚀 Loading routes on first request...")
            print("=" * 60)
            _safe_load_routes()
            routes_loaded = True
            print("=" * 60)
            print("✅ Route loading completed")
            print("=" * 60)
        except Exception as e:
            print(f"❌ Route loading error (non-fatal): {type(e).__name__}: {e}")
            # Continue anyway - basic endpoints still work
            routes_loaded = True  # Don't keep trying
    return await call_next(request)

@app.on_event("startup")
async def startup():
    """Startup event - minimal logging"""
    try:
        print("=" * 60)
        print("🚀 FastAPI application starting...")
        print("=" * 60)
        print("✅ Basic endpoints available: /, /health, /test")
        print("✅ Routes will load on first request")
        print("=" * 60)
    except Exception as e:
        print(f"⚠️ Startup event warning: {e}")

@app.on_event("shutdown")
async def shutdown():
    """Shutdown event"""
    print("🛑 FastAPI application shutting down...")

# Favicon handlers
@app.get("/favicon.ico")
async def favicon():
    return {"message": "No favicon"}

@app.get("/favicon.png")
async def favicon_png():
    return {"message": "No favicon"}
