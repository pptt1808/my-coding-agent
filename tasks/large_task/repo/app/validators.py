def validate_title(title: str) -> None:
    if not title or not title.strip():
        raise ValueError("title must not be empty")
