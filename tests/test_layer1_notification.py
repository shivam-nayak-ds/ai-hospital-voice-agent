import asyncio
import sys
from pathlib import Path

# Ensure project root is in PYTHONPATH
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.services.notification_service import NotificationService
from src.utils.pdf_generator import generate_appointment_ticket


async def test_layer1():
    print("="*60)
    print("TESTING LAYER 1: PDF GENERATION & EMAIL DISPATCH")
    print("="*60)
    
    # 1. Mock Appointment Details
    appointment_id = 999
    patient_name = "Amit Sharma"
    doctor_name = "Anand Kumar"
    date_str = "2026-06-15"
    time_str = "10:30 AM"
    location = "2nd Floor, Cardiology Wing, Cabin B"
    recipient_email = "shiva.test@example.com"
    
    # 2. Generate PDF
    print("\nGenerating appointment ticket PDF...")
    pdf_bytes = generate_appointment_ticket(
        appointment_id=appointment_id,
        patient_name=patient_name,
        doctor_name=doctor_name,
        date_str=date_str,
        time_str=time_str,
        location=location
    )
    
    # Save a local copy of PDF to verify its styling
    pdf_path = Path("scratch/test_appointment_ticket.pdf")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
    print(f"[OK] PDF Slip successfully saved locally at: {pdf_path}")
    
    # 3. Dispatch Email
    print("\nSending email notification with PDF attachment...")
    await NotificationService.send_booking_email(
        to_email=recipient_email,
        patient_name=patient_name,
        doctor_name=doctor_name,
        date_str=date_str,
        time_str=time_str,
        location=location,
        appointment_id=appointment_id
    )
    
    # Wait a bit for the background async SMTP task to print logs
    await asyncio.sleep(1)
    print("\n[SUCCESS] Layer 1 test complete!")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_layer1())
