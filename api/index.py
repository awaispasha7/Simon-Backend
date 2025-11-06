"""
Ultra-minimal Vercel entry point - no emojis to avoid encoding issues
"""
import sys
import traceback

# Force output to stderr so Vercel captures it
def log(msg):
    print(msg, file=sys.stderr)
    print(msg)

log("=" * 60)
log("Python process started")
log("=" * 60)
log(f"Python version: {sys.version}")
log(f"Python path: {sys.path}")

try:
    log("Importing FastAPI...")
    from fastapi import FastAPI
    log("[OK] FastAPI imported")
except Exception as e:
    log(f"[ERROR] FastAPI import failed: {type(e).__name__}: {e}")
    traceback.print_exc(file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)

try:
    log("Creating FastAPI app...")
    app = FastAPI(title="Simon Chatbot")
    log("[OK] FastAPI app created")
except Exception as e:
    log(f"[ERROR] FastAPI app creation failed: {type(e).__name__}: {e}")
    traceback.print_exc(file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)

try:
    log("Adding CORS...")
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi import Request
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    log("[OK] CORS added")
except Exception as e:
    log(f"[WARNING] CORS failed: {type(e).__name__}: {e}")
    traceback.print_exc(file=sys.stderr)
    traceback.print_exc()

@app.get("/")
async def root():
    return {"status": "ok", "message": "API running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

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

log("[OK] Basic endpoints registered")

# Try to import routes one by one
log("=" * 60)
log("Testing route imports...")
log("=" * 60)

# Test auth import
try:
    log("Testing: from app.api import auth")
    from app.api import auth
    log(f"[OK] Auth module imported: {auth}")
    log(f"Auth router: {auth.router}")
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    log("[OK] Auth router included")
except Exception as e:
    log(f"[ERROR] Auth import failed: {type(e).__name__}: {e}")
    traceback.print_exc(file=sys.stderr)
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
    log("Testing: from app.api import simple_session_manager")
    from app.api import simple_session_manager
    app.include_router(simple_session_manager.router, prefix="/api/v1", tags=["session"])
    log("[OK] Session router included")
except Exception as e:
    log(f"[ERROR] Session router failed: {type(e).__name__}: {e}")
    traceback.print_exc(file=sys.stderr)
    traceback.print_exc()

# Load chat routes
try:
    log("Testing: from app.api import simple_chat")
    from app.api import simple_chat
    app.include_router(simple_chat.router, prefix="/api/v1", tags=["chat"])
    log("[OK] Chat router included")
except Exception as e:
    log(f"[ERROR] Chat router failed: {type(e).__name__}: {e}")
    traceback.print_exc(file=sys.stderr)
    traceback.print_exc()

log("=" * 60)
log(f"[OK] App ready with {len(app.routes)} routes")
log("=" * 60)

# Export handler
handler = app
log("[OK] Handler exported")
