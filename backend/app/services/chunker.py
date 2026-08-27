import re
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class DocumentChunkData:
    chunk_index: int
    page_number: int
    text: str
    char_length: int


class TextChunkerService:
    """Service for cleaning raw text and recursively splitting into overlapping chunks."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", " ", ""]

    @staticmethod
    def clean_text(text: str) -> str:
        """Cleans raw text by removing NULL bytes and normalizing excessive whitespace."""
        if not text:
            return ""
        # Remove NULL bytes
        cleaned = text.replace("\x00", "")
        # Replace non-breaking spaces
        cleaned = cleaned.replace("\xa0", " ")
        # Replace 3 or more consecutive newlines with double newline
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        # Standardize horizontal tabs/spaces
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        return cleaned.strip()

    def _split_text_recursive(self, text: str, separators: List[str]) -> List[str]:
        """Recursively splits text on separators until chunks are <= chunk_size."""
        final_chunks: List[str] = []
        if not text.strip():
            return final_chunks

        if len(text) <= self.chunk_size:
            return [text.strip()]

        # Pick current separator
        separator = separators[-1]
        new_separators = []
        for i, s in enumerate(separators):
            if s == "":
                separator = ""
                break
            if s in text:
                separator = s
                new_separators = separators[i + 1:]
                break

        # Split text by separator
        if separator != "":
            splits = text.split(separator)
        else:
            # Character by character split
            splits = list(text)

        # Recombine splits up to chunk_size with overlap
        current_doc: List[str] = []
        current_len = 0

        for s in splits:
            s_len = len(s) + (len(separator) if current_doc else 0)
            if current_len + s_len > self.chunk_size:
                if current_doc:
                    doc_text = separator.join(current_doc).strip()
                    if doc_text:
                        final_chunks.append(doc_text)

                    # Calculate overlap start
                    while current_doc and current_len > self.chunk_overlap:
                        removed = current_doc.pop(0)
                        current_len -= len(removed) + len(separator)

                current_doc.append(s)
                current_len = sum(len(x) for x in current_doc) + (len(separator) * (len(current_doc) - 1))
            else:
                current_doc.append(s)
                current_len += s_len

        if current_doc:
            doc_text = separator.join(current_doc).strip()
            if doc_text:
                final_chunks.append(doc_text)

        return final_chunks

    def chunk_document_pages(
        self, pages_text: List[Tuple[int, str]]
    ) -> List[DocumentChunkData]:
        """
        Takes page-numbered text tuples [(page_num, raw_text), ...] and returns clean overlapping DocumentChunkData list.
        """
        all_chunks: List[DocumentChunkData] = []
        global_chunk_index = 0

        for page_num, raw_text in pages_text:
            cleaned = self.clean_text(raw_text)
            if not cleaned:
                continue

            page_chunks = self._split_text_recursive(cleaned, self.separators)
            for chunk_text in page_chunks:
                if chunk_text.strip():
                    all_chunks.append(
                        DocumentChunkData(
                            chunk_index=global_chunk_index,
                            page_number=page_num,
                            text=chunk_text,
                            char_length=len(chunk_text),
                        )
                    )
                    global_chunk_index += 1

        return all_chunks
