"""
Vercel entry point - app.py (Vercel looks for this)
This imports from app.main
"""
from app.main import app

# Export for Vercel
__all__ = ['app']

