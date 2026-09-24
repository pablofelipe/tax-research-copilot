def chunk_text(text: str, max_chars: int) -> list[str]:
    """Splits text into chunks no larger than max_chars, preferring to break
    on paragraph boundaries (blank lines) and only hard-splitting a single
    paragraph that alone exceeds max_chars.
    """
    paragraphs = [p for p in (p.strip() for p in text.split("\n\n")) if p]

    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        for piece in _split_oversized(paragraph, max_chars):
            candidate = f"{current}\n\n{piece}" if current else piece
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = piece

    if current:
        chunks.append(current)

    return chunks


def _split_oversized(paragraph: str, max_chars: int) -> list[str]:
    if len(paragraph) <= max_chars:
        return [paragraph]
    return [paragraph[i : i + max_chars] for i in range(0, len(paragraph), max_chars)]
