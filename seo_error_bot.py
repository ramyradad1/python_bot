#!/usr/bin/env python3
"""
=============================================================================
  SEO Content Automation Bot — High-CPC IT Troubleshooting Focus
  Python 3.14 | Gemini 2.5 Flash + Imagen 3.0 | DuckDuckGo Discovery
=============================================================================
  Production-ready pipeline that:
    1. Auto-discovers high-value forum posts via DuckDuckGo keyword search
    2. Scrapes error codes, symptoms, and solutions from IT forums
    3. Generates unique SEO articles via Gemini 2.5 Flash
    4. Creates photorealistic thumbnails via Imagen 3.0
    5. Saves all outputs locally with robust error handling & logging
    
  (Dashboard Integrated Version)
=============================================================================
"""

import os
import re
import sys
import uuid
import random
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag
from google import genai
from google.genai import types

# ── Dashboard Integration Imports ──
from bot.logger import log_info
from bot.key_manager import get_next_api_key

# ──────────────────────────────────────────────────────────────────────────────
# Configuration & Constants
# ──────────────────────────────────────────────────────────────────────────────

# Output directory for generated articles & images
OUTPUT_DIR = Path(os.path.join(os.path.dirname(__file__), "output"))
ARTICLES_DIR = OUTPUT_DIR / "articles"
IMAGES_DIR = OUTPUT_DIR / "images"

# HTTP request settings
REQUEST_TIMEOUT = 20  # seconds
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
}

# ──────────────────────────────────────────────────────────────────────────────
# HIGH-VALUE NICHE KEYWORD DATABASE ($10-$60+ CPC)
# ──────────────────────────────────────────────────────────────────────────────

HIGH_VALUE_NICHES = {
    "cloud_computing": {
        "name": "Cloud Computing & Hosting",
        "cpc_range": "$15 – $40",
        "keywords": [
            "AWS migration errors",
            "Azure Active Directory sync fix",
            "Office 365 tenant migration guide",
            "Best enterprise cloud backup",
            "AWS S3 access denied error",
            "Google Cloud IAM permission denied",
            "Azure VM boot diagnostics failed",
            "Cloud database connection timeout",
        ],
    },
    "cybersecurity": {
        "name": "Cybersecurity & Data Recovery",
        "cpc_range": "$20 – $50",
        "keywords": [
            "Ransomware recovery steps",
            "RAID 5 data recovery tools",
            "Enterprise firewall configuration errors",
            "Fix Windows Server 2025 boot loop",
            "SSL certificate error fix",
            "Active Directory breach recovery",
            "BitLocker recovery key not working",
            "Zero-day vulnerability patch guide",
        ],
    },
    "enterprise_software": {
        "name": "Enterprise Software & SaaS Errors",
        "cpc_range": "$10 – $30",
        "keywords": [
            "Salesforce API integration failed",
            "Microsoft Exchange Server error 503 fix",
            "Cisco VPN connection timeout",
            "Docker container crash logs explained",
            "Kubernetes pod CrashLoopBackOff fix",
            "SAP HANA memory allocation error",
            "VMware ESXi purple screen of death",
            "Jenkins pipeline build failure fix",
        ],
    },
    "managed_it_services": {
        "name": "Managed IT Services & VoIP",
        "cpc_range": "$25 – $60+",
        "keywords": [
            "Small business VoIP phone systems",
            "Outsourced IT helpdesk pricing",
            "Network infrastructure setup cost",
            "SIP trunk configuration errors",
            "PBX system troubleshooting guide",
            "Managed SIEM setup for SMB",
            "SD-WAN vs MPLS comparison guide",
        ],
    },
}

# Search modifiers to append — drives the bot to forum/solution pages
SEARCH_MODIFIERS = ["Forum", "Solved", "Fix", "Error code", "Troubleshoot", "How to resolve"]

# Target forum sites for site-specific search
TARGET_FORUMS = [
    "techcommunity.microsoft.com",
    "community.spiceworks.com",
    "stackoverflow.com",
    "reddit.com/r/sysadmin",
    "reddit.com/r/ITSupport",
    "serverfault.com",
    "superuser.com",
    "learn.microsoft.com",
]

# Regex patterns for detecting IT error codes in text
ERROR_CODE_PATTERNS = [
    r"0x[0-9A-Fa-f]{4,8}",               # Windows hex codes: 0x80070005
    r"(?:Error|ERR)[_ ]?\d{3,5}",         # Error 1045, ERR_CONNECTION_REFUSED
    r"STOP[:\s]+0x[0-9A-Fa-f]+",          # BSOD stop codes
    r"\bHTTP\s*\d{3}\b",                  # HTTP 404, HTTP 500
    r"\b[45]\d{2}\s+(?:Error|Not Found|Internal Server|Forbidden|Bad Request)",
    r"ERRNO[:\s]*\d+",                    # Linux ERRNO codes
    r"(?:SQLSTATE|ORA-|MySQL Error)\s*[\[\(]?\d+",  # DB error codes
    r"CRITICAL|FATAL|EXCEPTION",          # Log-level keywords
    r"(?:Blue\s?Screen|BSOD|KERNEL_)",    # BSOD references
    r"(?:ERR_[A-Z_]+)",                   # Chrome-style error codes
]

# CSS selectors for boilerplate elements to strip
BOILERPLATE_SELECTORS = [
    "script", "style", "iframe", "noscript",
    "nav", "header", "footer",
    ".ad", ".advertisement", ".sidebar", ".widget",
    ".social-share", ".newsletter-signup", ".cookie-banner",
    ".nav", ".menu", ".breadcrumb", ".pagination",
    "#comments", ".comments-section",
    ".related-posts", ".author-bio",
]


# ──────────────────────────────────────────────────────────────────────────────
# Module 0: Keyword-Driven Source Discovery (DuckDuckGo)
# ──────────────────────────────────────────────────────────────────────────────

def search_for_sources(
    niche_key: str | None = None,
    custom_keyword: str | None = None,
    max_results_per_keyword: int = 5,
    stop_check=None,
) -> list[str]:
    """Auto-discover high-value forum posts via DuckDuckGo search."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        log_info(
            "[Search] 'duckduckgo-search' package not installed. Skipping auto-discovery."
        )
        return []

    discovered_urls: dict[str, bool] = {}

    if stop_check and stop_check(): return []

    # ── Determine which keywords to use ──
    if custom_keyword:
        keywords = [custom_keyword]
        log_info(f"[Search] Using custom keyword: '{custom_keyword}'")
    else:
        if niche_key and niche_key in HIGH_VALUE_NICHES:
            niche = HIGH_VALUE_NICHES[niche_key]
        else:
            niche_key = random.choice(list(HIGH_VALUE_NICHES.keys()))
            niche = HIGH_VALUE_NICHES[niche_key]

        # Use only 2 keywords per run to save time in the automated pipeline
        keywords = random.sample(niche["keywords"], min(2, len(niche["keywords"])))
        log_info(
            f"[Search] Selected niche: {niche['name']} (CPC: {niche['cpc_range']})"
        )

    # ── Search for each keyword with modifiers ──
    with DDGS() as ddgs:
        for keyword in keywords:
            if stop_check and stop_check(): break

            modifier = random.choice(SEARCH_MODIFIERS)
            query = f"{keyword} {modifier}"

            if random.random() < 0.5:
                target_site = random.choice(TARGET_FORUMS)
                query = f"site:{target_site} {keyword} {modifier}"

            try:
                log_info(f"[Search] Querying: '{query}'")
                results = ddgs.text(
                    query,
                    max_results=max_results_per_keyword,
                    region="us-en",
                )

                for result in results:
                    url = result.get("href", "")
                    if url and url.startswith("http"):
                        skip_patterns = [
                            "/login", "/signup", "/register", "/pricing",
                            "youtube.com", "facebook.com", "twitter.com",
                            ".pdf", ".zip", ".exe",
                        ]
                        if not any(pat in url.lower() for pat in skip_patterns):
                            discovered_urls[url] = True

                log_info(f"[Search] Found {len(results)} result(s) for '{keyword}'.")

            except Exception as e:
                log_info(f"[Search] Query failed for '{query}': {e}")
                continue

    urls = list(discovered_urls.keys())
    log_info(
        f"[Search] Discovery complete: {len(urls)} unique URL(s) found."
    )
    return urls


# ──────────────────────────────────────────────────────────────────────────────
# Module 1: Web Scraping — IT Error Code Extraction
# ──────────────────────────────────────────────────────────────────────────────

def scrape_error_data(url: str, stop_check=None) -> dict | None:
    """Scrape a single URL and extract structured IT error/troubleshooting data."""
    if stop_check and stop_check(): return None

    try:
        log_info(f"[Scraper] Fetching: {url}")

        if not url.startswith("http"):
            url = f"https://{url}"

        response = requests.get(
            url,
            headers=HTTP_HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for selector in BOILERPLATE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()

        title = ""
        title_el = soup.select_one("h1, title")
        if title_el:
            title = title_el.get_text(strip=True)

        content_node = None
        content_selectors = [
            "main article", "article", ".post-content", ".entry-content",
            ".article-body", ".content-body", "main", "#main-content",
            '[role="main"]', ".doc-content", "#bodyContent",
            ".question-body", ".answer-body", ".post-text",
            ".comment-body", ".md",
            ".lia-message-body", ".message-body",
        ]
        for sel in content_selectors:
            node = soup.select_one(sel)
            if node and len(node.get_text(strip=True)) > 100:
                content_node = node
                break

        if not content_node:
            content_node = soup.body or soup

        full_text = content_node.get_text(separator="\n", strip=True)

        error_codes = set()
        for pattern in ERROR_CODE_PATTERNS:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            error_codes.update(matches)
        error_codes = sorted(error_codes)

        symptom_keywords = [
            "error", "fail", "crash", "freeze", "not working", "unable to",
            "cannot", "issue", "problem", "symptom", "blue screen", "bsod",
            "unexpected", "stopped", "hung", "timeout", "refused", "denied",
            "blocked", "corrupted", "missing", "broken", "exception",
        ]
        symptoms = []
        for p in content_node.find_all(["p", "li", "td"]):
            text = p.get_text(strip=True).lower()
            if any(kw in text for kw in symptom_keywords) and len(text) > 30:
                clean_text = p.get_text(strip=True)
                if clean_text not in symptoms:
                    symptoms.append(clean_text)

        symptoms = symptoms[:20]

        solutions = []
        for ol in content_node.find_all("ol"):
            steps = []
            for li in ol.find_all("li", recursive=False):
                step_text = li.get_text(strip=True)
                if len(step_text) > 10:
                    steps.append(step_text)
            if steps:
                solutions.append({"type": "steps", "content": steps})

        for code in content_node.find_all(["code", "pre"]):
            code_text = code.get_text(strip=True)
            if len(code_text) > 5:
                solutions.append({"type": "command", "content": code_text})

        solution_headings = content_node.find_all(
            ["h2", "h3", "h4"],
            string=re.compile(
                r"fix|solution|resolve|repair|troubleshoot|workaround|how to|steps|method",
                re.IGNORECASE,
            ),
        )
        for heading in solution_headings:
            sibling = heading.find_next_sibling()
            while sibling and isinstance(sibling, Tag):
                if sibling.name in ("ul", "ol"):
                    items = [
                        li.get_text(strip=True)
                        for li in sibling.find_all("li")
                        if len(li.get_text(strip=True)) > 10
                    ]
                    if items:
                        solutions.append({
                            "type": "fix",
                            "heading": heading.get_text(strip=True),
                            "content": items,
                        })
                    break
                elif sibling.name in ("h2", "h3", "h4"):
                    break
                sibling = sibling.find_next_sibling()

        if not error_codes and not symptoms and not solutions:
            return None

        return {
            "title": title,
            "error_codes": error_codes,
            "symptoms": symptoms,
            "solutions": solutions,
            "source_url": url,
        }

    except requests.Timeout:
        log_info(f"[Scraper] Timeout requesting: {url}")
        return None
    except requests.HTTPError as e:
        log_info(f"[Scraper] HTTP {e.response.status_code} for: {url}")
        return None
    except Exception as e:
        log_info(f"[Scraper] Failed to scrape {url}: {e}")
        return None


def scrape_multiple_sources(urls: list[str], max_sources: int = 5, stop_check=None) -> list[dict]:
    """Scrape multiple URLs up to a limit."""
    log_info(f"[Scraper] Starting batch scrape of {len(urls)} URL(s)...")
    results = []

    for i, url in enumerate(urls, 1):
        if stop_check and stop_check(): break

        if len(results) >= max_sources:
            log_info(f"[Scraper] Reached {max_sources} successful scrapes, stopping.")
            break

        data = scrape_error_data(url, stop_check)
        if data:
            results.append(data)
            log_info(f"[Scraper] ✓ [{len(results)}/{max_sources}] {data['title'][:60]}")
        else:
            log_info(f"[Scraper] ✗ Skipped (no data): {url[:80]}")

    log_info(f"[Scraper] Batch complete: {len(results)} source(s) scraped successfully.")
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Module 2: Content Generation — Gemini 2.5 Flash SEO Article
# ──────────────────────────────────────────────────────────────────────────────

def generate_article(
    client: genai.Client,
    scraped_data: list[dict],
    target_niche: str = "",
    stop_check=None
) -> str | None:
    """Generate a comprehensive, SEO-optimized troubleshooting article using Gemini 2.5 Flash."""
    if stop_check and stop_check(): return None

    if not scraped_data:
        log_info("[Generator] No scraped data provided. Cannot generate article.")
        return None

    data_brief = ""
    for entry in scraped_data:
        data_brief += f"\n--- Source: {entry['source_url']} ---\n"
        data_brief += f"Title: {entry['title']}\n"

        if entry["error_codes"]:
            codes = ", ".join(entry["error_codes"][:15])
            data_brief += f"Error Codes: {codes}\n"

        if entry["symptoms"]:
            data_brief += "Symptoms:\n"
            for s in entry["symptoms"][:10]:
                data_brief += f"  - {s}\n"

        if entry["solutions"]:
            data_brief += "Solutions Found:\n"
            for sol in entry["solutions"][:8]:
                if sol["type"] == "steps":
                    for step in sol["content"][:6]:
                        data_brief += f"  Step: {step}\n"
                elif sol["type"] == "command":
                    data_brief += f"  Command: {sol['content'][:200]}\n"
                elif sol["type"] == "fix":
                    data_brief += f"  Fix ({sol.get('heading', 'N/A')}):\n"
                    for item in sol["content"][:5]:
                        data_brief += f"    - {item}\n"

    if len(data_brief) > 15000:
        data_brief = data_brief[:15000] + "\n... [truncated for brevity]"

    niche_context = ""
    if target_niche:
        niche_context = f"\nTARGET NICHE: {target_niche} (high-CPC, commercial-intent audience)\n"

    prompt = f"""You are an SEO Expert and Senior Tech Blogger specializing in IT troubleshooting.
{niche_context}
YOUR TASK: Using the raw technical data below, write a **100% unique, comprehensive troubleshooting guide** article. This must NOT be a direct translation, rewrite, or summary of the source material. You must synthesize the information into an original, authoritative guide.

=== RAW TECHNICAL DATA ===
{data_brief}

=== ARTICLE REQUIREMENTS ===

1. **FORMAT**: Output clean HTML using ONLY these tags: <h2>, <h3>, <p>, <ul>, <li>, <ol>, <strong>, <em>, <code>, <blockquote>. Do NOT include <html>, <head>, <body>, or <doctype> tags.

2. **STRUCTURE** (follow this exact structure):
   - <h2> — A compelling, SEO-friendly main title about the error/problem
   - <p> — Introduction paragraph: what this error is and why it matters (include primary keyword in the first 100 words)
   - <h2>What Causes [Error Name/Code]?</h2> — Root cause analysis
   - <h2>Symptoms You'll Notice</h2> — Observable signs of the problem
   - <h2>Step-by-Step Troubleshooting Guide</h2> — Numbered, actionable fixes
     - Use <h3> for each major fix method
     - Include any relevant commands in <code> tags
   - <h2>Advanced Solutions</h2> — For power users (registry edits, CLI tools, etc.)
   - <h2>How to Prevent This Error</h2> — Preventive measures
   - <h2>Final Verdict</h2> — Summary of the best approach, when to seek professional help

3. **SEO RULES**:
   - Write at minimum 900 words
   - Use the primary error code/keyword naturally 4-6 times throughout
   - Each <h2> must contain relevant keywords
   - Write short paragraphs (2-4 sentences max)
   - Use bullet points for scannable content
   - Include at least one <blockquote> with an important technical note or warning

4. **WRITING STYLE**:
   - Write like a senior IT professional explaining to a competent colleague
   - Be direct, practical, and authoritative
   - No fluff, no filler, no generic introductions
   - Use contractions naturally (don't, won't, it's)
   - Avoid AI-sounding phrases: "In today's world", "It's worth noting", "landscape", "crucial", "leverage", "delve", "Moreover", "Furthermore"

5. **ORIGINALITY**:
   - Do NOT copy sentences from the source data
   - Synthesize and restructure the information completely
   - The article must pass plagiarism checks

Return ONLY the HTML content. No markdown, no code blocks, no explanations outside the HTML."""

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        if stop_check and stop_check(): break

        try:
            api_key = get_next_api_key()
            if not api_key:
                log_info("[Generator] No Gemini API key available from Key Manager.")
                return None
                
            client = genai.Client(api_key=api_key)
            log_info(f"[Generator] Sending prompt to Gemini 2.5 Flash (attempt {attempt}/{max_retries})...")
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )

            if response and response.text:
                article_html = response.text.strip()
                article_html = re.sub(r"^```html\s*", "", article_html, flags=re.IGNORECASE)
                article_html = re.sub(r"```\s*$", "", article_html)

                word_count = len(article_html.split())
                log_info(f"[Generator] ✓ Article generated successfully (~{word_count} words).")
                return article_html

        except Exception as e:
            log_info(f"[Generator] API error on attempt {attempt}: {e}")

    log_info("[Generator] ✗ Failed to generate article after all retries.")
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Module 3: Image Generation — Imagen 3.0 Thumbnail
# ──────────────────────────────────────────────────────────────────────────────

def extract_topic(article_html: str) -> str:
    """Extract the main topic from the generated article HTML."""
    try:
        soup = BeautifulSoup(article_html, "html.parser")
        first_h2 = soup.find("h2")
        if first_h2:
            topic = first_h2.get_text(strip=True)
            log_info(f"[Image] Extracted topic: {topic}")
            return topic
    except Exception as e:
        log_info(f"[Image] Failed to extract topic from HTML: {e}")

    return "IT troubleshooting computer error"


def generate_thumbnail(client: genai.Client, topic: str, stop_check=None) -> str | None:
    """Generate a photorealistic thumbnail image using Gemini Imagen 3.0."""
    if stop_check and stop_check(): return None

    image_prompt = (
        f"A photorealistic, high-resolution editorial photograph representing "
        f"the IT concept: '{topic}'. "
        f"The scene should depict a professional IT environment — a modern server room, "
        f"a technician's workstation with diagnostic screens, or a close-up of a computer "
        f"displaying an error screen. "
        f"Lighting should be dramatic and cinematic with cool blue tones. "
        f"Style: sharp focus, 8K resolution, professional tech magazine cover quality. "
        f"NO cartoons, NO illustrations, NO text overlays, NO watermarks."
    )

    max_retries = 2
    for attempt in range(1, max_retries + 1):
        if stop_check and stop_check(): break

        try:
            log_info(f"[Image] Generating thumbnail via Imagen 3.0 (attempt {attempt}/{max_retries})...")

            api_key = get_next_api_key()
            if not api_key:
                return None
                
            client = genai.Client(api_key=api_key)
            response = client.models.generate_images(
                model="imagen-3.0-generate-001",
                prompt=image_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/jpeg",
                ),
            )

            if response and response.generated_images:
                image_bytes = response.generated_images[0].image.data

                IMAGES_DIR.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"thumbnail_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
                filepath = IMAGES_DIR / filename

                with open(filepath, "wb") as f:
                    f.write(image_bytes)

                file_size_kb = len(image_bytes) / 1024
                log_info(f"[Image] ✓ Thumbnail saved: {filepath} ({file_size_kb:.1f} KB)")
                
                # Also upload to Supabase if configured in the main bot
                try:
                    from bot.image_handler import upload_to_supabase
                    public_url = upload_to_supabase(image_bytes, filename)
                    if public_url:
                        log_info(f"[Image] ✓ Thumbnail mapped to CDNs: {public_url}")
                except ImportError:
                    pass

                return str(filepath)

        except Exception as e:
            log_info(f"[Image] Imagen 3.0 error on attempt {attempt}: {e}")

    log_info("[Image] ✗ Failed to generate thumbnail after all retries.")
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Module 4: Output Saving
# ──────────────────────────────────────────────────────────────────────────────

def save_article(article_html: str, topic: str) -> str | None:
    """Save the generated article HTML to a local file with professional styling."""
    try:
        ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

        slug = re.sub(r"[^a-zA-Z0-9]+", "-", topic.lower()).strip("-")[:60]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{slug}_{timestamp}.html"
        filepath = ARTICLES_DIR / filename

        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{topic}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            line-height: 1.8;
            color: #1a1a2e;
            background: #f8f9fa;
            max-width: 820px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }}
        h2 {{ color: #0f3460; margin: 2rem 0 1rem; padding-bottom: 0.5rem; border-bottom: 3px solid #e94560; font-size: 1.6rem; }}
        h3 {{ color: #16213e; margin: 1.5rem 0 0.75rem; font-size: 1.25rem; }}
        p {{ margin-bottom: 1rem; }}
        ul, ol {{ margin: 1rem 0 1rem 1.5rem; }}
        li {{ margin-bottom: 0.5rem; }}
        code {{ background: #1a1a2e; color: #00ff88; padding: 0.2rem 0.5rem; border-radius: 4px; font-family: monospace; }}
        pre code {{ display: block; padding: 1rem; overflow-x: auto; margin: 1rem 0; }}
        blockquote {{ border-left: 4px solid #e94560; background: #eef2ff; padding: 1rem 1.5rem; margin: 1.5rem 0; font-style: italic; border-radius: 0 8px 8px 0; }}
    </style>
</head>
<body>
{article_html}
</body>
</html>"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_html)

        log_info(f"[Output] ✓ Article saved: {filepath}")
        return str(filepath)

    except Exception as e:
        log_info(f"[Output] Failed to save article: {e}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Main Pipeline Orchestrator (Dashboard Integrated)
# ──────────────────────────────────────────────────────────────────────────────

def run_seo_bot(stop_check=None):
    """
    Main entry point triggered by the Nerve Center dashboard.
    Full pipeline: Search → Scrape → Generate → Image → Publish to Supabase.
    """
    if stop_check and stop_check(): return

    log_info("=" * 50)
    log_info("  [SEO Error Bot] 🎯 بدء صيد الأخطاء التقنية ذات الـ CPC العالي")
    log_info("=" * 50)

    start_time = datetime.now()

    # ── Load SEO Settings ──
    import json as _json
    _settings_path = os.path.join(os.path.dirname(__file__), "bot", "dynamic_settings.json")
    if not os.path.exists(_settings_path):
        _settings_path = os.path.join(os.path.dirname(__file__), "bot/dynamic_settings.json")
    try:
        with open(_settings_path, "r", encoding="utf-8") as _f:
            seo_settings = _json.load(_f)
    except Exception:
        seo_settings = {}
    
    author_name = seo_settings.get("author_name", "Ramy Radad")

    # ── Step 1: Load API Key ──
    api_key = get_next_api_key()
    if not api_key:
        log_info("[SEO Error Bot] ✗ No Gemini API key found from Key Manager. Aborting.")
        return
    client = genai.Client(api_key=api_key)

    # ── Step 2: Select Niche & Discover Sources ──
    selected_niche = os.getenv("TARGET_NICHE")
    custom_kw = os.getenv("CUSTOM_KEYWORD")
    custom_urls_str = os.getenv("SOURCE_URLS")

    if custom_urls_str:
        source_urls = [u.strip() for u in custom_urls_str.split(",") if u.strip()]
        niche_name = "Custom Sources"
    else:
        source_urls = search_for_sources(
            niche_key=selected_niche,
            custom_keyword=custom_kw,
            max_results_per_keyword=3,
            stop_check=stop_check,
        )

        if selected_niche and selected_niche in HIGH_VALUE_NICHES:
            niche_name = HIGH_VALUE_NICHES[selected_niche]["name"]
        elif custom_kw:
            niche_name = custom_kw
        else:
            niche_name = "Random Niche"

    if not source_urls:
        log_info("[SEO Error Bot] ✗ No source URLs found. Skipping cycle.")
        return

    # ── Step 3: Scrape Source URLs ──
    scraped_data = scrape_multiple_sources(source_urls, max_sources=3, stop_check=stop_check)

    if not scraped_data:
        log_info("[SEO Error Bot] ✗ No data scraped from sources. Skipping cycle.")
        return

    # ── Step 4: Generate Article ──
    article_html = generate_article(client, scraped_data, target_niche=niche_name, stop_check=stop_check)

    if not article_html:
        log_info("[SEO Error Bot] ✗ Article generation failed.")
        return

    # ── Step 5: Generate Thumbnail ──
    topic = extract_topic(article_html)
    thumbnail_path = generate_thumbnail(client, topic, stop_check=stop_check)

    # ── Step 6: Save Locally ──
    article_path = save_article(article_html, topic)
    
    # ── Step 7: Inject E-E-A-T Author Bio ──
    author_bio_html = f"""
    <div class="author-bio" style="margin-top: 3rem; padding: 1.5rem; background: #f8f9fa; border-left: 4px solid #0f3460; border-radius: 8px;">
        <h3 style="margin-top: 0; color: #16213e;">About the Author: {author_name}</h3>
        <p style="margin-bottom: 0; font-size: 0.95rem; line-height: 1.6;">
            {author_name} is a Senior Systems Engineer with extensive hands-on experience in enterprise IT infrastructure. 
            He specializes in managing <strong>Office 365 environments</strong>, deploying advanced <strong>Access Points</strong> and networking solutions, 
            and integrating <strong>Smart Locks</strong> and <strong>Biometric attendance devices</strong>. 
            Through his work, he has resolved hundreds of complex technical issues for businesses worldwide.
        </p>
    </div>
    """
    article_html_with_bio = article_html + author_bio_html
    
    # ── Step 8: Publish to Supabase ──
    try:
        from bot.supabase_client import get_supabase_client
        from bot.publisher import sanitize_slug
        supabase = get_supabase_client()
        
        if supabase:
            from datetime import timezone
            slug = re.sub(r"[^a-zA-Z0-9]+", "-", topic.lower()).strip("-")[:80]
            
            # Try to get a hero image URL
            hero_image_url = ""
            if thumbnail_path:
                try:
                    from bot.image_handler import upload_to_supabase
                    with open(thumbnail_path, "rb") as img_f:
                        img_bytes = img_f.read()
                    hero_image_url = upload_to_supabase(img_bytes, os.path.basename(thumbnail_path)) or ""
                except Exception as e:
                    log_info(f"[SEO Error Bot] ⚠️ Image upload failed: {e}")
            
            # Extract tags from niche
            tags = []
            if niche_name and niche_name != "Random Niche":
                tags = [t.strip() for t in niche_name.replace("&", ",").split(",") if t.strip()]
            for d in scraped_data[:2]:
                for code in d.get("error_codes", [])[:3]:
                    tags.append(code)
            
            article_doc = {
                "title": topic,
                "slug": slug,
                "metaDescription": f"Complete step-by-step guide to troubleshoot and fix {topic}. Expert solutions from a Senior Systems Engineer.",
                "content": article_html_with_bio,
                "category": niche_name,
                "tags": tags[:10],
                "author": author_name,
                "sourceUrl": source_urls[0] if source_urls else "",
                "heroImage": hero_image_url,
                "views": 0,
                "status": "published",
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "publishedAt": datetime.now(timezone.utc).isoformat(),
            }
            
            supabase.table('articles').insert(article_doc).execute()
            log_info(f"[SEO Error Bot] ✅ Published to Supabase: /articles/{slug}")
            
            # Internal linking
            if seo_settings.get("internal_linking_enabled", True):
                try:
                    from bot.internal_linker import inject_internal_links
                    inject_internal_links(topic, slug, tags)
                except Exception as e:
                    log_info(f"[SEO Error Bot] ⚠️ Internal linking error: {e}")
        else:
            log_info("[SEO Error Bot] ⚠️ Supabase not configured. Article saved locally only.")
            
    except Exception as e:
        log_info(f"[SEO Error Bot] ⚠️ Supabase publish failed: {e}. Article saved locally.")

    # ── Pipeline Summary ──
    elapsed = (datetime.now() - start_time).total_seconds()
    log_info(f"[SEO Error Bot] ✅ اكتملت الدورة في {elapsed:.1f} ثانية")
    log_info(f"  - النيتش: {niche_name}")
    log_info(f"  - المصادر المسحوبة: {len(scraped_data)}")
    log_info(f"  - المقال: {article_path or 'فشل'}")
    log_info(f"  - الصورة: {thumbnail_path or 'فشلت'}")
    log_info(f"  - الكاتب: {author_name}")
    log_info("=" * 50)


if __name__ == "__main__":
    run_seo_bot()
