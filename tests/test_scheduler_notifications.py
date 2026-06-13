import pytest
import datetime
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from src.utils.pdf_generator import generate_appointment_ticket
from src.services.notification_service import NotificationService
from scripts.scheduler import run_reminder_scan, parse_appointment_datetime

def test_pdf_ticket_generator():
    """Assert that the ticket generator runs and outputs bytes (PDF or text fallback)."""
    ticket_bytes = generate_appointment_ticket(
        appointment_id=999,
        patient_name="John Doe",
        doctor_name="Amit Kumar",
        date_str="2026-06-15",
        time_str="10:30 AM",
        location="Block A, Ground Floor"
    )
    assert isinstance(ticket_bytes, bytes)
    assert len(ticket_bytes) > 0

@pytest.mark.asyncio
async def test_async_notification_booking_dispatch():
    """Verify notification service starts a background task and dispatches mock emails."""
    with patch("src.services.notification_service.NotificationService._send_smtp_email_sync") as mock_send:
        mock_send.return_value = True
        
        await NotificationService.send_booking_email(
            to_email="test@domain.com",
            patient_name="Alice",
            doctor_name="Rajesh Sharma",
            date_str="2026-06-15",
            time_str="11:00 AM",
            location="Cardiology, Block A",
            appointment_id=101
        )
        
        # Give asyncio loop a microsecond to schedule the background thread
        await asyncio.sleep(0.01)
        mock_send.assert_called_once()

def test_parse_appointment_datetime():
    """Verify correct parsing of date and time strings to standard python datetimes."""
    appt_date = datetime.date(2026, 6, 12)
    time_str = "10:30 AM"
    dt = parse_appointment_datetime(appt_date, time_str)
    assert dt == datetime.datetime(2026, 6, 12, 10, 30)

@pytest.mark.asyncio
@patch("scripts.scheduler.get_db")
@patch("src.services.notification_service.NotificationService._send_smtp_email_sync")
async def test_run_reminder_scan(mock_send, mock_db_ctx):
    """Verify reminder scanner queries DB and correctly flags upcoming appointments."""
    mock_send.return_value = True
    
    # Mock database session
    mock_db = AsyncMock()
    mock_db_ctx.return_value.__aenter__.return_value = mock_db
    
    # Setup mock appointment (2 hours from now)
    now = datetime.datetime.now()
    appt_time_str = (now + datetime.timedelta(hours=1, minutes=30)).strftime("%I:%M %p")
    
    mock_appt = MagicMock()
    mock_appt.ID = 777
    mock_appt.STATUS = "Confirmed"
    mock_appt.APPOINTMENT_DATE = now.date()
    mock_appt.APPOINTMENT_TIME = appt_time_str
    mock_appt.PATIENT_ID = 5
    mock_appt.DOCTOR_NAME = "Vijay Kumar"
    
    # Mock result scalars
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_appt]
    mock_db.execute.return_value = mock_result
    
    # Mock patient fetch (second query in loop)
    mock_patient = MagicMock()
    mock_patient.NAME = "Bob"
    mock_patient.EMAIL = "bob@domain.com"
    
    mock_patient_res = MagicMock()
    mock_patient_res.scalar_one_or_none.return_value = mock_patient
    
    # Bind execute side effects: first query gets appointments, second gets patient
    mock_db.execute.side_effect = [mock_result, mock_patient_res]
    
    # Run scan
    await run_reminder_scan()
    
    # Assert email sent
    mock_send.assert_called_once()
