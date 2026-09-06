from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
import os
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib import colors
from ..database import get_db
from ..models import User, ScannedProduct, Violation
from ..auth import get_current_active_user

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/{scan_id}/pdf")
async def generate_pdf_report(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate PDF compliance report for a scan
    """
    # Get scan
    scan = db.query(ScannedProduct).filter(
        ScannedProduct.id == scan_id,
        ScannedProduct.user_id == current_user.id
    ).first()
    
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found"
        )
    
    # Get violations
    violations = db.query(Violation).filter(
        Violation.product_id == scan_id
    ).all()
    
    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=30,
        alignment=1  # Center
    )
    story.append(Paragraph("Legal Metrology Compliance Report", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Report ID and Date
    story.append(Paragraph(f"<b>Scan ID:</b> #{scan.id}", styles['Normal']))
    story.append(Paragraph(f"<b>Date:</b> {scan.created_at.strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    story.append(Paragraph(f"<b>Product:</b> {scan.product_name or 'N/A'}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Verdict
    verdict = scan.overall_verdict or "UNKNOWN"
    if verdict == "COMPLIANT":
        color = colors.HexColor('#2e7d32')
        bg = colors.HexColor('#e8f5e9')
    elif verdict == "PARTIALLY COMPLIANT":
        color = colors.HexColor('#ef6c00')
        bg = colors.HexColor('#fff3e0')
    else:
        color = colors.HexColor('#c62828')
        bg = colors.HexColor('#ffebee')
    
    story.append(Paragraph(f"<b>Verdict:</b> <font color='{color}'>{verdict}</font>", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Extracted Fields
    story.append(Paragraph("<b>Extracted Fields</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    
    fields_data = [
        ["Field", "Value"],
        ["MRP", scan.mrp or "Not found"],
        ["Net Quantity", scan.net_quantity or "Not found"],
        ["MFG Date", scan.mfg_date or "Not found"],
        ["Expiry Date", scan.exp_date or "Not found"],
        ["Consumer Care", scan.consumer_care or "Not found"],
        ["Manufacturer", scan.manufacturer or "Not found"],
        ["Country of Origin", scan.country_of_origin or "Not found"],
    ]
    
    table = Table(fields_data, colWidths=[2*inch, 3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8faff')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.3*inch))
    
    # Violations
    if violations:
        story.append(Paragraph("<b>Violations</b>", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        
        for v in violations:
            severity = v.severity.upper()
            if severity == "CRITICAL":
                color = colors.HexColor('#c62828')
            elif severity == "WARNING":
                color = colors.HexColor('#ef6c00')
            else:
                color = colors.HexColor('#1a237e')
            
            story.append(Paragraph(f"<font color='{color}'>[{severity}]</font> <b>{v.rule_id}</b>: {v.description}", styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
    else:
        story.append(Paragraph("✅ <b>No violations found. Product is COMPLIANT.</b>", styles['Normal']))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1a237e')))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        "Generated by LMPC Compliance Checker System",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, textColor=colors.grey, alignment=1)
    ))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=compliance_report_{scan_id}.pdf"
        }
    )