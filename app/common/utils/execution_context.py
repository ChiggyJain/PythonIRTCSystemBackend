
import os
import multiprocessing

def get_worker_name() -> str:
    return f"{multiprocessing.current_process().name}-{os.getpid()}"