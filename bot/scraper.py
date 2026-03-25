"""
Scraper module: Fetches and extracts article content from web pages.
Uses requests with timeout protection. No multiprocessing to avoid Windows hangs.
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone, timedelta
from bot.config import load_config
from bot.logger import log_info

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Cache-Control': 'no-cache',
}


def fetch_url(url: str, timeout: int = 15) -> requests.Response:
    """Simple HTTP GET with timeout. No curl_cffi, no multiprocessing."""
    if not url.startswith("http"):
        url = "https://" + url
    resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    return resp


def scrape_article(url: str) -> dict | str | None:
    """Scrape a single article page and return structured data."""
    try:
        response = fetch_url(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. Extract Title
        title_element = soup.select_one('h1.article-title, h1.title, article h1, h1')
        title = title_element.get_text(strip=True) if title_element else (soup.title.string.strip() if soup.title else "")

        # Check max age
        config = load_config()
        max_age_hours = config.get("max_age_hours", 24)

        publish_time_str = None
        meta_pub = soup.select_one('meta[property="article:published_time"]')
        if meta_pub:
            publish_time_str = meta_pub.get('content')
        else:
            time_tag = soup.select_one('time[pubdate], time[datetime]')
            if time_tag:
                publish_time_str = time_tag.get('datetime')

        if publish_time_str:
            try:
                clean_str = publish_time_str.strip().replace(" UTC", "").replace(" GMT", "")
                if " " in clean_str and "T" not in clean_str:
                    parts = clean_str.split(" ", 1)
                    if len(parts) == 2:
                        clean_str = f"{parts[0]}T{parts[1].replace(' ', '')}"

                pub_dt = datetime.fromisoformat(clean_str.replace("Z", "+00:00"))
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)

                now = datetime.now(timezone.utc)
                age = now - pub_dt
                if age > timedelta(hours=max_age_hours):
                    log_info(f"[Scraper] المقال قديم ({age.total_seconds() / 3600:.1f} ساعة). الحد: {max_age_hours}h")
                    return "too_old"
            except Exception as e:
                log_info(f"[Scraper] تحذير: فشل تحليل تاريخ النشر {publish_time_str}: {e}")

        # 2. Extract Content Body
        content_selectors = [
            'article .post-content',
            'article .entry-content',
            'article .c-entry-content',
            '.article-body',
            '.post-body',
            'main article',
            'article'
        ]

        content_node = None
        for selector in content_selectors:
            node = soup.select_one(selector)
            if node:
                content_node = node
                break

        if not content_node:
            log_info(f"[Scraper] لم يتم العثور على محتوى المقال في {url}")
            return None

        # Clean up
        for element in content_node.select('script, style, iframe, .ad, .advertisement, .social-share, .newsletter-signup'):
            element.decompose()

        # 3. Extract Images
        images = []
        for img in content_node.find_all('img'):
            src = img.get('src') or img.get('data-src')
            alt = img.get('alt') or title

            if src and 'data:image' not in src and 'pixel' not in src and 'spacer' not in src:
                absolute_url = urljoin(url, src)
                images.append({"url": absolute_url, "alt": alt.strip()})

        # 4. Extract clean HTML
        content_html = str(content_node)

        return {
            "title": title,
            "content": content_html.strip(),
            "images": images,
            "sourceUrl": url
        }

    except requests.Timeout:
        log_info(f"[Scraper] انتهت المهلة عند سحب {url}")
        return None
    except Exception as e:
        log_info(f"[Scraper] فشل سحب {url}: {e}")
        return None


def scrape_latest_links(source_url: str, max_links: int = 15) -> list[str]:
    """Scrape homepage/feed for article links."""
    try:
        response = fetch_url(source_url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        links_dict = {}
        base_url = f"{urlparse(source_url).scheme}://{urlparse(source_url).netloc}"

        for a_tag in soup.select('article a, .post-feed a, h2 a, h3 a'):
            href = a_tag.get('href')
            if href:
                if href.startswith('/'):
                    href = urljoin(base_url, href)

                if len(href) > len(base_url) + 10 and href.startswith('http'):
                    if '/category/' not in href and '/author/' not in href:
                        if href not in links_dict:
                            links_dict[href] = True

        return list(links_dict.keys())[:max_links]
    except requests.Timeout:
        log_info(f"[Scraper] انتهت المهلة عند جمع الروابط من {source_url}")
        return []
    except Exception as e:
        log_info(f"[Scraper] فشل جمع الروابط من {source_url}: {e}")
        return []


def scrape_reddit_links(subreddit: str, max_links: int = 5) -> list[str]:
    """Scrape top posts from a Reddit subreddit's JSON API for outbound article links."""
    try:
        sub_name = subreddit.replace("r/", "").strip()
        url = f"https://www.reddit.com/r/{sub_name}/hot.json?limit=25"
        headers = {'User-Agent': 'TechnifyBot/1.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        links = []
        for post in data.get("data", {}).get("children", []):
            post_data = post.get("data", {})
            post_url = post_data.get("url", "")
            is_self = post_data.get("is_self", True)
            score = post_data.get("score", 0)
            
            # Only grab outbound links (not self-posts) with decent engagement
            if not is_self and post_url.startswith("http") and score > 10:
                if "reddit.com" not in post_url and "imgur.com" not in post_url:
                    links.append(post_url)
        
        log_info(f"[Scraper] Reddit r/{sub_name}: {len(links)} outbound links found")
        return links[:max_links]
    except Exception as e:
        log_info(f"[Scraper] Reddit r/{subreddit} failed: {e}")
        return []


def scrape_rss_links(feed_url: str, max_links: int = 5) -> list[str]:
    """Parse an RSS/Atom feed and extract recent article links."""
    try:
        resp = fetch_url(feed_url, timeout=15)
        soup = BeautifulSoup(resp.text, 'xml')
        
        links = []
        # Try RSS format first
        items = soup.find_all('item')
        if not items:
            # Try Atom format
            items = soup.find_all('entry')
        
        for item in items:
            link_tag = item.find('link')
            if link_tag:
                href = link_tag.get('href') or link_tag.text
                if href and href.strip().startswith('http'):
                    links.append(href.strip())
        
        log_info(f"[Scraper] RSS {feed_url[:40]}...: {len(links)} entries found")
        return links[:max_links]
    except Exception as e:
        log_info(f"[Scraper] RSS {feed_url} failed: {e}")
        return []

