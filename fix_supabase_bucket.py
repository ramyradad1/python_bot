from bot.supabase_client import get_supabase_client

try:
    print("Initializing Supabase client...")
    supabase = get_supabase_client()
    bucket_name = "articles"
    
    print(f"Checking if '{bucket_name}' bucket exists...")
    buckets = supabase.storage.list_buckets()
    if any(b.name == bucket_name for b in buckets):
        print(f"Bucket '{bucket_name}' already exists.")
    else:
        print(f"Creating public bucket '{bucket_name}'...")
        supabase.storage.create_bucket(bucket_name, options={"public": True})
        print(f"Bucket '{bucket_name}' created successfully.")
except Exception as e:
    print(f"Error communicating with Supabase Storage: {e}")
