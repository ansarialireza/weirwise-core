import os
import re
from typing import List
from pypdf import PdfReader


def extract_text_from_file(file_path: str, mime_type: str) -> str:
    """Extract clean text from PDF, Markdown, or plain text file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if "pdf" in mime_type.lower() or file_path.lower().endswith(".pdf"):
        reader = PdfReader(file_path)
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages_text.append(text)
        return "\n\n".join(pages_text)
    else:
        # Plain text, markdown, etc.
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()


def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    """Splits text into overlapping chunks respecting paragraph or sentence boundaries."""
    if not text:
        return []

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    # Normalize whitespace
    text = re.sub(r"\r\n", "\n", text)
    paragraphs = text.split("\n\n")

    chunks = []
    current_chunk = []
    current_length = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_len = len(para)
        if current_length + para_len + 2 <= chunk_size:
            current_chunk.append(para)
            current_length += para_len + 2
        else:
            if current_chunk:
                chunk_str = "\n\n".join(current_chunk)
                chunks.append(chunk_str)
                # Overlap handling
                overlap_text = chunk_str[-chunk_overlap:] if len(chunk_str) > chunk_overlap else ""
                current_chunk = [overlap_text, para] if overlap_text else [para]
                current_length = sum(len(p) for p in current_chunk) + 2
            else:
                # Single paragraph exceeds chunk_size, split by sentences or characters
                for i in range(0, para_len, chunk_size - chunk_overlap):
                    sub = para[i : i + chunk_size]
                    if sub.strip():
                        chunks.append(sub.strip())
                current_chunk = []
                current_length = 0

    if current_chunk:
        chunk_str = "\n\n".join(current_chunk).strip()
        if chunk_str:
            chunks.append(chunk_str)

    return chunks
