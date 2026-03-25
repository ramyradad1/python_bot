import sys
import os

# Ensure bot modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.scraper import scrape_latest_links, scrape_article

test_sources = [
    "https://www.theverge.com",
    "https://www.tech-wd.com",
    "https://aitnews.com"
]

for source in test_sources:
    print(f"\n--- Testing source: {source} ---")
    links = scrape_latest_links(source, max_links=5)
    print(f"Found {len(links)} links.")
    for idx, link in enumerate(links):
        print(f"  {idx+1}: {link}")
        
    if links:
        for idx, link in enumerate(links):
            print(f"Attempting to scrape content of link {idx+1}: {link}")
            data = scrape_article(link)
            if data:
                print(f"  SUCCESS! Title: {data.get('title')}")
                print(f"  Content snippet: {data.get('content')[:100]}...")
                break # Stop at the first successful article
            else:
                print("  Failed or too old. Trying next...")
