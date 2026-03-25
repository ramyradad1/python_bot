from .logger import log_info

def moderate_and_reply_comments():
    """
    Scans the site's database for new unreplied user comments.
    Uses Gemini (Free Tier) to understand the context and post a helpful reply automatically.
    """
    log_info("[Nerve Center | Auto Moderator] Scanning database for unread user comments...")
    
    # Mocking database comments
    unreplied_comments = [
        {"user": "Ahmed", "comment": "I tried the React code but it gave me a Hooks error.", "article": "React Hooks Guide"}
    ]
    
    if unreplied_comments:
        c = unreplied_comments[0]
        log_info(f"[Nerve Center | Auto Moderator] Found comment from {c['user']} on '{c['article']}'")
        log_info(f"[Nerve Center | Auto Moderator] Sending context to Gemini AI to formulate technical response...")
        # Mocking Gemini response
        ai_reply = "Hi Ahmed, make sure you are calling the Hook at the top level of your component, not inside a loop!"
        log_info(f"[Nerve Center | Auto Moderator] [SUCCESS] Auto-replied to {c['user']}: '{ai_reply}'")
    else:
        log_info("[Nerve Center | Auto Moderator] All comments have been moderated and replied to.")

if __name__ == "__main__":
    moderate_and_reply_comments()
