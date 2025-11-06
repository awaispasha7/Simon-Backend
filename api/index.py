"""
Vercel entry point - Start with NO route imports, add them one by one
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

# Create minimal auth endpoint without importing the router
@app.post("/api/v1/auth/login")
async def login():
    return JSONResponse(
        status_code=401,
        content={"detail": "Login endpoint - needs credentials"},
        headers={"Access-Control-Allow-Origin": "*"}
    )

@app.get("/api/v1/auth/me")
async def get_me():
    return JSONResponse(
        content={"user_id": "single_client", "username": "admin"},
        headers={"Access-Control-Allow-Origin": "*"}
    )

# Export handler for Vercel
handler = app
