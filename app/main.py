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

# Include routes with individual error handling
# Using new simplified session and chat system

# Enable auth for single-client system
if auth:
    try:
        app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
        print("SUCCESS: Auth router included")
    except Exception as e:
        print(f"ERROR: Error including auth router: {e}")

if transcribe:
    try:
        app.include_router(transcribe.router, prefix="/api/v1", tags=["transcribe"])
        print("SUCCESS: Transcribe router included")
    except Exception as e:
        print(f"ERROR: Error including transcribe router: {e}")

## Pruned for new client MVP: dossier disabled

## Pruned for new client MVP: projects disabled

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
    except Exception as e:
        print(f"ERROR: Error including simple session manager router: {e}")

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

if coach_tools:
    try:
        app.include_router(coach_tools.router, prefix="/api/v1", tags=["coach"])
        print("SUCCESS: Coach tools router included")
    except Exception as e:
        print(f"ERROR: Error including coach tools router: {e}")

if ingest:
    try:
        app.include_router(ingest.router, prefix="/api/v1", tags=["ingestion"])
        print("SUCCESS: Ingestion router included")
    except Exception as e:
        print(f"ERROR: Error including ingest router: {e}")

# Add root route to handle 404 errors
@app.get("/")
async def root():
    return {"message": "Simon Chatbot Backend API", "status": "running"}

# Add health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "Backend is running",
        "cors_enabled": True,
        "allowed_origins": ["*"],  # All origins allowed
        "endpoints": ["/dossier", "/transcribe", "/upload", "/api/v1/chat", "/api/v1/sessions", "/api/v1/auth/login", "/api/v1/auth/signup", "/api/v1/dossiers", "/api/v1/admin/extract-knowledge"],
        "routes_available": {
            "chat_sessions": False,  # Using simplified system
            "auth": auth is not None,
            "transcribe": transcribe is not None,
            "dossier": dossier is not None,
            "upload": upload is not None
        },
        "background_workers": {
            "periodic_cleanup": True,
            "knowledge_extraction": True
        }
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
    print("Starting up FastAPI application...")
    print("CORS middleware configured")
    print("Application ready to serve requests")
    # Note: Background workers disabled for serverless deployment
    # Periodic cleanup and knowledge extraction should be handled via scheduled tasks
    # or external cron jobs in production serverless environments

@app.on_event("shutdown")
async def shutdown():
    """
    This function runs when the FastAPI application shuts down.
    You can add cleanup tasks here if needed.
    """
    print("Shutting down FastAPI application...")

