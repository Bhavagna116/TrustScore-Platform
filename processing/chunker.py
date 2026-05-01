"""
chunker.py
----------
Splits text content into logical chunks of ≤300 words each.
Uses paragraph-first splitting, falls back to sentence-level splitting
when paragraphs are too long.
"""

import re
from typing import List


MAX_CHUNK_WORDS = 300
MIN_CHUNK_WORDS = 20  # Discard very short chunks (titles, single sentences)


def _count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def _split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using regex.
    Handles common abbreviations to avoid false splits.
    """
    # Protect common abbreviations
    text = re.sub(r"\b(Dr|Mr|Mrs|Ms|Prof|Sr|Jr|vs|etc|i\.e|e\.g|Fig|Vol|No)\.", r"\1<DOT>", text)
    text = re.sub(r"\b([A-Z])\.([A-Z])\.", r"\1<DOT>\2<DOT>", text)  # Initials like U.S.A

    # Split on sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)

    # Restore dots
    sentences = [s.replace("<DOT>", ".") for s in sentences]

    return [s.strip() for s in sentences if s.strip()]


def _split_into_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs on blank lines."""
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def chunk_text(text: str) -> List[str]:
    """
    Main chunking function.
    Algorithm:
    1. Split into paragraphs
    2. If paragraph ≤ MAX_CHUNK_WORDS → keep as single chunk
    3. If paragraph > MAX_CHUNK_WORDS → split into sentence groups
    4. Group sentences until approaching MAX_CHUNK_WORDS limit
    5. Discard chunks shorter than MIN_CHUNK_WORDS
    """
    if not text or not text.strip():
        return []

    chunks = []
    paragraphs = _split_into_paragraphs(text)

    if not paragraphs:
        # No paragraph breaks → treat as single block
        paragraphs = [text.strip()]

    for para in paragraphs:
        word_count = _count_words(para)

        if word_count == 0:
            continue
        elif word_count <= MAX_CHUNK_WORDS:
            # Paragraph fits in one chunk
            if word_count >= MIN_CHUNK_WORDS:
                chunks.append(para)
        else:
            # Paragraph too long → split into sentences and regroup
            sentences = _split_into_sentences(para)
            current_chunk_sentences = []
            current_word_count = 0

            for sentence in sentences:
                sent_word_count = _count_words(sentence)

                if current_word_count + sent_word_count > MAX_CHUNK_WORDS and current_chunk_sentences:
                    # Save current chunk and start new one
                    chunk_text_result = " ".join(current_chunk_sentences)
                    if _count_words(chunk_text_result) >= MIN_CHUNK_WORDS:
                        chunks.append(chunk_text_result)
                    current_chunk_sentences = [sentence]
                    current_word_count = sent_word_count
                else:
                    current_chunk_sentences.append(sentence)
                    current_word_count += sent_word_count

            # Add remaining sentences
            if current_chunk_sentences:
                chunk_text_result = " ".join(current_chunk_sentences)
                if _count_words(chunk_text_result) >= MIN_CHUNK_WORDS:
                    chunks.append(chunk_text_result)

    # Final cleanup: strip each chunk
    chunks = [c.strip() for c in chunks if c.strip()]

    # If no chunks produced (all too short), return entire text as single chunk
    if not chunks and text.strip():
        return [text.strip()[:3000]]  # Cap at 3000 chars as fallback

    return chunks


def chunk_transcript(transcript: str) -> List[str]:
    """
    Special chunker for YouTube transcripts.
    Transcripts often lack proper paragraph breaks,
    so we use time-based chunking via sentence groups.
    """
    if not transcript:
        return []

    # Transcripts may have newlines for each caption line
    # First try to merge into continuous text
    text = re.sub(r"\n+", " ", transcript)
    text = re.sub(r"\s+", " ", text).strip()

    return chunk_text(text)


if __name__ == "__main__":
    sample = """
    Artificial intelligence is transforming the healthcare industry in profound ways.
    Machine learning models can now detect cancers from medical images with accuracy
    rivaling experienced radiologists. Natural language processing tools help extract
    insights from clinical notes. These advances are accelerating drug discovery.

    However, significant challenges remain. Data privacy is a major concern when
    training AI models on patient records. Algorithmic bias can lead to disparate
    outcomes across demographic groups. Regulatory frameworks struggle to keep pace
    with the rapid development of AI medical devices.

    Despite these obstacles, the potential benefits are enormous. AI-powered tools
    could democratize access to high-quality medical diagnosis in underserved regions.
    Predictive models may help identify patients at risk before symptoms appear.
    The coming decade will be pivotal in determining how AI reshapes medicine.
    """

    result = chunk_text(sample)
    for i, chunk in enumerate(result):
        print(f"\n[Chunk {i+1}] ({len(chunk.split())} words)")
        print(chunk)
