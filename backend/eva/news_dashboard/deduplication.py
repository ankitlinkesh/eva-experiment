import re
import hashlib
def duplicate_group_id(title: str) -> str:
    normalized = re.sub(r"[^a-z0-9 ]", "", str(title).lower()).strip()
    return "story-" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:10]
