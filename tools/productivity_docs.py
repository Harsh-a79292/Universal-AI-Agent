import io
from typing import List, Dict, Any, Optional
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def create_pdf_document(title: str, content: str) -> bytes:
    """Generate a clean, styled PDF document and return bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=14
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#374151'),
        spaceAfter=8
    )

    story = [Paragraph(title, title_style), Spacer(1, 10)]

    # Split paragraphs
    paragraphs = content.split('\n')
    for p in paragraphs:
        clean_p = p.strip()
        if clean_p:
            story.append(Paragraph(clean_p, body_style))
        else:
            story.append(Spacer(1, 6))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def create_docx_document(title: str, content: str) -> bytes:
    """Generate a clean Word (.docx) document and return bytes."""
    doc = Document()
    doc.add_heading(title, level=0)

    for p in content.split('\n'):
        clean_p = p.strip()
        if clean_p.startswith('### '):
            doc.add_heading(clean_p[4:], level=3)
        elif clean_p.startswith('## '):
            doc.add_heading(clean_p[3:], level=2)
        elif clean_p.startswith('# '):
            doc.add_heading(clean_p[2:], level=1)
        elif clean_p.startswith('- ') or clean_p.startswith('* '):
            doc.add_paragraph(clean_p[2:], style='List Bullet')
        elif clean_p:
            doc.add_paragraph(clean_p)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

def create_excel_document(title: str, data_rows: List[Dict[str, Any]]) -> bytes:
    """Generate an Excel (.xlsx) file from structured records."""
    df = pd.DataFrame(data_rows)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=title[:30] if title else "Sheet1", index=False)
    buffer.seek(0)
    return buffer.getvalue()

