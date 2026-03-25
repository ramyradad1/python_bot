import os
from supabase import create_client, Client
from dotenv import load_dotenv
from .logger import log_info

# Load environment from both paths
_bot_env = os.path.join(os.path.dirname(__file__), "..", ".env")
_project_env = os.path.join(os.path.dirname(__file__), "..", "..", ".env.local")
load_dotenv(_bot_env)
load_dotenv(_project_env)

# Singleton cached client
_cached_client: Client | None = None


def get_supabase_client() -> Client:
    """
    Returns a cached Supabase client with a 15-second timeout.
    Uses SERVICE ROLE key for admin access (bypasses RLS).
    """
    global _cached_client
    if _cached_client is not None:
        return _cached_client

    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not url or not key:
        log_info("[DB] ❌ NEXT_PUBLIC_SUPABASE_URL أو SUPABASE_SERVICE_ROLE_KEY مفقودة من .env")
        raise Exception("Supabase credentials missing from environment.")

    log_info("[DB] جاري الاتصال بقاعدة بيانات Supabase...")

    try:
        # Create client — the service role key is set as both apikey and Authorization headers automatically
        _cached_client = create_client(url, key)
        log_info("[DB] ✅ تم الاتصال بنجاح.")
        return _cached_client
    except Exception as e:
        log_info(f"[DB] ❌ فشل الاتصال: {e}")
        raise


if __name__ == "__main__":
    try:
        supabase = get_supabase_client()
        res = supabase.table("articles").select("id", count="exact").limit(1).execute()
        print(f"[SUCCESS] Connected to Supabase. Response: {res}")
    except Exception as e:
        print(f"[FAIL] Connection error: {e}")
