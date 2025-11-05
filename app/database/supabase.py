import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Optional Supabase setup for MVP (safe no-op when not configured)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

def get_supabase_client():
    """Return a Supabase client if credentials exist; otherwise return None.
    This makes DB optional for the MVP.
    """
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            return None
        from supabase import create_client  # import lazily to avoid hard dependency
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as _:
        return None
