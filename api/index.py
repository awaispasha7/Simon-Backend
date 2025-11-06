"""
Vercel entry point - Add CORS first, then routes incrementally
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

@app.post("/api/v1/auth/login")
def login():
    return {"detail": "Login endpoint"}

@app.get("/api/v1/auth/me")
def get_me():
    return {"user_id": "single_client", "username": "admin"}
