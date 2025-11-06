"""
Vercel entry point - Load routes one at a time to find the problem
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

# Try loading auth route ONLY
try:
    print("[TEST] Attempting to import auth...")
    from app.api import auth
    print("[TEST] Auth imported successfully")
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    print("[OK] Auth router loaded")
except Exception as e:
    print(f"[ERROR] Auth router failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    # Create fallback login endpoint
    @app.post("/api/v1/auth/login")
    async def fallback_login():
        return JSONResponse(
            status_code=500,
            content={"detail": "Auth router not available"},
            headers={"Access-Control-Allow-Origin": "*"}
        )

# Try loading session route ONLY
try:
    print("[TEST] Attempting to import simple_session_manager...")
    from app.api import simple_session_manager
    print("[TEST] Session imported successfully")
    app.include_router(simple_session_manager.router, prefix="/api/v1", tags=["session"])
    print("[OK] Session router loaded")
except Exception as e:
    print(f"[ERROR] Session router failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Try loading chat route ONLY
try:
    print("[TEST] Attempting to import simple_chat...")
    from app.api import simple_chat
    print("[TEST] Chat imported successfully")
    app.include_router(simple_chat.router, prefix="/api/v1", tags=["chat"])
    print("[OK] Chat router loaded")
except Exception as e:
    print(f"[ERROR] Chat router failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("[SUCCESS] App initialization complete")

# Export handler for Vercel
handler = app
