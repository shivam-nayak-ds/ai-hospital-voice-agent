from datetime import datetime, date
from src.db.session import get_db
from src.db.models import Appointment, Doctor, Patient
from src.utils.logger import custom_logger as logger

def check_slot_availability(doctor_name: str, date_str: str, time_str: str) -> str:
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        if date_obj < date.today():
            return "Cannot check availability for a past date."

        with get_db() as db:
            # 1. Resolve canonical doctor first to prevent incorrect matching
            doctor = (
                db.query(Doctor)
                .filter(Doctor.NAME.ilike(f"%{doctor_name}%"), Doctor.STATUS == "Active")
                .first()
            )
            if not doctor:
                return f"Doctor '{doctor_name}' not found."

            existing = (
                db.query(Appointment)
                .filter(
                    Appointment.DOCTOR_ID == doctor.ID,
                    Appointment.APPOINTMENT_DATE == date_obj,
                    Appointment.APPOINTMENT_TIME == time_str,
                    Appointment.STATUS == "Confirmed",
                )
                .first()
            )
            if existing:
                return f"Slot {time_str} on {date_str} with Dr. {doctor.NAME} is already booked."
            return f"Slot {time_str} on {date_str} with Dr. {doctor.NAME} is available."

    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD."
    except Exception as e:
        logger.error(f"Slot check error: {e}")
        return "Slot availability check failed. Please try again."

def book_appointment(patient_name: str, patient_phone: str, doctor_name: str, date_str: str, time_str: str) -> str:
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        if date_obj < date.today():
            return "Cannot book appointments in the past."

        phone_clean = patient_phone.strip().replace("-", "").replace(" ", "")
        if len(phone_clean) < 10:
            return "Please provide a valid 10-digit phone number."

        with get_db() as db:
            # 1. Resolve canonical doctor
            doctor = (
                db.query(Doctor)
                .filter(Doctor.NAME.ilike(f"%{doctor_name}%"), Doctor.STATUS == "Active")
                .first()
            )
            if not doctor:
                return f"Doctor '{doctor_name}' not found or is currently inactive."

            # 2. Resolve/Create Patient record
            patient = db.query(Patient).filter(Patient.PHONE == phone_clean).first()
            if not patient:
                patient = Patient(NAME=patient_name, PHONE=phone_clean)
                db.add(patient)
                db.flush() # Populate patient.ID

            # 3. Create Appointment linking relationships
            appt = Appointment(
                PATIENT_NAME=patient.NAME,
                DOCTOR_NAME=doctor.NAME,
                APPOINTMENT_DATE=date_obj,
                APPOINTMENT_TIME=time_str,
                PATIENT_ID=patient.ID,
                DOCTOR_ID=doctor.ID,
                STATUS="Confirmed",
            )
            db.add(appt)
            db.flush() # Populate appt.ID

            logger.info(f"Booked Appointment ID {appt.ID}: {patient.NAME} with Dr. {doctor.NAME}")
            return (
                f"Appointment confirmed! ID: {appt.ID} | Patient: {patient.NAME} | "
                f"Doctor: Dr. {doctor.NAME} | Date: {date_str} | Time: {time_str}. "
                f"Please arrive 15 minutes early."
            )

    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD."
    except Exception as e:
        if "uq_doctor_slot" in str(e).lower() or "unique" in str(e).lower():
            return (
                f"Slot {time_str} on {date_str} with Dr. {doctor_name} is already taken. "
                f"Please choose a different time."
            )
        logger.error(f"Booking error: {e}")
        return "Booking failed. Please try again."

def cancel_appointment(appointment_id: int) -> str:
    try:
        with get_db() as db:
            appt = db.query(Appointment).filter(Appointment.ID == appointment_id).first()
            if not appt:
                return f"No appointment found with ID {appointment_id}."
            if appt.STATUS == "Cancelled":
                return f"Appointment ID {appointment_id} is already cancelled."

            appt.STATUS = "Cancelled"
            return (
                f"Appointment ID {appointment_id} with Dr. {appt.DOCTOR_NAME} on {appt.APPOINTMENT_DATE} "
                f"at {appt.APPOINTMENT_TIME} has been cancelled successfully."
            )

    except Exception as e:
        logger.error(f"Cancel error for ID {appointment_id}: {e}")
        return "Cancellation failed. Please try again."
