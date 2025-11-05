"""
Vercel Serverless Function Entry Point
This file is used by Vercel to serve the FastAPI application
"""
from app.main import app

# Vercel will use this 'app' variable as the WSGI application
# This is the entry point for all serverless function invocations
# Deployment trigger: 2025-01-21

# Export the app for Vercel
handler = app
