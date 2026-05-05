import re

from pydantic import BaseModel


class ReviewResult(BaseModel):
    approved: bool | None = None
    text: str
    reviewer: str


def parse_review_approval(text: str) -> bool | None:
    """Найти явное решение reviewer-а в markdown-ответе."""
    match = re.search(r"^\s*approved\s*:\s*(true|false)\s*$", text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    return match.group(1).lower() == "true"
