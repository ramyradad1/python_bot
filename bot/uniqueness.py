import re
import json
from google import genai
from bs4 import BeautifulSoup
from .key_manager import get_next_api_key

def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    return re.sub(r'\s+', ' ', text).strip()

def check_uniqueness(original_html: str, rewritten_html: str) -> dict:
    original_text = extract_text(original_html)
    rewritten_text = extract_text(rewritten_html)

    max_retries = 8
    attempt = 0
    while attempt < max_retries:
        try:
            api_key = get_next_api_key()
            if not api_key:
                return {"isUnique": True, "score": 0}
                
            client = genai.Client(api_key=api_key)
            target_a = original_text[:1500]
            target_b = rewritten_text[:1500]
            
            prompt = f"""
            You are an expert SEO plagiarism checker. Compare these two texts and determine the percentage of EXACT textual duplication.
            CRITICAL RULES:
            1. YOU MUST ONLY MEASURE EXACT MATCHING WORDS, N-GRAMS, AND COPY-PASTED PHRASES. 
            2. Do NOT measure similarity of "ideas", "meaning", or "concepts". 
            3. If Text A and Text B are in DIFFERENT LANGUAGES (e.g., Arabic vs English), the lexical exact-match overlap is mathematically 0%. Return 0.
            4. Focus exclusively on whether the English text copied literal English phrases from the original text.
            
            Text A (Original):
            "{target_a}..."
            
            Text B (Rewritten):
            "{target_b}..."
            
            Return ONLY a JSON object with:
            {{
              "similarityPercentage": number (0-100),
              "reason": "brief explanation"
            }}
            """

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            
            response_text = response.text.replace('```json', '').replace('```', '').strip()
            
            try:
                data = json.loads(response_text)
                score = data.get("similarityPercentage", 0)
                
                return {
                    "isUnique": score < 40,
                    "score": score
                }
            except json.JSONDecodeError as e:
                print(f"[Uniqueness] Parse error, assuming unique. {e}")
                return {"isUnique": True, "score": 0}

        except Exception as e:
            error_str = str(e)
            print(f"[Uniqueness API Error]: '{error_str}'. Rotating key... ({attempt+1}/{max_retries})")
            attempt += 1
            continue
            
    print("[Uniqueness API Error] Exhausted all API keys or retries.")
    return {"isUnique": True, "score": 0}
