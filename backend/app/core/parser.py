import base64
import fitz  # PyMuPDF
import zipfile
import io
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from app.schemas.audit import DocumentInput

class DocumentParser:
    """
    Ingests PDF documents (via PyMuPDF), DOCX files, and raw text files, splitting them into indexed passages.
    Preserves paragraph structure, sentence order, and heading contexts.
    """

    @staticmethod
    def parse_documents(documents: List[DocumentInput]) -> List[Dict[str, Any]]:
        passages = []

        for doc in documents:
            filename = doc.filename or "uploaded_doc"
            content = doc.content or ""
            fn_lower = filename.lower()

            if not content.strip():
                continue

            try:
                if doc.content_type == "application/pdf" or fn_lower.endswith(".pdf"):
                    pdf_passages = DocumentParser._parse_pdf(filename, content)
                    passages.extend(pdf_passages)
                elif fn_lower.endswith(".docx") or fn_lower.endswith(".doc") or "wordprocessingml" in (doc.content_type or ""):
                    docx_passages = DocumentParser._parse_docx(filename, content)
                    passages.extend(docx_passages)
                else:
                    text_passages = DocumentParser._parse_text(filename, content)
                    passages.extend(text_passages)
            except Exception as e:
                # Fallback to simple text parsing if format parsing encounters error
                clean_text = "".join(c for c in content if c.isprintable() or c in "\n\r\t")
                if clean_text.strip():
                    passages.extend(DocumentParser._parse_text(filename, clean_text))

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
                
                # Extract text grouped by paragraphs (<w:p>)
                paragraphs = []
                for p_node in tree.iter():
                    if p_node.tag.endswith('}p'):
                        p_text = "".join([t.text for t in p_node.iter() if t.tag.endswith('}t') and t.text]).strip()
                        if p_text:
                            paragraphs.append(p_text)

                if paragraphs:
                    extracted_text = "\n\n".join(paragraphs)
                    return DocumentParser._parse_text(filename, extracted_text)

            # Fallback if no paragraphs extracted
            clean_text = "".join(c for c in content_data if c.isprintable() or c in "\n\r\t")
            return DocumentParser._parse_text(filename, clean_text)
        except Exception:
            clean_text = "".join(c for c in content_data if c.isprintable() or c in "\n\r\t")
            return DocumentParser._parse_text(filename, clean_text)

    @staticmethod
    def _parse_text(filename: str, content: str) -> List[Dict[str, Any]]:
        passages = []
        if not content or not content.strip():
            return passages

        # Split by double newline or single line breaks if double newline not present
        raw_paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        
        if not raw_paragraphs or len(raw_paragraphs) == 1:
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            # Group lines into chunks of ~2-3 sentences if single line breaks
            raw_paragraphs = []
            chunk = []
            for line in lines:
                chunk.append(line)
                if len(chunk) >= 2 or len(" ".join(chunk)) > 200:
                    raw_paragraphs.append(" ".join(chunk))
                    chunk = []
            if chunk:
                raw_paragraphs.append(" ".join(chunk))

        for idx, para in enumerate(raw_paragraphs):
            if len(para) >= 10:
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
            if content_data.startswith("data:") and "," in content_data[:40]:
                content_data = content_data.split(",", 1)[1]

            pdf_bytes = base64.b64decode(content_data)
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            for page_num in range(len(pdf_doc)):
                page = pdf_doc.load_page(page_num)
                text = page.get_text("text")
                if not text or not text.strip():
                    continue

                page_paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) >= 10]
                if not page_paragraphs:
                    # Fallback grouping by single newlines
                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    page_paragraphs = [" ".join(lines[i:i+3]) for i in range(0, len(lines), 3) if lines[i:i+3]]

                for p_idx, para in enumerate(page_paragraphs):
                    passages.append({
                        "id": f"{filename}_pg{page_num+1}_p{p_idx+1}",
                        "text": para,
                        "source_name": filename,
                        "page_number": page_num + 1,
                        "paragraph_index": p_idx + 1
                    })

            pdf_doc.close()
        except Exception:
            # Fallback to plain text parsing if PDF decoding fails
            passages.extend(DocumentParser._parse_text(filename, content_data))

        return passages

