import json
from google import genai
from .key_manager import get_next_api_key
from .config import load_config
from .state import GLOBAL_STOP_EVENT
from .logger import log_info
from .seo_agent import load_dynamic_settings

def rewrite_article(original_title: str, original_html: str, 
                    tone: str = 'Professional, highly engaging, and indistinguishable from an expert human writer') -> dict | None:
    try:
        if GLOBAL_STOP_EVENT.is_set(): return None
        
        config = load_config()
        ai_model = config.get("ai_model", "Google Gemini 2.5 Flash")
        depth = int(config.get("editorial_depth", 50))
        translate = config.get("auto_translate", False)
        
        model_name = 'gemini-1.5-pro-latest' if '1.5 Pro' in ai_model else 'gemini-2.5-flash'
        
        depth_instructions = "Rewrite the article while closely matching the original length."
        if depth > 75:
            depth_instructions = "Deep Synthesis: Expand heavily on the concepts, add comprehensive context, and create a much longer, deeply analytical article."
        elif depth < 25:
            depth_instructions = "Light Aggregation: Summarize the article concisely. Keep it brief, directly to the point, and highly scannable."
            
        translate_instructions = "Rewrite completely in fluent, engaging **American English**."
        if translate:
            translate_instructions = "Rewrite and translate everything completely into fluent, engaging **Arabic** suitable for a modern tech magazine."
            
        settings = load_dynamic_settings()
        dynamic_rules = settings.get("dynamic_seo_rules", [])
        rules_text = ""
        if dynamic_rules:
            rules_text = "\nLATEST GOOGLE ALGORITHM RULES YOU MUST FOLLOW:\n"
            for i, rule in enumerate(dynamic_rules, 1):
                rules_text += f"{i}. {rule}\n"
            
        prompt = f"""
        You are a veteran tech journalist with 15+ years writing for top publications.
        You have a sharp, opinionated voice. You write like a real person — not a machine.
        Your task: take this article and rewrite it as YOUR OWN original piece for Technify magazine.
        {translate_instructions}
        
        Original Article (Title): {original_title}
        Original Content (HTML):
        {original_html}

        === WRITING STYLE (CRITICAL — THIS IS THE MOST IMPORTANT PART) ===
        You MUST write like a real human journalist. Follow these rules strictly:
        - Use contractions naturally (don't, won't, it's, they're, that's)
        - Vary your sentence length dramatically. Mix short punchy sentences with longer flowing ones.
        - Start some sentences with "And", "But", "So", "Look," or "Here's the thing" — like a real writer would.
        - Include personal opinions and mild editorial takes (e.g., "Frankly, this is long overdue")
        - Use rhetorical questions occasionally (e.g., "But does any of this actually matter?")
        - Avoid these AI giveaway phrases at ALL COSTS: "In today's rapidly evolving", "It's worth noting", "landscape", "paradigm", "delve", "crucial", "Moreover", "Furthermore", "In conclusion", "leveraging", "robust", "pivotal", "realm", "It is important to", "One might argue"
        - Write like you're explaining to a smart friend over coffee, not presenting to a boardroom
        - Use colloquial transitions: "Now,", "Thing is,", "The kicker?", "Here's where it gets interesting"
        - Add a touch of humor or wit where appropriate
        - DO NOT use bullet points excessively. Prefer flowing paragraphs with occasional lists.
        - The opening paragraph should hook the reader with a bold statement, question, or surprising fact — NOT a generic introduction.
        
        === CONTENT RULES ===
        1. **Depth**: {depth_instructions}
        2. **Tone**: {tone}.
        3. **HTML Format**: Use <h2>, <h3>, <p>, <ul>, <blockquote>. No <html> or <body> tags.
        
        === ADVANCED SEO (ADSENSE-READY — CRITICAL) ===
        - Place the PRIMARY keyword naturally in the first 100 words, in at least ONE <h2>, and in the meta description.
        - Use 2-4 <h2> subheadings and 1-2 <h3> subheadings. Each must be descriptive and contain related keywords.
        - Write a UNIQUE, compelling meta description (120-155 chars) that contains the main keyword and a call-to-action.
        - Use short paragraphs (2-4 sentences max). Break up walls of text.
        - Add a Table of Contents hint: at the top, include a brief summary (2-3 sentences) of what the reader will learn.
        - Include at least ONE <blockquote> with an expert opinion or key statistic.
        - Internal linking: mention "Technify" or "our coverage" naturally 1-2 times to hint at being a real publication.
        - Use semantic HTML: <strong> for emphasis, <em> for nuance — NOT for keyword stuffing.
        - The article MUST be at least 800 words for AdSense eligibility.
        - Add a clear, human-written conclusion paragraph that summarizes key takeaways (but DO NOT start with "In conclusion").
        - NO thin content, NO duplicate paragraphs, NO filler text.
        {rules_text}

        Return output EXCLUSIVELY as strict, valid JSON:
        {{
          "title": "A punchy, engaging title a human editor would write (max 60 chars)",
          "slug": "url-slug-in-english-with-hyphens",
          "metaDescription": "A click-worthy meta description (max 155 chars)",
          "content": "Full rewritten article in HTML",
          "category": "One category (e.g., Technology, AI, Gadgets, Science)",
          "tags": ["tag1", "tag2", "tag3", "tag4"]
        }}
        
        CRITICAL JSON RULES:
        - Escape all internal double quotes inside strings with \\".
        - Use single quotes for HTML attributes (e.g., <div class='wrapper'>).
        - NO literal newlines inside JSON string values. Use \\n or single-line strings.
        - Return ONLY raw JSON. No markdown code blocks.
        """

        max_retries = 8
        attempt: int = 0
        
        while attempt < max_retries:
            if GLOBAL_STOP_EVENT.is_set(): return None
            
            api_key = get_next_api_key()
            if not api_key:
                log_info("[Rewriter Error]: No API keys available.")
                return None
                
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(model=model_name, contents=prompt)
                
                response_text = response.text
                clean_json_string = response_text.replace('```json', '').replace('```', '').strip()
                
                try:
                    parsed_data = json.loads(clean_json_string)
                    return parsed_data
                except json.JSONDecodeError:
                    log_info(f"[Rewriter Error]: Failed to parse AI JSON response.")
                    return None
                    
            except Exception as e:
                error_str = str(e)
                log_info(f"[Rewriter Error]: API Error '{error_str}'. Rotating API key automatically... ({attempt + 1}/{max_retries})")
                attempt += 1
                continue
                    
        log_info("[Rewriter Error]: Exhausted all available API keys or retries.")
        return None

    except Exception as e:
        print(f"[Rewriter Error]: {e}")
        return None

def generate_image_alt_text(article_context: str, image_url: str) -> str:
    return f"Illustrative image related to {article_context}"
