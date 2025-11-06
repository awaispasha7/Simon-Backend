"""
Vercel entry point - loads routes at import time for serverless compatibility
"""
import sys
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Wrap everything in try/except to prevent crashes
try:
    # Create app directly here
    app = FastAPI(title="Simon Chatbot")

    # Add CORS with explicit OPTIONS handling
    try:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        print("✅ CORS middleware added")
    except Exception as e:
        print(f"⚠️ CORS middleware error: {e}")
        traceback.print_exc()

    # Basic endpoints that definitely work
    @app.get("/")
    async def root():
        return {"status": "ok", "message": "API running"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    # Explicit OPTIONS handler for CORS preflight
    @app.options("/{full_path:path}")
    async def options_handler(request: Request):
        return JSONResponse(
            content={},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
            }
        )

    # Load routes at import time (required for Vercel serverless)
    print("=" * 60)
    print("Loading routes...")
    print("=" * 60)

    try:
        from app.api import auth
        app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
        print("✅ Auth router loaded")
    except Exception as e:
        print(f"❌ Auth router failed: {type(e).__name__}: {e}")
        traceback.print_exc()
        # Create a minimal auth endpoint if import fails
        @app.post("/api/v1/auth/login")
        async def fallback_login():
            return JSONResponse(
                status_code=500,
                content={"detail": "Auth router failed to load"},
                headers={"Access-Control-Allow-Origin": "*"}
            )

    try:
        from app.api import simple_session_manager
        app.include_router(simple_session_manager.router, prefix="/api/v1", tags=["session"])
        print("✅ Session router loaded")
    except Exception as e:
        print(f"❌ Session router failed: {type(e).__name__}: {e}")
        traceback.print_exc()

    try:
        from app.api import simple_chat
        app.include_router(simple_chat.router, prefix="/api/v1", tags=["chat"])
        print("✅ Chat router loaded")
    except Exception as e:
        print(f"❌ Chat router failed: {type(e).__name__}: {e}")
        traceback.print_exc()

    print("=" * 60)
    print(f"Routes loaded. App ready with {len(app.routes)} routes.")
    print("=" * 60)

    # Export handler for Vercel
    handler = app

except Exception as e:
    print("=" * 60)
    print("CRITICAL ERROR: Failed to create app")
    print(f"Error: {type(e).__name__}: {e}")
    print("=" * 60)
    traceback.print_exc()
    
    # Create minimal fallback app
    app = FastAPI(title="Simon Chatbot - Error Mode")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/")
    async def root():
        return {"status": "error", "message": "App failed to initialize", "error": str(e)}
    
    @app.get("/health")
    async def health():
        return {"status": "error"}
    
    @app.options("/{full_path:path}")
    async def options_handler(request: Request):
        return JSONResponse(
            content={},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    
    handler = app
