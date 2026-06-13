import sys
import asyncio
import datetime
from pathlib import Path
from sqlalchemy import select

# Ensure project root is in PYTHONPATH
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.db.session import get_db
from src.db.models import Appointment, Patient
from src.services.notification_service import NotificationService
from src.utils.logger import custom_logger as logger

# In-memory registry to avoid sending duplicate reminders during runtime
_sent_reminder_ids = set()

def parse_appointment_datetime(appt_date: datetime.date, time_str: str) -> datetime.datetime:
    """Combines appointment date object and time string (e.g. '10:00 AM') into a datetime object."""
    # Strip any extra whitespace
    time_clean = time_str.strip().upper()
    try:
        dt = datetime.datetime.strptime(f"{appt_date} {time_clean}", "%Y-%m-%d %I:%M %p")
        return dt
    except ValueError:
        try:
            dt = datetime.datetime.strptime(f"{appt_date} {time_clean}", "%Y-%m-%d %H:%M")
            return dt
        except ValueError as e:
            raise ValueError(f"Unable to parse appointment time '{time_str}': {e}")

async def run_reminder_scan():
    """Scans DB for confirmed appointments scheduled in the next 2 hours and dispatches reminders."""
    now = datetime.datetime.now()
    today = now.date()
    two_hours_later = now + datetime.timedelta(hours=2)
    
    logger.info("Scanning database for upcoming appointments requiring reminders...")
    
    async with get_db() as db:
        # Select confirmed appointments for today
        stmt = (
            select(Appointment)
            .where(Appointment.STATUS == "Confirmed")
            .where(Appointment.APPOINTMENT_DATE == today)
        )
        result = await db.execute(stmt)
        appointments = result.scalars().all()
        
        count_scanned = 0
        count_sent = 0
        
        for appt in appointments:
            if appt.ID in _sent_reminder_ids:
                continue
                
            try:
                appt_dt = parse_appointment_datetime(appt.APPOINTMENT_DATE, appt.APPOINTMENT_TIME)
                
                # Check if appointment occurs within the next 2 hours and hasn't passed
                if now <= appt_dt <= two_hours_later:
                    count_scanned += 1
                    
                    # Fetch patient email details
                    patient_stmt = select(Patient).where(Patient.ID == appt.PATIENT_ID)
                    p_res = await db.execute(patient_stmt)
                    patient = p_res.scalar_one_or_none()
                    
                    if patient and patient.EMAIL:
                        logger.info(f"Upcoming Appointment ID {appt.ID} found for {patient.NAME} at {appt.APPOINTMENT_TIME}.")
                        
                        subject = f"Reminder: Appointment with Dr. {appt.DOCTOR_NAME} in 2 hours"
                        body = (
                            f"Dear {patient.NAME},\n\n"
                            f"This is a reminder that you have an upcoming appointment with Dr. {appt.DOCTOR_NAME} today.\n\n"
                            f"Details:\n"
                            f"- Appointment ID: {appt.ID}\n"
                            f"- Time: {appt.APPOINTMENT_TIME}\n"
                            f"- Location: Main Clinic, Block A\n\n"
                            f"Please arrive 15 minutes prior to check-in. If you need to cancel, please contact us immediately.\n\n"
                            f"Warm regards,\n"
                            f"Lifeline Multi-Speciality Hospital Team"
                        )
                        
                        # Dispatch asynchronous email
                        NotificationService._send_smtp_email_sync(
                            to_email=patient.EMAIL,
                            subject=subject,
                            body=body
                        )
                        
                        # Add to sent registry
                        _sent_reminder_ids.add(appt.ID)
                        count_sent += 1
                        
            except Exception as e:
                logger.error(f"Error checking reminder for Appointment ID {appt.ID}: {e}")
                
        logger.info(f"Scan complete. Scanned: {len(appointments)} | Reminded: {count_sent}")

async def main():
    logger.success("ASHA Background Reminder Scheduler is running.")
    while True:
        try:
            await run_reminder_scan()
        except Exception as e:
            logger.error(f"Error in background scheduler execution loop: {e}")
            
        # Scan every 15 minutes (900 seconds)
        await asyncio.sleep(900)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scheduler process terminated by user.")
