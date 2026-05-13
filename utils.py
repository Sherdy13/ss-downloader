import re


def safe_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "", name).strip()
