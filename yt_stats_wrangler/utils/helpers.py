from datetime import datetime

def current_commit_time(prefix: str) -> str:
    return {f"{prefix}_commit_time": str(datetime.now())}