import re
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from .logger import log_info

# Mock historical data for CTR prediction
def get_historical_ctr_data():
    return pd.DataFrame([
        {"length": 45, "has_power_word": 0, "has_number": 0, "has_year": 0, "is_question": 0, "ctr": 2.1},
        {"length": 55, "has_power_word": 1, "has_number": 1, "has_year": 0, "is_question": 1, "ctr": 8.5},
        {"length": 58, "has_power_word": 1, "has_number": 1, "has_year": 1, "is_question": 0, "ctr": 12.3},
        {"length": 30, "has_power_word": 0, "has_number": 0, "has_year": 0, "is_question": 1, "ctr": 3.4},
        {"length": 80, "has_power_word": 1, "has_number": 0, "has_year": 0, "is_question": 0, "ctr": 1.2}, # Too long
    ])

def extract_features(title: str) -> dict:
    power_words = ["ultimate", "complete", "free", "best", "top", "secret", "guide", "review", "vs"]
    title_lower = title.lower()
    
    return {
        "length": len(title),
        "has_power_word": 1 if any(pw in title_lower for pw in power_words) else 0,
        "has_number": 1 if re.search(r'\d+', title) else 0,
        "has_year": 1 if re.search(r'20\d\d', title) else 0,
        "is_question": 1 if "?" in title or title_lower.startswith(("how", "what", "why", "where")) else 0,
    }

def predict_best_title(titles: list) -> str:
    """
    Selects the best title from a list of LLM-generated candidates using a Random Forest CTR Predictor.
    """
    if not titles:
        return ""
        
    df = get_historical_ctr_data()
    X_train = df[["length", "has_power_word", "has_number", "has_year", "is_question"]]
    y_train = df["ctr"]
    
    model = RandomForestRegressor(n_estimators=10, random_state=42)
    model.fit(X_train, y_train)
    
    best_title = titles[0]
    best_ctr = 0.0
    
    log_info(f"[Nerve Center | CTR Predictor] Evaluating {len(titles)} candidate titles...")
    
    for title in titles:
        features = extract_features(title)
        X_test = pd.DataFrame([features])
        predicted_ctr = model.predict(X_test)[0]
        
        log_info(f"   -> [{predicted_ctr:.1f}% CTR Predicted] '{title}'")
        
        if predicted_ctr > best_ctr:
            best_ctr = predicted_ctr
            best_title = title
            
    log_info(f"[Nerve Center | CTR Predictor] Selected Winning Title: '{best_title}'")
    return best_title

if __name__ == "__main__":
    candidates = [
        "Laptops for programming",
        "7 Best Laptops for Developers in 2026",
        "How to Choose the Ultimate Programming Laptop",
        "Laptop Guide 2026: What is the best?"
    ]
    predict_best_title(candidates)
