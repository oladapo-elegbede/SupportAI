import io
import asyncio
from typing import List, Tuple
import pdfplumber


class ExtractionError(Exception):
    """Base exception for document text extraction failures."""
    pass


class TextExtractorService:
    """Service for extracting raw text from PDF and TXT files."""

    @staticmethod
    def extract_from_txt(file_bytes: bytes) -> List[Tuple[int, str]]:
        """Extracts text from a UTF-8 encoded text file. Returns [(page_num, text)]."""
        try:
            text = file_bytes.decode("utf-8")
            if not text.strip():
                raise ExtractionError("TXT file contains no readable text.")
            return [(1, text)]
        except UnicodeDecodeError:
            raise ExtractionError("TXT file is not valid UTF-8 text.")

    @staticmethod
    def _extract_pdf_sync(file_bytes: bytes) -> List[Tuple[int, str]]:
        """Synchronous pdfplumber execution."""
        pages_text: List[Tuple[int, str]] = []
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                if len(pdf.pages) == 0:
                    raise ExtractionError("PDF file has zero pages.")

                for idx, page in enumerate(pdf.pages, start=1):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        pages_text.append((idx, page_text))

            if not pages_text:
                raise ExtractionError("No extractable text found in PDF (file may contain only scanned images or be encrypted).")

            return pages_text
        except pdfplumber.pdfminer.pdfparser.PDFSyntaxError:
            raise ExtractionError("Corrupted or malformed PDF file.")
        except Exception as e:
            if "ExtractionError" in type(e).__name__:
                raise e
            raise ExtractionError(f"PDF extraction failed: {str(e)}")

    async def extract_text(self, file_bytes: bytes, file_type: str) -> List[Tuple[int, str]]:
        """
        Extracts page-numbered text tuples [(page_num, text), ...] from file bytes.
        Executes CPU-bound PDF parsing in a thread to keep async event loop responsive.
        """
        clean_type = file_type.lower().strip(".")
        
        if clean_type == "txt":
            return self.extract_from_txt(file_bytes)
        elif clean_type == "pdf":
            return await asyncio.to_thread(self._extract_pdf_sync, file_bytes)
        else:
            raise ExtractionError(f"Unsupported file type for extraction: '{file_type}'")
