"""Document chunking for kgraph.

Splits documents into overlapping chunks suitable for entity extraction.
Tracks provenance back to source files.
"""

from __future__ import annotations

from pathlib import Path

from kgraph.domain.models import Chunk

SUPPORTED_EXTENSIONS = {".txt", ".md"}
DEFAULT_CHUNK_SIZE = 1000  # tokens (approximate by chars / 4)
DEFAULT_OVERLAP = 200


def read_documents(path: Path) -> list[tuple[str, str]]:
    """Read documents from a file or directory.

    Args:
        path: Path to a single file or directory of files.

    Returns:
        List of (filename, content) tuples.

    Raises:
        FileNotFoundError: If path doesn't exist.
        ValueError: If no supported files found.
    """
    if not path.exists():
        msg = f"Path does not exist: {path}"
        raise FileNotFoundError(msg)

    if path.is_file():
        if path.suffix not in SUPPORTED_EXTENSIONS:
            msg = f"Unsupported file type: {path.suffix}. Supported: {SUPPORTED_EXTENSIONS}"
            raise ValueError(msg)
        return [(path.name, path.read_text(encoding="utf-8"))]

    # Directory: collect all supported files
    documents = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.suffix in SUPPORTED_EXTENSIONS:
            content = file_path.read_text(encoding="utf-8")
            relative = str(file_path.relative_to(path))
            documents.append((relative, content))

    if not documents:
        msg = f"No supported files found in {path}. Supported: {SUPPORTED_EXTENSIONS}"
        raise ValueError(msg)

    return documents


def chunk_text(
    text: str,
    source_file: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """Split text into overlapping chunks.

    Uses character-based splitting with approximate token estimation (chars / 4).
    Splits on paragraph boundaries when possible.

    Args:
        text: Full document text.
        source_file: Name of the source file for provenance.
        chunk_size: Target chunk size in approximate tokens.
        overlap: Overlap between consecutive chunks in approximate tokens.

    Returns:
        List of Chunk objects with provenance metadata.
    """
    if not text.strip():
        return []

    # Convert token targets to character targets (rough: 1 token ≈ 4 chars)
    char_chunk_size = chunk_size * 4
    char_overlap = overlap * 4

    paragraphs = text.split("\n\n")
    chunks: list[Chunk] = []
    current_text = ""
    chunk_index = 0

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        if len(current_text) + len(paragraph) > char_chunk_size and current_text:
            chunks.append(
                Chunk(
                    text=current_text.strip(),
                    source_file=source_file,
                    chunk_index=chunk_index,
                    total_chunks=0,  # Will be set after all chunks created
                )
            )
            chunk_index += 1

            # Keep overlap from end of current chunk
            if char_overlap > 0 and len(current_text) > char_overlap:
                current_text = current_text[-char_overlap:] + "\n\n" + paragraph
            else:
                current_text = paragraph
        else:
            current_text = current_text + "\n\n" + paragraph if current_text else paragraph

    # Don't forget the last chunk
    if current_text.strip():
        chunks.append(
            Chunk(
                text=current_text.strip(),
                source_file=source_file,
                chunk_index=chunk_index,
                total_chunks=0,
            )
        )

    # Fix total_chunks count
    total = len(chunks)
    return [
        Chunk(
            text=c.text,
            source_file=c.source_file,
            chunk_index=c.chunk_index,
            total_chunks=total,
        )
        for c in chunks
    ]
