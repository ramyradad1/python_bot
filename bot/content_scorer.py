import re
from .logger import log_info

def score_article_quality(title: str, content: str) -> dict:
    """
    NLP Quality Gate: Scores an article from 0 to 100 based on structural and readability metrics.
    Rejects content scoring below 70 to prevent SEO penalties for thin/low-quality content.
    """
    log_info(f"[Nerve Center | Content Scorer] Analyzing structural quality of: '{title}'")
    
    score = 100
    penalties = []
    
    word_count = len(content.split())
    
    # 1. Thin Content Check
    if word_count < 500:
        penalty = 30
        score -= penalty
        penalties.append(f"Thin content ({word_count} words): -{penalty}")
    elif word_count < 800:
        penalty = 15
        score -= penalty
        penalties.append(f"Short content ({word_count} words): -{penalty}")
        
    # 2. Structure Check (H2, H3 tags)
    h2_count = len(re.findall(r'<h2.*?>|## ', content, re.IGNORECASE))
    if h2_count == 0:
        penalty = 20
        score -= penalty
        penalties.append(f"No H2 headings: -{penalty}")
    elif h2_count > 15:
        # Over-optimized
        penalty = 10
        score -= penalty
        penalties.append(f"Too many H2 headings ({h2_count}): -{penalty}")
        
    # 3. Paragraph Length (Wall of text check)
    paragraphs = re.split(r'\n\s*\n|<p>', content)
    long_paragraphs = [p for p in paragraphs if len(p.split()) > 150] # > 150 words in a single paragraph is bad for web
    if len(long_paragraphs) > 2:
        penalty = 15
        score -= penalty
        penalties.append(f"Walls of text detected ({len(long_paragraphs)} huge paragraphs): -{penalty}")
        
    # 4. Keyword Stuffing Basic Check (if a single normal word appears > 8% of the time, flag it)
    # This is a very basic NLP heuristic without NLTK overhead
    words = [w.lower() for w in re.findall(r'\b\w{4,}\b', content)]
    if words:
        from collections import Counter
        most_common = Counter(words).most_common(5)
        for term, count in most_common:
            # Skip common stop words roughly by checking if they are in a hardcoded list or just ignore it 
            # and only penalize if it's crazy high (like > 10% density for a 5+ letter word)
            density = (count / word_count) * 100
            if density > 8.0 and len(term) > 4:
                penalty = 25
                score -= penalty
                penalties.append(f"Keyword stuffing detected ('{term}' density {density:.1f}%): -{penalty}")
                
    # 5. Multimedia checks
    has_images = bool(re.search(r'<img|!\[', content, re.IGNORECASE))
    if not has_images:
        penalty = 10
        score -= penalty
        penalties.append(f"No images found: -{penalty}")
        
    score = max(0, score)
    
    passed = score >= 70
    res_status = "PASSED" if passed else "FAILED (Rejected by Quality Gate)"
    
    log_info(f"[Nerve Center | Content Scorer] Article Quality Score: {score}/100 [{res_status}]")
    if penalties:
        for p in penalties:
            log_info(f"   -> Penalty: {p}")
            
    return {"score": score, "passed": passed, "penalties": penalties}

if __name__ == "__main__":
    mock_bad_content = "This is a short article. " * 20
    score_article_quality("Bad Article", mock_bad_content)
    
    mock_good = "## Introduction\n\nThis is a great article about tech.\n\n## Details\n\nIt has multiple paragraphs. " * 50
    score_article_quality("Good Article", mock_good)
