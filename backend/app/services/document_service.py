import os
import logging
from typing import List, Dict, Any, Optional
from pypdf import PdfReader
import docx
from app.config import settings
from app.schemas.document import DocumentUploadResponse, DocumentChunkResult
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


class DocumentService:
    """Document processing service for PDF, DOCX, and TXT files."""

    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_document(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Extract text with page-level tracking and generate chunks."""
        file_path = storage_service.resolve(file_path)
        ext = filename.rsplit(".", 1)[-1].lower()
        pages_content = []

        if ext == "pdf":
            pages_content = self._extract_pdf(file_path)
        elif ext in {"docx", "doc"}:
            pages_content = self._extract_docx(file_path)
        elif ext in {"txt", "md"}:
            pages_content = self._extract_text_file(file_path)
        else:
            raise ValueError(f"Unsupported document type: {ext}")

        # Chunk content while preserving page numbers
        chunks = self._chunk_pages(pages_content)
        total_text = " ".join([p["text"] for p in pages_content])
        summary = self._generate_extractive_summary(total_text)

        return {
            "filename": filename,
            "page_count": len(pages_content),
            "chunks": chunks,
            "summary": summary,
            "total_words": len(total_text.split())
        }

    def _extract_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        pages = []
        try:
            reader = PdfReader(file_path)
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                # If page text is empty (scanned image PDF), attempt OCR fallback if pytesseract installed
                if len(text.strip()) < 10:
                    text = self._ocr_pdf_page_fallback(page) or "[Scanned image content]"
                pages.append({"page_number": idx + 1, "text": text.strip()})
        except Exception as e:
            logger.error(f"Error reading PDF {file_path}: {e}")
            pages.append({"page_number": 1, "text": f"[Error reading document: {str(e)}]"})
        return pages

    def _ocr_pdf_page_fallback(self, page) -> str:
        try:
            import pytesseract
            from PIL import Image
            import io
            for img in page.images:
                pil_img = Image.open(io.BytesIO(img.data))
                ocr_text = pytesseract.image_to_string(pil_img)
                if ocr_text.strip():
                    return ocr_text.strip()
        except Exception:
            pass
        return ""

    def _extract_docx(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            doc = docx.Document(file_path)
            full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            return [{"page_number": 1, "text": full_text}]
        except Exception as e:
            logger.error(f"Error reading DOCX {file_path}: {e}")
            return [{"page_number": 1, "text": f"[Error reading DOCX: {str(e)}]"}]

    def _extract_text_file(self, file_path: str) -> List[Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return [{"page_number": 1, "text": content}]

    def _chunk_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        chunks = []
        chunk_idx = 0

        for p in pages:
            text = p["text"]
            page_num = p["page_number"]
            if not text:
                continue

            words = text.split()
            if not words:
                continue

            # Rolling window chunking
            start = 0
            while start < len(words):
                end = min(start + self.chunk_size, len(words))
                chunk_text = " ".join(words[start:end])
                chunks.append({
                    "chunk_index": chunk_idx,
                    "page_number": page_num,
                    "text": chunk_text
                })
                chunk_idx += 1
                if end == len(words):
                    break
                start += (self.chunk_size - self.chunk_overlap)

        return chunks

    def _generate_extractive_summary(self, text: str, max_sentences: int = 3) -> str:
        """Create a clean 3-sentence executive summary from extracted text."""
        if not text:
            return "No readable text content extracted."
        sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 25]
        if not sentences:
            return text[:200] + "..."
        return ". ".join(sentences[:max_sentences]) + "."


# Global singleton
document_service = DocumentService()
