"""
Vercel entry point - ultra-minimal to ensure it starts
"""
import sys
import os
import traceback

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("Starting Vercel function...")
print("=" * 60)

try:
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    print("✅ FastAPI imports successful")
except Exception as e:
    print(f"❌ FastAPI import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Create minimal app first
app = FastAPI(title="Simon Chatbot")
print("✅ FastAPI app created")

# Add CORS
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

# Basic endpoints
@app.get("/")
async def root():
    return {"status": "ok", "message": "API running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# OPTIONS handler for CORS
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

print("✅ Basic endpoints registered")

# Now try to load routes - but don't fail if they don't load
print("=" * 60)
print("Loading routes...")
print("=" * 60)

# Load auth routes
try:
    from app.api import auth
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    print("✅ Auth router loaded")
except Exception as e:
    print(f"❌ Auth router failed: {type(e).__name__}: {e}")
    traceback.print_exc()
    # Create fallback login endpoint
    @app.post("/api/v1/auth/login")
    async def fallback_login():
        return JSONResponse(
            status_code=500,
            content={"detail": f"Auth router failed to load: {str(e)}"},
            headers={"Access-Control-Allow-Origin": "*"}
        )

# Load session routes
try:
    from app.api import simple_session_manager
    app.include_router(simple_session_manager.router, prefix="/api/v1", tags=["session"])
    print("✅ Session router loaded")
except Exception as e:
    print(f"❌ Session router failed: {type(e).__name__}: {e}")
    traceback.print_exc()

# Load chat routes
try:
    from app.api import simple_chat
    app.include_router(simple_chat.router, prefix="/api/v1", tags=["chat"])
    print("✅ Chat router loaded")
except Exception as e:
    print(f"❌ Chat router failed: {type(e).__name__}: {e}")
    traceback.print_exc()

print("=" * 60)
print(f"✅ App initialized with {len(app.routes)} routes")
print("=" * 60)

# Export for Vercel
handler = app
