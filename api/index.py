"""
Vercel entry point - Step 3: Add session routes
"""
import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

app = FastAPI()

# Add CORS - essential for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "API running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

# Step 2: Auth router (already working)
try:
    from app.api import auth
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    print("[OK] Auth router loaded")
except Exception as e:
    print(f"[ERROR] Auth router failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Step 3: Session router
try:
    from app.api import simple_session_manager
    app.include_router(simple_session_manager.router, prefix="/api/v1", tags=["session"])
    print("[OK] Session router loaded")
except Exception as e:
    print(f"[ERROR] Session router failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
