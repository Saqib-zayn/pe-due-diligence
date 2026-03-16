"""
file_processor.py — Standardises extraction of plain text from varying document types.
"""

import io


class FileProcessor:
    """Extracts plain text from PDF, DOCX, and TXT file byte streams."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

    def process(self, filename: str, file_bytes: bytes) -> str:
        """Detect file type by extension and route to the appropriate extractor.

        Args:
            filename: Original filename including extension.
            file_bytes: Raw file content as bytes.

        Returns:
            Extracted plain text string.

        Raises:
            ValueError: If the file extension is not supported.
        """
        lower = filename.lower()
        if lower.endswith(".pdf"):
            return self.extract_from_pdf(file_bytes)
        elif lower.endswith(".docx"):
            return self.extract_from_docx(file_bytes)
        elif lower.endswith(".txt"):
            return self.extract_from_txt(file_bytes)
        else:
            ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else "(none)"
            raise ValueError(
                f"Unsupported file type '{ext}'. "
                f"Please upload one of: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}."
            )

    def extract_from_pdf(self, file_bytes: bytes) -> str:
        """Extract all text blocks from a PDF byte stream using PyMuPDF."""
        import fitz  # PyMuPDF

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        texts = []
        for page in doc:
            texts.append(page.get_text("text"))
        doc.close()
        return "\n".join(texts)

    def extract_from_docx(self, file_bytes: bytes) -> str:
        """Extract all paragraph text from a DOCX byte stream using python-docx."""
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(para.text for para in doc.paragraphs)

    def extract_from_txt(self, file_bytes: bytes) -> str:
        """Decode a raw byte stream as UTF-8 text."""
        return file_bytes.decode("utf-8")
