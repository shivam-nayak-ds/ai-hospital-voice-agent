import io

from src.utils.logger import custom_logger as logger

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab not installed. Falling back to plain-text slips.")

def generate_appointment_ticket(
    appointment_id: int,
    patient_name: str,
    doctor_name: str,
    date_str: str,
    time_str: str,
    location: str
) -> bytes:
    """
    Generates a stylized PDF confirmation slip or a text fallback slip.
    Returns the file contents in raw bytes.
    """
    if REPORTLAB_AVAILABLE:
        try:
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            
            # Outer Ticket Box
            p.setStrokeColor(colors.HexColor("#0D6EFD"))  # Lifeline Blue
            p.setLineWidth(2)
            p.rect(0.5 * inch, height - 4.5 * inch, width - 1.0 * inch, 4.0 * inch)
            
            # Hospital Header Title
            p.setFillColor(colors.HexColor("#0D6EFD"))
            p.setFont("Helvetica-Bold", 18)
            p.drawString(1.0 * inch, height - 1.4 * inch, "LIFELINE MULTI-SPECIALITY HOSPITAL")
            
            p.setFillColor(colors.HexColor("#6C757D"))
            p.setFont("Helvetica", 9)
            p.drawString(1.0 * inch, height - 1.6 * inch, "Vijay Nagar, Sector 26, Indore, Madhya Pradesh | 24x7 Helpline: +91 731 4000 100")
            
            # Horizontal Divider Line
            p.setStrokeColor(colors.HexColor("#DEE2E6"))
            p.setLineWidth(1)
            p.line(1.0 * inch, height - 1.8 * inch, width - 1.0 * inch, height - 1.8 * inch)
            
            # Details Title
            p.setFillColor(colors.HexColor("#212529"))
            p.setFont("Helvetica-Bold", 12)
            p.drawString(1.0 * inch, height - 2.2 * inch, f"APPOINTMENT CONFIRMATION SLIP (ID: {appointment_id})")
            
            # Details Rows
            p.setFont("Helvetica", 11)
            p.drawString(1.0 * inch, height - 2.6 * inch, f"Patient Name:    {patient_name}")
            p.drawString(1.0 * inch, height - 2.9 * inch, f"Doctor Name:     Dr. {doctor_name}")
            p.drawString(1.0 * inch, height - 3.2 * inch, f"Date & Time:     {date_str} at {time_str}")
            p.drawString(1.0 * inch, height - 3.5 * inch, f"Location:        {location}")
            
            # Disclaimer Note
            p.setFillColor(colors.HexColor("#DC3545"))
            p.setFont("Helvetica-Oblique", 9)
            p.drawString(1.0 * inch, height - 4.1 * inch, "* Note: Please arrive 15 minutes before your scheduled appointment time for registration check-in.")
            
            p.showPage()
            p.save()
            
            buffer.seek(0)
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Failed to compile PDF via ReportLab: {e}. Falling back to plain text.")
            
    # Plain Text Fallback
    ticket_text = f"""
==================================================
        LIFELINE MULTI-SPECIALITY HOSPITAL
  Vijay Nagar, Sector 26, Indore, Madhya Pradesh
==================================================
        APPOINTMENT CONFIRMATION SLIP
        
Appointment ID: {appointment_id}
Patient Name:   {patient_name}
Doctor Name:    Dr. {doctor_name}
Date & Time:    {date_str} at {time_str}
Location:       {location}

--------------------------------------------------
* Note: Please arrive 15 minutes before your
  scheduled appointment time for check-in.
==================================================
"""
    return ticket_text.encode("utf-8")
