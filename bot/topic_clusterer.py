import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from collections import Counter
from .logger import log_info
from .supabase_client import get_supabase_client

def run_topic_clustering() -> dict:
    """
    Connects to Supabase, fetches all articles, and uses K-Means clustering + TF-IDF to:
    1. Group articles into pillar topic clusters.
    2. Identify 'orphan' topics that need more content.
    3. Identify oversaturated topics to avoid keyword cannibalization.
    """
    log_info("[Nerve Center | Topic Clusterer] Extracting live article database from Supabase...")
    
    existing_articles = []
    try:
        supabase = get_supabase_client()
        response = supabase.table("articles").select("title").execute()
        if response.data:
            existing_articles = response.data
    except Exception as e:
        log_info(f"[Nerve Center | Topic Clusterer] Supabase error: {e}")
        return {}
        
    log_info(f"[Nerve Center | Topic Clusterer] Analyzing {len(existing_articles)} live articles for semantic clustering...")
    
    if len(existing_articles) < 5:
        log_info("[Nerve Center | Topic Clusterer] Not enough articles to perform K-Means clustering (minimum 5 required).")
        return {}
        
    titles = [a.get("title", "") for a in existing_articles]
    
    try:
        vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        tfidf_matrix = vectorizer.fit_transform(titles)
        
        # Dynamically determine optimal cluster count (roughly 1 cluster per 3 articles)
        n_clusters = max(2, min(len(existing_articles) // 3, 10))
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
        kmeans.fit(tfidf_matrix)
        
        clusters = kmeans.labels_
        
        cluster_counts = Counter(clusters)
        
        orphan_cluster = min(cluster_counts.items(), key=lambda x: x[1])
        saturated_cluster = max(cluster_counts.items(), key=lambda x: x[1])
        
        log_info(f"[Nerve Center | Topic Clusterer] K-Means algorithm formed {n_clusters} distinct topical nodes.")
        
        orphan_titles = [titles[i] for i, label in enumerate(clusters) if label == orphan_cluster[0]]
        saturated_titles = [titles[i] for i, label in enumerate(clusters) if label == saturated_cluster[0]]
        
        log_info(f"   -> [WARNING] Oversaturated Cluster ({saturated_cluster[1]} articles). Pause writing about: '{saturated_titles[0]}'")
        log_info(f"   -> [OPPORTUNITY] Orphan Cluster ({orphan_cluster[1]} articles). Needs more content supporting: '{orphan_titles[0]}'")
        
        return {
            "orphan_cluster_examples": orphan_titles,
            "saturated_cluster_examples": saturated_titles
        }
        
    except Exception as e:
        log_info(f"[Nerve Center | Topic Clusterer] ML Error: {e}")
        return {}

if __name__ == "__main__":
    run_topic_clustering()
