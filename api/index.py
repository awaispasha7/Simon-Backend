"""
Vercel entry point - Full backend functionality
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="Simon Chatbot")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic endpoints
@app.get("/")
def root():
    return {"status": "ok", "message": "API running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

# OPTIONS handler for CORS preflight
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

# Load routes
try:
    from app.api import auth
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
except Exception as e:
    print(f"[ERROR] Auth router failed: {type(e).__name__}: {e}")
    @app.post("/api/v1/auth/login")
    async def fallback_login():
        return JSONResponse(
            status_code=500,
            content={"detail": f"Auth router failed to load: {str(e)}"},
            headers={"Access-Control-Allow-Origin": "*"}
        )

try:
    from app.api import simple_session_manager
    app.include_router(simple_session_manager.router, prefix="/api/v1", tags=["session"])
except Exception as e:
    print(f"[ERROR] Session router failed: {type(e).__name__}: {e}")

try:
    from app.api import simple_chat
    app.include_router(simple_chat.router, prefix="/api/v1", tags=["chat"])
except Exception as e:
    print(f"[ERROR] Chat router failed: {type(e).__name__}: {e}")

try:
    from app.api import upload
    app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
except Exception as e:
    print(f"[ERROR] Upload router failed: {type(e).__name__}: {e}")

try:
    from app.api import transcribe
    app.include_router(transcribe.router, prefix="/api/v1", tags=["transcribe"])
except Exception as e:
    print(f"[ERROR] Transcribe router failed: {type(e).__name__}: {e}")

try:
    from app.api import dossier
    app.include_router(dossier.router, prefix="/api/v1", tags=["dossier"])
except Exception as e:
    print(f"[ERROR] Dossier router failed: {type(e).__name__}: {e}")

try:
    from app.api import coach_tools
    app.include_router(coach_tools.router, prefix="/api/v1/coach", tags=["coach"])
except Exception as e:
    print(f"[ERROR] Coach tools router failed: {type(e).__name__}: {e}")

# Export handler for Vercel
handler = app
