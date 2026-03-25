import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .logger import log_info
from .supabase_client import get_supabase_client

def check_duplicate_content(new_title: str, new_content: str) -> dict:
    """
    Computes TF-IDF Cosine Similarity between a new article and all existing articles in Supabase.
    If similarity > 80%: BLOCK
    If similarity 60-80%: WARN
    If < 60%: APPROVE
    """
    log_info(f"[Nerve Center | Deduplicator] Connecting to Supabase to fetch historical articles...")
    
    existing_articles = []
    try:
        supabase = get_supabase_client()
        # Only fetch title and content to save memory
        response = supabase.table("articles").select("title, content").execute()
        if response.data:
            existing_articles = response.data
    except Exception as e:
        log_info(f"[Nerve Center | Deduplicator] Supabase connection error: {e}. Defaulting to APPROVE based on title.")
        return {"status": "APPROVE", "max_similarity": 0.0, "match_title": None}
        
    log_info(f"[Nerve Center | Deduplicator] Checking semantic similarity for '{new_title}' against {len(existing_articles)} live articles.")
    
    if not existing_articles:
        return {"status": "APPROVE", "max_similarity": 0.0, "match_title": None}
        
    corpus = [a.get("content", a.get("title", "")) for a in existing_articles]
    titles = [a.get("title", "Unknown") for a in existing_articles]
    
    corpus.append(new_content)
    
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(corpus)
        
        # Compare the last item (new_content) against all others
        cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
        
        if len(cosine_sim) == 0:
            return {"status": "APPROVE", "max_similarity": 0.0, "match_title": None}
            
        max_sim_idx = cosine_sim.argmax()
        max_sim = cosine_sim[max_sim_idx] * 100
        match_title = titles[max_sim_idx]
        
        if max_sim > 80.0:
            log_info(f"[Nerve Center | Deduplicator] [BLOCK] Similarity {max_sim:.1f}% with '{match_title}'. Duplicate content detected.")
            return {"status": "BLOCK", "max_similarity": max_sim, "match_title": match_title}
        elif max_sim > 60.0:
            log_info(f"[Nerve Center | Deduplicator] [WARN] Similarity {max_sim:.1f}% with '{match_title}'. High risk of cannibalization.")
            return {"status": "WARN", "max_similarity": max_sim, "match_title": match_title}
        else:
            log_info(f"[Nerve Center | Deduplicator] [APPROVE] Highest similarity is {max_sim:.1f}% with '{match_title}'. Content is unique.")
            return {"status": "APPROVE", "max_similarity": max_sim, "match_title": match_title}
            
    except Exception as e:
        log_info(f"[Nerve Center | Deduplicator] ML Error during deduplication: {e}. Defaulting to exact title match check.")
        for t in titles:
            if new_title.lower().strip() == t.lower().strip():
                return {"status": "BLOCK", "max_similarity": 100.0, "match_title": t}
        return {"status": "APPROVE", "max_similarity": 0.0, "match_title": None}

if __name__ == "__main__":
    res = check_duplicate_content("Test Next.js", "Testing the dedup with nextjs")
    print(res)
