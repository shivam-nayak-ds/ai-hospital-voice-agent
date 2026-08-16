import asyncio
import smtplib
from email.encoders import encode_base64
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config.settings import settings
from src.utils.logger import custom_logger as logger
from src.utils.pdf_generator import generate_appointment_ticket


class NotificationService:
    """
    Handles outbound notifications (Email and SMS) asynchronously.
    """
    
    @staticmethod
    def _send_smtp_email_sync(
        to_email: str,
        subject: str,
        body: str,
        attachment_bytes: bytes | None = None,
        attachment_filename: str = "ticket.pdf"
    ) -> bool:
        """Synchronous helper designed to run inside an asyncio execution thread."""
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            # Fallback to local trace logging for offline development/sandbox testing
            logger.success(
                f"\n[MOCK EMAIL NOTIFICATION SENT]\n"
                f"From: {settings.SMTP_FROM}\n"
                f"To: {to_email}\n"
                f"Subject: {subject}\n"
                f"Body: {body}\n"
                f"Attachment: Attached {len(attachment_bytes) if attachment_bytes else 0} bytes as {attachment_filename}\n"
            )
            return True

        try:
            # Construct Email
            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_FROM
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            # Attach slip
            if attachment_bytes:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment_bytes)
                encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={attachment_filename}"
                )
                msg.attach(part)

            # Establish Connection
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=5)
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
            server.quit()
            
            logger.info(f"Notification successfully dispatched to {to_email}.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to dispatch SMTP notification to {to_email}: {e}")
            return False

    @classmethod
    async def send_booking_email(
        cls,
        to_email: str,
        patient_name: str,
        doctor_name: str,
        date_str: str,
        time_str: str,
        location: str,
        appointment_id: int
    ):
        """Dispatches appointment booking confirmation receipt asynchronously."""
        # Generate ticket attachment (PDF or text fallback)
        ticket_bytes = generate_appointment_ticket(
            appointment_id=appointment_id,
            patient_name=patient_name,
            doctor_name=doctor_name,
            date_str=date_str,
            time_str=time_str,
            location=location
        )
        
        subject = f"Appointment Confirmed: Dr. {doctor_name} - Lifeline Hospital"
        body = (
            f"Dear {patient_name},\n\n"
            f"Your appointment with Dr. {doctor_name} has been successfully booked.\n\n"
            f"Appointment Details:\n"
            f"- ID: {appointment_id}\n"
            f"- Date: {date_str}\n"
            f"- Time: {time_str}\n"
            f"- Location: {location}\n\n"
            f"Please review the attached slip for instructions. If you need to cancel, please call our helpdesk.\n\n"
            f"Warm regards,\n"
            f"Lifeline Multi-Speciality Hospital Team"
        )
        
        # Run email dispatch in threadpool to prevent blocking voice websocket
        asyncio.create_task(
            asyncio.to_thread(
                cls._send_smtp_email_sync,
                to_email,
                subject,
                body,
                ticket_bytes,
                f"appointment_ticket_{appointment_id}.pdf"
            )
        )

    @classmethod
    async def send_cancellation_email(
        cls,
        to_email: str,
        patient_name: str,
        doctor_name: str,
        date_str: str,
        time_str: str,
        appointment_id: int
    ):
        """Dispatches appointment cancellation receipt asynchronously."""
        subject = f"Appointment Cancelled: ID {appointment_id} - Lifeline Hospital"
        body = (
            f"Dear {patient_name},\n\n"
            f"Your appointment with Dr. {doctor_name} scheduled for {date_str} at {time_str} "
            f"(ID: {appointment_id}) has been cancelled successfully.\n\n"
            f"If this was done in error, please visit our website to reschedule.\n\n"
            f"Warm regards,\n"
            f"Lifeline Multi-Speciality Hospital Team"
        )
        
        # Run in background
        asyncio.create_task(
            asyncio.to_thread(
                cls._send_smtp_email_sync,
                to_email,
                subject,
                body
            )
        )
