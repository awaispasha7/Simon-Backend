"""
Vercel entry point - Match the exact working minimal version
"""
from fastapi import FastAPI

app = FastAPI()

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
