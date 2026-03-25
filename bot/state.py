import threading

# A global event to signal all running background threads/jobs to halt immediately.
GLOBAL_STOP_EVENT = threading.Event()
