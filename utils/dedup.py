import hashlib
from typing import Dict, List, Set


def make_hash(source: str, post_url: str, raw_text: str) -> str:
    """SHA-256 of source + post_url + first 200 chars of text."""
    key = f"{source}|{post_url}|{raw_text[:200]}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def filter_new(items: List[Dict], seen: Set[str]) -> List[Dict]:
    """Return items whose hash is not in seen. Adds '_hash' key to each new item."""
    new_items: List[Dict] = []
    for item in items:
        h = make_hash(item["source"], item["post_url"], item["raw_text"])
        if h not in seen:
            item["_hash"] = h
            new_items.append(item)
    return new_items
