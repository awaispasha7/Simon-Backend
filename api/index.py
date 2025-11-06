"""
Vercel entry point - Step 2: Add real auth router
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# Step 2: Try to load auth router
try:
    from app.api import auth
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    print("[OK] Auth router loaded")
except Exception as e:
    print(f"[ERROR] Auth router failed: {type(e).__name__}: {e}")
    # Fallback endpoints
    @app.post("/api/v1/auth/login")
    def login():
        return {"detail": "Auth router not available", "error": str(e)}
    
    @app.get("/api/v1/auth/me")
    def get_me():
        return {"user_id": "single_client", "username": "admin"}
