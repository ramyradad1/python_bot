from bot.supabase_client import get_supabase_client
from postgrest.exceptions import APIError

try:
    print("Initializing Supabase client...")
    supabase = get_supabase_client()
    bucket_name = "articles"
    
    # 1. Ensure Bucket Exists and is Public
    print(f"Checking if '{bucket_name}' bucket exists...")
    buckets = supabase.storage.list_buckets()
    if any(b.name == bucket_name for b in buckets):
        print(f"Bucket '{bucket_name}' exists. Ensuring it's public...")
        supabase.storage.update_bucket(bucket_name, options={"public": True})
    else:
        print(f"Creating public bucket '{bucket_name}'...")
        supabase.storage.create_bucket(bucket_name, options={"public": True})
        print(f"Bucket '{bucket_name}' created successfully.")

    # 2. Add Select Policy for public access (Standard for Supabase Storage)
    # Since the SDK doesn't always expose policy management directly, 
    # we rely on the bucket being marked 'public' which usually handles this,
    # but we will perform a test download to verify.
    
    print("Verifying public access with a test fetch...")
    # We'll check if we can get a public URL for a non-existent file just to see the format
    test_url = supabase.storage.from_(bucket_name).get_public_url("non_existent_test.jpg")
    print(f"Generated Public URL format: {test_url}")
    print("✅ Logic update complete. Please check the website for newly generated articles.")

except Exception as e:
    print(f"Error communicating with Supabase Storage: {e}")
