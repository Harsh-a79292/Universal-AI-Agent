import re

def truncate_text(text: str, max_chars: int = 50) -> str:
    """Truncate text for short preview titles."""
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip() + "..."

