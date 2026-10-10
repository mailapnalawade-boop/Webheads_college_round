import base64
<<<<<<< HEAD
import pymupdf as fitz
=======
import fitz  # PyMuPDF
import zipfile
import io
import xml.etree.ElementTree as ET
>>>>>>> af5005437a29a1c7c6f88044d83790b29af04e38
from typing import List, Dict, Any
from app.schemas.audit import DocumentInput

class DocumentParser:
    """
    Ingests PDF documents (via PyMuPDF), DOCX files, and raw text files, splitting them into indexed passages.
    """

    @staticmethod
    def parse_documents(documents: List[DocumentInput]) -> List[Dict[str, Any]]:
        passages = []

        for doc in documents:
            filename = doc.filename
            content = doc.content
            fn_lower = filename.lower()

            # Check if PDF, DOCX, or raw text
            if doc.content_type == "application/pdf" or fn_lower.endswith(".pdf"):
                pdf_passages = DocumentParser._parse_pdf(filename, content)
                passages.extend(pdf_passages)
            elif fn_lower.endswith(".docx") or fn_lower.endswith(".doc") or "wordprocessingml" in (doc.content_type or ""):
                docx_passages = DocumentParser._parse_docx(filename, content)
                passages.extend(docx_passages)
            else:
                text_passages = DocumentParser._parse_text(filename, content)
                passages.extend(text_passages)

        return passages

    @staticmethod
    def _parse_docx(filename: str, content_data: str) -> List[Dict[str, Any]]:
        try:
            if "," in content_data and (content_data.startswith("data:") or "base64" in content_data[:35]):
                content_data = content_data.split(",", 1)[1]

            try:
                raw_bytes = base64.b64decode(content_data)
            except Exception:
                raw_bytes = content_data.encode('utf-8', errors='ignore')

            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
                xml_content = z.read('word/document.xml')
                tree = ET.fromstring(xml_content)
                texts = [node.text for node in tree.iter() if node.tag.endswith('}t') and node.text]
                extracted_text = " ".join(texts)

            return DocumentParser._parse_text(filename, extracted_text)
        except Exception:
            clean_text = "".join(c for c in content_data if c.isprintable() or c in "\n\r\t")
            return DocumentParser._parse_text(filename, clean_text)

    @staticmethod
    def _parse_text(filename: str, content: str) -> List[Dict[str, Any]]:
        passages = []
        # Split by double newline or logical paragraph blocks
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        
        if not paragraphs:
            # Fallback to single line split if double newlines absent
            paragraphs = [p.strip() for p in content.split("\n") if len(p.strip()) > 15]

        for idx, para in enumerate(paragraphs):
            passages.append({
                "id": f"{filename}_p{idx+1}",
                "text": para,
                "source_name": filename,
                "page_number": 1,
                "paragraph_index": idx + 1
            })
        return passages

    @staticmethod
    def _parse_pdf(filename: str, content_data: str) -> List[Dict[str, Any]]:
        passages = []
        try:
            # Handle base64 encoded PDF bytes or raw string fallback
            if content_data.startswith("data:application/pdf;base64,"):
                content_data = content_data.split(",", 1)[1]

            pdf_bytes = base64.b64decode(content_data)
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            for page_num in range(len(pdf_doc)):
                page = pdf_doc.load_page(page_num)
                text = page.get_text("text")
                paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 15]

                for p_idx, para in enumerate(paragraphs):
                    passages.append({
                        "id": f"{filename}_pg{page_num+1}_p{p_idx+1}",
                        "text": para,
                        "source_name": filename,
                        "page_number": page_num + 1,
                        "paragraph_index": p_idx + 1
                    })

            pdf_doc.close()
        except Exception as e:
            # Fallback to plain text parsing if PDF decoding fails
            passages.extend(DocumentParser._parse_text(filename, content_data))

        return passages
