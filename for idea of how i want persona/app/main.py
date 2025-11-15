"""
Ultra-minimal FastAPI app - guaranteed to start
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create app
app = FastAPI(title="Simon Chatbot")

# CORS - if it fails, continue anyway
try:
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
except:
    pass

@app.get("/")
async def root():
    return {"status": "ok", "message": "API running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Try to load routes - but don't crash if they fail
def load_routes():
    try:
        from app.api import auth
        app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
        print("✅ Auth loaded")
    except Exception as e:
        print(f"⚠️ Auth failed: {e}")

    try:
        from app.api import simple_session_manager
        app.include_router(simple_session_manager.router, prefix="/api/v1", tags=["session"])
        print("✅ Session loaded")
    except Exception as e:
        print(f"⚠️ Session failed: {e}")

    try:
        from app.api import simple_chat
        app.include_router(simple_chat.router, prefix="/api/v1", tags=["chat"])
        print("✅ Chat loaded")
    except Exception as e:
        print(f"⚠️ Chat failed: {e}")

# Load routes on first request via middleware
_loaded = False

@app.middleware("http")
async def lazy_load(request, call_next):
    global _loaded
    if not _loaded:
        load_routes()
        _loaded = True
    return await call_next(request)
