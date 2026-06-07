"""
document-service/app/services/pdf_generator.py

Generates signed document PDFs using ReportLab (not HTML-to-PDF).

Why ReportLab instead of WeasyPrint/wkhtmltopdf?
- Pure Python, no OS-level browser or rendering engine dependency
- Deterministic output — same input always produces the same PDF
- Fine-grained control over layout, fonts, and image placement
- Better performance in containerized environments

PDF structure:
  Page 1+: Document header (To, CC, Ref, Date) + body text
  Signature pages: Each signatory's block with image, name, timestamp
  Final page: Full audit trail table
"""

import io
import os
import base64
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, PageBreak
)
from reportlab.platypus.flowables import Flowable
from PIL import Image as PILImage

from ..config import settings


# CAT = UTC+2 — display all times in Africa/Harare timezone per specification
CAT_OFFSET = timedelta(hours=2)


def _utc_to_cat(dt: datetime) -> datetime:
    """Convert UTC datetime to CAT (UTC+2) for display on PDFs."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone(CAT_OFFSET))


def _format_datetime_cat(dt: Optional[datetime]) -> str:
    """Format datetime as '14 June 2025 at 09:32 CAT'."""
    if not dt:
        return "N/A"
    cat_dt = _utc_to_cat(dt)
    return cat_dt.strftime("%-d %B %Y at %H:%M CAT")


def _resize_signature_png(png_bytes: bytes, width_px: int = 200, height_px: int = 80) -> bytes:
    """
    Normalize signature images to a standard size for consistent PDF layout.
    We resize with LANCZOS (best quality downscaler) while maintaining the
    transparent background by converting to RGBA.
    """
    img = PILImage.open(io.BytesIO(png_bytes)).convert("RGBA")
    img.thumbnail((width_px, height_px), PILImage.LANCZOS)
    
    # Create white background and composite (PDF doesn't support PNG transparency well)
    background = PILImage.new("RGB", img.size, (255, 255, 255))
    background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
    
    buf = io.BytesIO()
    background.save(buf, format="PNG")
    return buf.getvalue()


class HorizontalLine(Flowable):
    """Custom ReportLab Flowable for drawing a horizontal rule."""
    def __init__(self, width, thickness=0.5, color=colors.grey):
        Flowable.__init__(self)
        self.width = width
        self.thickness = thickness
        self.color = color

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)


def generate_document_pdf(
    document_data: dict,
    signatories: List[dict],
    signatures: List[dict],
    audit_logs: List[dict],
    output_path: str
) -> str:
    """
    Generate a complete signed document PDF.
    
    Args:
        document_data: Document fields (title, to_field, subject, body, etc.)
        signatories: List of signatory info dicts with user details
        signatures: List of signature records including image bytes
        audit_logs: List of audit log entries for the final page
        output_path: Where to write the PDF file
    
    Returns:
        SHA-256 hex digest of the generated PDF bytes (for integrity verification)
    """
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    styles = getSampleStyleSheet()
    
    # Custom styles for document letter format
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#1e3a5f"),
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    org_style = ParagraphStyle(
        "OrgName",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#1e3a5f"),
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )
    header_label_style = ParagraphStyle(
        "HeaderLabel",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
        fontName="Helvetica-Bold",
    )
    header_value_style = ParagraphStyle(
        "HeaderValue",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.black,
    )
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=16,
        spaceAfter=8,
    )
    section_heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#1e3a5f"),
        spaceAfter=6,
        spaceBefore=12,
    )
    sig_name_style = ParagraphStyle(
        "SigName",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica-Bold",
    )
    sig_detail_style = ParagraphStyle(
        "SigDetail",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#444444"),
    )
    audit_style = ParagraphStyle(
        "AuditText",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
    )
    
    page_width, page_height = A4
    margin = 20 * mm
    content_width = page_width - 2 * margin
    
    story = []
    
    # ── Letterhead ──────────────────────────────────────────────
    story.append(Paragraph(settings.ORG_NAME.upper(), org_style))
    story.append(Paragraph(settings.ORG_TAGLINE, ParagraphStyle(
        "Tagline", parent=styles["Normal"], fontSize=9,
        textColor=colors.grey, alignment=TA_CENTER
    )))
    story.append(HorizontalLine(content_width, thickness=2, color=colors.HexColor("#1e3a5f")))
    story.append(Spacer(1, 8))
    
    # ── Document header block (Ref, Date, To, CC) ───────────────
    created_at_display = _format_datetime_cat(document_data.get("created_at"))
    
    header_rows = []
    if document_data.get("ref_field"):
        header_rows.append([
            Paragraph("REF:", header_label_style),
            Paragraph(document_data["ref_field"], header_value_style)
        ])
    header_rows.append([
        Paragraph("DATE:", header_label_style),
        Paragraph(created_at_display, header_value_style)
    ])
    header_rows.append([
        Paragraph("TO:", header_label_style),
        Paragraph(document_data.get("to_field", ""), header_value_style)
    ])
    if document_data.get("cc_field"):
        header_rows.append([
            Paragraph("CC:", header_label_style),
            Paragraph(document_data["cc_field"], header_value_style)
        ])
    
    header_table = Table(header_rows, colWidths=[20 * mm, content_width - 20 * mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))
    
    # ── Subject line ────────────────────────────────────────────
    story.append(Paragraph(
        f"<b>SUBJECT: {document_data.get('subject', '')}</b>",
        ParagraphStyle("Subject", parent=styles["Normal"], fontSize=11,
                       textColor=colors.black, spaceAfter=12, underline=1)
    ))
    
    # ── Document body ───────────────────────────────────────────
    body_text = document_data.get("body", "").replace("\n", "<br/>")
    story.append(Paragraph(body_text, body_style))
    
    # ── Signature Blocks ────────────────────────────────────────
    if signatures:
        story.append(Spacer(1, 12))
        story.append(HorizontalLine(content_width))
        story.append(Paragraph("SIGNATURES", section_heading_style))
        story.append(Spacer(1, 6))
        
        # Build a lookup from user_id → signature record
        sig_map = {s["user_id"]: s for s in signatures}
        
        for signatory in signatories:
            sig = sig_map.get(signatory["user_id"])
            if not sig:
                continue
            
            sig_elements = []
            
            # Signature image
            if sig.get("signature_image_bytes"):
                try:
                    resized = _resize_signature_png(sig["signature_image_bytes"])
                    img_buf = io.BytesIO(resized)
                    rl_img = RLImage(img_buf, width=50 * mm, height=20 * mm)
                    sig_elements.append(rl_img)
                except Exception:
                    sig_elements.append(Paragraph("[Signature image unavailable]", sig_detail_style))
            
            sig_elements.append(Spacer(1, 4))
            sig_elements.append(Paragraph(signatory.get("full_name", "Unknown"), sig_name_style))
            
            if signatory.get("title"):
                sig_elements.append(Paragraph(signatory["title"], sig_detail_style))
            if signatory.get("department"):
                sig_elements.append(Paragraph(signatory["department"], sig_detail_style))
            
            signed_at_display = _format_datetime_cat(sig.get("signed_at"))
            sig_elements.append(Paragraph(f"Signed: {signed_at_display}", sig_detail_style))
            
            rec = sig.get("recommendation", "none")
            if rec != "none":
                rec_text = "✓ Recommended" if rec == "recommended" else "✗ Not Recommended"
                rec_color = "#2d6a4f" if rec == "recommended" else "#c1121f"
                sig_elements.append(Paragraph(
                    f'<font color="{rec_color}"><b>{rec_text}</b></font>', sig_detail_style
                ))
            
            if sig.get("note"):
                sig_elements.append(Paragraph(f'Note: {sig["note"]}', sig_detail_style))
            
            # Wrap signatory block in a bordered table for visual separation
            sig_table = Table([[sig_elements]], colWidths=[content_width])
            sig_table.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
            ]))
            story.append(sig_table)
            story.append(Spacer(1, 8))
    
    # ── Audit Trail Page ────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("AUDIT TRAIL", section_heading_style))
    story.append(Paragraph(
        f"Document ID: {document_data.get('id', 'N/A')} | "
        f"Content Hash: {document_data.get('content_hash', 'N/A')[:16]}...",
        ParagraphStyle("HashNote", parent=styles["Normal"], fontSize=7, textColor=colors.grey)
    ))
    story.append(Spacer(1, 8))
    
    audit_table_data = [["#", "Timestamp (CAT)", "User", "Action", "IP Address"]]
    for i, entry in enumerate(audit_logs, 1):
        audit_table_data.append([
            str(i),
            _format_datetime_cat(entry.get("timestamp")),
            entry.get("user_name", entry.get("user_id", "System"))[:30],
            entry.get("action", ""),
            entry.get("ip_address", ""),
        ])
    
    audit_table = Table(
        audit_table_data,
        colWidths=[8 * mm, 40 * mm, 45 * mm, 55 * mm, 30 * mm],
        repeatRows=1
    )
    audit_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        # Data rows
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(audit_table)
    
    # ── Generate PDF ────────────────────────────────────────────
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title=document_data.get("title", "Document"),
        author=settings.ORG_NAME,
        subject=document_data.get("subject", ""),
        creator="DocSign Platform",
    )
    
    doc.build(story)
    
    # Compute SHA-256 of the PDF for authenticity verification
    with open(output_path, "rb") as f:
        pdf_bytes = f.read()
    
    return hashlib.sha256(pdf_bytes).hexdigest()
