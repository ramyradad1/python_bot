import json
from google import genai
from .key_manager import get_next_api_key
from .logger import log_info
from .seo_agent import load_dynamic_settings

def generate_solution_article(problem: dict) -> dict | None:
    """
    Filters the problem and acts as an expert consultant to generate a step-by-step solution.
    """
    settings = load_dynamic_settings()
    dynamic_rules = settings.get("dynamic_seo_rules", [])
    rules_text = ""
    if dynamic_rules:
        rules_text = "\nLATEST GOOGLE ALGORITHM RULES YOU MUST FOLLOW:\n"
        for i, rule in enumerate(dynamic_rules, 1):
            rules_text += f"{i}. {rule}\n"
            
    prompt = f"""
    You are an elite Senior Developer and Tech Support Expert.
    A user is facing the following technical problem on {problem.get('source', 'the web')}:
    
    TITLE: {problem.get('title')}
    PROBLEM DESCRIPTION: {problem.get('body')}
    
    Your task:
    1. Write a comprehensive, step-by-step authoritative 'How-To' guide that completely solves this problem.
    2. Format the response as an engaging blog post for a tech website.
    3. Include a "Why this happens" section and a "Step-by-Step Fix" section.
    
    {rules_text}
    
    Output strictly in JSON:
    {{
      "title": "How to Fix: [Problem] (Engaging Title)",
      "slug": "how-to-fix-problem-slug",
      "metaDescription": "Learn how to solve the [Problem] in simple steps...",
      "content": "The full HTML body starting with <h2>...",
      "category": "Tech Support",
      "tags": ["Fix", "Tutorial", "Tech Support"]
    }}
    
    CRITICAL JSON RULES:
    - Escape internal double quotes with \\".
    - ONLY return raw JSON without markdown blocks like ```json.
    """
    
    max_retries = 8
    attempt = 0
    while attempt < max_retries:
        api_key = get_next_api_key()
        if not api_key:
            return None
            
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            response_text = response.text.replace('```json', '').replace('```', '').strip()
            parsed = json.loads(response_text)
            log_info(f"[QnA Handler] Successfully analyzed and solved problem: '{parsed.get('title')}'")
            return parsed
        except Exception as e:
            error_str = str(e)
            log_info(f"[QnA Handler] Engine failed to solve problem: '{error_str}'. Rotating key... ({attempt+1}/{max_retries})")
            attempt += 1
            continue
            
    log_info("[QnA Handler] Exhausted all API keys or retries.")
    return None

if __name__ == "__main__":
    mock_problem = {"title": "Test Error 404", "body": "My page constantly shows 404.", "source": "Web"}
    print(generate_solution_article(mock_problem))
