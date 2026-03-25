class ArticleMetrics:
    def __init__(self, title: str, url: str, summary: str, image_url: str, tags: list[str]):
        self.title = title
        self.url = url
        self.summary = summary
        self.image_url = image_url
        self.tags = tags

def post_to_twitter(article: ArticleMetrics) -> bool:
    # Mock Twitter API integration
    hashtags = " ".join([f"#{t.replace(' ', '_')}" for t in article.tags])
    tweet_content = f"🚨 مقال جديد!\n\n{article.title}\n\n{article.summary[:100]}...\n\nاقرأ المزيد: {article.url}\n\n{hashtags}"
    
    print(f"[Social Auto-Poster] Mock Posting to Twitter:\n{tweet_content}")
    return True

def post_to_facebook(article: ArticleMetrics) -> bool:
    # Mock Facebook Graph API integration
    print(f"[Social Auto-Poster] Mock Posting to Facebook Page: {article.url}")
    return True

def auto_share_article(article: ArticleMetrics) -> None:
    try:
        post_to_twitter(article)
        post_to_facebook(article)
        print(f'[Social Auto-Poster] Successfully shared "{article.title}" to connected platforms.')
    except Exception as e:
        print(f"[Social Auto-Poster Error] {e}")
