import os
import json
import random
import datetime
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from .logger import log_info
from .seo_agent import load_dynamic_settings, save_dynamic_settings

def fetch_analytics_data():
    """Simulates fetching real performance data for the last 150 published articles."""
    log_info("[Nerve Center | Adv. ML Engine] Fetching Google Search Console / Analytics data...")
    # Mock data generation
    data = []
    for _ in range(150):
        words = random.randint(300, 3500)
        kw_density = float(f"{random.uniform(0.5, 6.0):.1f}")
        images = random.randint(0, 10)
        headings = random.randint(1, 25)
        
        # Traffic formula (hidden from the ML model, it must learn it)
        # Non-linear relationships: >2500 words causes traffic to drop (tl;dr)
        base_traffic = 100
        traffic = base_traffic + (words * 0.5) if words < 2500 else base_traffic + (2500 * 0.5) - ((words-2500)*2.0)
        traffic += (kw_density * 50) if kw_density < 4.5 else (kw_density * 50) - ((kw_density-4.5)*150)
        traffic += (images * 30) if images <= 5 else (images * 30) - ((images-5)*40)
        traffic += (headings * 10) if headings <= 10 else (headings * 10) - ((headings-10)*15)
        
        traffic = max(10, int(traffic + random.randint(-50, 50))) # Add noise
        
        data.append({
            "word_count": words,
            "keyword_density": kw_density,
            "image_count": images,
            "heading_count": headings,
            "organic_traffic": traffic
        })
    return pd.DataFrame(data)

def run_regression_analysis():
    """
    Runs a Random Forest regression (non-linear) to find what correlates with high traffic.
    Calculates Feature Importance to determine which SEO factor is most critical right now.
    """
    df = fetch_analytics_data()
    
    if df.empty:
        log_info("[Nerve Center | Adv. ML Engine] Not enough data for Machine Learning analysis.")
        return
        
    log_info("[Nerve Center | Adv. ML Engine] Running Random Forest regression analysis on article features...")
    
    X = df[['word_count', 'keyword_density', 'image_count', 'heading_count']]
    y = df['organic_traffic']
    
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(X, y)
    
    # Feature Importance Rankings
    importances = model.feature_importances_
    feature_names = X.columns
    importance_dict = dict(zip(feature_names, importances))
    sorted_importance = sorted(importance_dict.items(), key=lambda item: item[1], reverse=True)
    
    log_info("[Nerve Center | Adv. ML Engine] Feature Importance Rankings:")
    for name, imp in sorted_importance:
        log_info(f"   -> {name}: {imp*100:.1f}% impact")
        
    # We perturb the settings dynamically based on the most important feature
    # to "climb the gradient" of the Random Forest
    settings = load_dynamic_settings()
    
    # Defaults
    current_target_words = settings.get("target_word_count", 1500)
    current_target_images = settings.get("target_image_count", 2)
    current_target_density = settings.get("target_keyword_density", 2.0)
    
    # Simple Gradient Ascent Simulation on the RF model
    # We test X+delta and X-delta through the predictor to see which yields higher traffic
    
    test_features = pd.DataFrame([{
        "word_count": current_target_words,
        "keyword_density": current_target_density,
        "image_count": current_target_images,
        "heading_count": 8
    }])
    
    base_prediction = model.predict(test_features)[0]
    
    # Test Word Count
    test_w_up = test_features.copy()
    test_w_up["word_count"] += 200
    if model.predict(test_w_up)[0] > base_prediction:
        current_target_words += 100
    else:
        test_w_down = test_features.copy()
        test_w_down["word_count"] -= 200
        if model.predict(test_w_down)[0] > base_prediction:
            current_target_words -= 100
            
    # Test Images
    test_i_up = test_features.copy()
    test_i_up["image_count"] += 1
    if model.predict(test_i_up)[0] > base_prediction:
        current_target_images += 1
    else:
         test_i_down = test_features.copy()
         test_i_down["image_count"] -= 1
         if model.predict(test_i_down)[0] > base_prediction:
             current_target_images -= 1

    # Cap limits to prevent insane values
    current_target_words = max(300, min(3000, current_target_words))
    current_target_images = max(0, min(8, current_target_images))
    current_target_density = max(0.5, min(5.0, current_target_density))

    settings["target_word_count"] = int(current_target_words)
    settings["target_image_count"] = int(current_target_images)
    settings["target_keyword_density"] = float(current_target_density)
    settings["last_ml_update_date"] = datetime.datetime.now().isoformat()
    
    save_dynamic_settings(settings)
    
    log_info(f"[Nerve Center | Adv. ML Engine] Learning complete. Autonomously adjusted settings: Target Words: {current_target_words}, Target Images: {current_target_images}")
    return settings

if __name__ == "__main__":
    run_regression_analysis()
