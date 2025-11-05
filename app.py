"""
Vercel entry point - loads routes at import time for serverless compatibility
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import traceback

# Create app directly here
app = FastAPI(title="Simon Chatbot")

# Add CORS
try:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
except Exception as e:
    print(f"⚠️ CORS middleware error: {e}")

# Basic endpoints that definitely work
@app.get("/")
async def root():
    return {"status": "ok", "message": "API running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

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
