import io
from typing import Dict, Any, Optional
from pypdf import PdfReader
from models.llm_service import query_llm_with_fallback

def extract_text_from_pdf(file_bytes: bytes, filename: str = "document.pdf") -> Dict[str, Any]:
    """
    Extract readable text from PDF bytes.
    Detects empty or scanned PDFs gracefully.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        total_pages = len(reader.pages)
        if total_pages == 0:
            return {
                "success": False,
                "error": "The uploaded PDF has no pages.",
                "total_pages": 0,
                "text": ""
            }

        extracted_pages = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                extracted_pages.append(f"--- Page {i + 1} ---\n{page_text.strip()}")

        full_text = "\n\n".join(extracted_pages)

        # Check for scanned/empty PDF
        if not full_text.strip():
            return {
                "success": False,
                "error": "This PDF appears to be empty or contains scanned images without selectable text. "
                         "OCR processing is required for scanned image-only documents.",
                "total_pages": total_pages,
                "text": ""
            }

        return {
            "success": True,
            "filename": filename,
            "total_pages": total_pages,
            "char_count": len(full_text),
            "text": full_text,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to read PDF: {str(e)}",
            "total_pages": 0,
            "text": ""
        }

def summarize_pdf_text(pdf_text: str, preferred_model: str = "auto") -> Dict[str, Any]:
    """Generate a structured summary of the extracted PDF text."""
    # Truncate text if extremely long to avoid exceeding LLM context windows safely
    truncated_text = pdf_text[:18000]
    prompt = f"""You are a professional document analyst. Provide a clear, comprehensive executive summary of the following document.
Include:
1. Document Overview / Main Subject
2. Key Highlights & Findings
3. Important Takeaways or Action Items

Document Content:
\"\"\"
{truncated_text}
\"\"\"
"""
    system_instruction = "You are an expert document summarizer. Use bullet points and clean markdown."
    return query_llm_with_fallback(prompt, system_instruction, preferred_model=preferred_model)

def answer_pdf_question(pdf_text: str, question: str, preferred_model: str = "auto") -> Dict[str, Any]:
    """Answer user questions based strictly on the extracted PDF content."""
    truncated_text = pdf_text[:18000]
    prompt = f"""Document Context:
\"\"\"
{truncated_text}
\"\"\"

User Question: {question}

Answer the question strictly based on the document context provided above.
If the information is not explicitly mentioned in the document, clearly state: 'The provided document does not contain information to answer this question.' Do not make up facts.
"""
    system_instruction = "You are a faithful document QA assistant. Answer only using the provided document."
    return query_llm_with_fallback(prompt, system_instruction, preferred_model=preferred_model)

