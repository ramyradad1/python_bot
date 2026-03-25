import os
import uuid
import time
import requests
import hashlib
from google import genai
from google.genai import types
from .supabase_client import get_supabase_client as _get_sb_client
from .key_manager import get_next_api_key
from .logger import log_info
from .state import GLOBAL_STOP_EVENT

def upload_to_supabase(image_bytes: bytes, file_name: str) -> str:
    """Uploads binary image stream to Supabase Storage and enforces public URL returning."""
    try:
        supabase_client = _get_sb_client()
        bucket_name = "articles"
        
        # Push file to storage securely bypassing 401s
        res = supabase_client.storage.from_(bucket_name).upload(
            path=file_name,
            file=image_bytes,
            file_options={"content-type": "image/jpeg", "upsert": "true"}
        )
        
        # Request immediate public URL mapping from CDNs
        public_url = supabase_client.storage.from_(bucket_name).get_public_url(file_name)
        return public_url
    except Exception as e:
        log_info(f"[Image AI] Deep Cloud injection failed targeting Supabase Storage: {e}")
        return ""

def get_dynamic_placeholder(prompt: str) -> str:
    """Generates a unique Pollinations.ai URL, downloads it, and uploads to Supabase."""
    try:
        seed = int(hashlib.md5(prompt.encode()).hexdigest(), 16) % 1000000
        safe_prompt = requests.utils.quote(prompt[:200])
        pollinations_url = f"https://pollinations.ai/p/{safe_prompt}?width=1024&height=576&seed={seed}&model=flux&nologo=true"
        
        log_info(f"[Image AI] Fetching dynamic asset: {pollinations_url[:60]}...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(pollinations_url, headers=headers, timeout=30)
        resp.raise_for_status()
        
        file_name = f"hero_fallback_{uuid.uuid4().hex}.jpg"
        public_url = upload_to_supabase(resp.content, file_name)
        
        if public_url:
            log_info(f"[Image AI] Dynamic asset synced to Supabase: {public_url}")
            return public_url
            
        return pollinations_url # Last ditch URL return
    except Exception as e:
        log_info(f"[Image AI] Dynamic sync failed: {e}")
        return "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=1200"

def generate_flux_image(prompt: str) -> str:
    """Generates an image via HuggingFace Inference API utilizing Flux.1 with local fallback."""
    hf_token = os.getenv("HF_TOKEN")
    
    # Standard stable fallback URL generator
    def get_fallback():
        return get_dynamic_placeholder(prompt)

    if not hf_token:
        log_info("[Image AI] 'HF_TOKEN' missing. Using dynamic placeholder...")
        return get_fallback()

    API_URLS = [
        f"https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell",
        f"https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
    ]
    
    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {
        "inputs": prompt,
        "parameters": {"width": 1024, "height": 576}
    }
    
    for api_url in API_URLS:
        try:
            log_info(f"[Image AI] Attempting synthesis via {api_url.split('/')[2]}...")
            response = requests.post(api_url, headers=headers, json=payload, timeout=45)
            
            if response.status_code == 503:
                log_info("[Image AI] Model is sleeping, waiting for boot...")
                time.sleep(15)
                response = requests.post(api_url, headers=headers, json=payload, timeout=45)

            if response.status_code == 200:
                image_bytes = response.content
                file_name = f"hero_{uuid.uuid4().hex}.jpg"
                public_url = upload_to_supabase(image_bytes, file_name)
                # If upload to Supabase worked, return that. If not, we will try the next API or fallback.
                if public_url: 
                    return public_url
                
            log_info(f"[Image AI] API failed ({response.status_code}). Trying next...")
        except Exception as e:
            log_info(f"[Image AI] Connection error: {e}")
            continue

    log_info("[Image AI] All primary APIs failed. Deploying dynamic Pollinations fallback.")
    return get_fallback()

def analyze_and_generate_image(original_url: str, article_title: str) -> str:
    """Downloads original image, streams prompt through Gemini Vision, and renders Flux natively."""
    try:
        image_bytes = None
        content_type = 'image/jpeg'

        if original_url and original_url.startswith('http'):
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.get(original_url, headers=headers, timeout=10)
                response.raise_for_status()
                image_bytes = response.content
                content_type = response.headers.get('content-type', 'image/jpeg')
            except Exception as e:
                log_info(f"[Image AI] Failed to fetch source image: {e}")
        
        max_retries = 3
        attempt = 0
        prompt_text = f"Analyze the article title: '{article_title}'. Write a concise image generation prompt (max 300 chars) for a PHOTOREALISTIC, editorial-quality photograph. ONLY return the prompt text."
        
        generated_prompt = f"A photorealistic editorial photograph for an article about {article_title}, sharp focus, 4K resolution."
        
        while attempt < max_retries:
            api_key = get_next_api_key()
            if not api_key: break
            try:
                client = genai.Client(api_key=api_key)
                contents = []
                if image_bytes:
                    contents.append(types.Part.from_bytes(data=image_bytes, mime_type=content_type))
                contents.append(prompt_text)
                
                resp = client.models.generate_content(model='gemini-2.0-flash', contents=contents)
                if resp and resp.text:
                    generated_prompt = resp.text.strip()
                    log_info(f"[Image AI] Gemini prompt synthesis successful.")
                    break
            except Exception:
                attempt += 1
                    
        return generate_flux_image(generated_prompt)
        
    except Exception as e:
        log_info(f"[Image AI] Pipeline fault: {e}. Using title-based fallback.")
        return get_dynamic_placeholder(article_title)

def process_article_image(original_url: str, article_title: str) -> str:
    return analyze_and_generate_image(original_url, article_title)
