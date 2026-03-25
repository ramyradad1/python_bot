from datetime import datetime
from collections import deque
import threading

# Store the last 1000 log messages
log_buffer = deque(maxlen=1000)
# A counter that always increments, used for SSE syncing
log_counter = 0
_log_lock = threading.Lock()

def log_info(message: str):
    global log_counter
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_log = f"[{timestamp}] {message}"
    
    # Print to terminal as well safely
    import sys
    try:
        print(formatted_log)
    except UnicodeEncodeError:
        print(formatted_log.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding))
    
    # Add to shared buffer safely
    with _log_lock:
        log_buffer.append(formatted_log)
        log_counter += 1

def get_logs():
    with _log_lock:
        return list(log_buffer), log_counter
