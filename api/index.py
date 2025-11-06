"""
Vercel entry point - Step 5: Add remaining routes (upload, transcribe, dossier, coach)
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

# Step 3: Session router (already working)
try:
    from app.api import simple_session_manager
    app.include_router(simple_session_manager.router, prefix="/api/v1", tags=["session"])
    print("[OK] Session router loaded")
except Exception as e:
    print(f"[ERROR] Session router failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Step 4: Chat router (already working)
try:
    from app.api import simple_chat
    app.include_router(simple_chat.router, prefix="/api/v1", tags=["chat"])
    print("[OK] Chat router loaded")
except Exception as e:
    print(f"[ERROR] Chat router failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Step 5: Upload router
try:
    from app.api import upload
    app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
    print("[OK] Upload router loaded")
except Exception as e:
    print(f"[ERROR] Upload router failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Step 5: Transcribe router
try:
    from app.api import transcribe
    app.include_router(transcribe.router, prefix="/api/v1", tags=["transcribe"])
    print("[OK] Transcribe router loaded")
except Exception as e:
    print(f"[ERROR] Transcribe router failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Step 5: Dossier router
try:
    from app.api import dossier
    app.include_router(dossier.router, prefix="/api/v1", tags=["dossier"])
    print("[OK] Dossier router loaded")
except Exception as e:
    print(f"[ERROR] Dossier router failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Step 5: Coach tools router
try:
    from app.api import coach_tools
    app.include_router(coach_tools.router, prefix="/api/v1/coach", tags=["coach"])
    print("[OK] Coach tools router loaded")
except Exception as e:
    print(f"[ERROR] Coach tools router failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
