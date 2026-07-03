"""
file_io.py — read plain text out of .txt / .docx / .pdf so it can be pasted
into the detector/humanizer. Also handles chunking long documents into
page-sized blocks purely so large files fit in the text widgets and can be
processed/saved incrementally — not for evading anything, just usability.
"""
import os

try:
    import docx  # python-docx
except ImportError:
    docx = None

try:
    import pypdf
except ImportError:
    pypdf = None


class UnsupportedFileType(Exception):
    pass


def extract_text(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    if ext == ".docx":
        if not docx:
            raise ImportError("python-docx is required to read .docx files: pip install python-docx")
        d = docx.Document(path)
        return "\n".join(p.text for p in d.paragraphs)
    if ext == ".pdf":
        if not pypdf:
            raise ImportError("pypdf is required to read .pdf files: pip install pypdf")
        reader = pypdf.PdfReader(path)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    raise UnsupportedFileType(f"Unsupported file type: {ext}")


def chunk_text(text: str, words_per_chunk: int = 500) -> list:
    """Split into word-count-based chunks so long documents are easy to
    review page-by-page in the UI (not related to detector evasion)."""
    words = text.split()
    if not words:
        return []
    return [
        " ".join(words[i:i + words_per_chunk])
        for i in range(0, len(words), words_per_chunk)
    ]
