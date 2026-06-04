from src.db.session import get_db
from src.db.models import Doctor, DoctorSchedule
from src.utils.logger import custom_logger as logger

def search_doctors_by_specialty(specialization: str) -> str:
    if not specialization or len(specialization.strip()) < 2:
        return "Please specify a valid specialty (e.g., Cardiology, Pediatrics)."
        
    try:
        with get_db() as db:
            doctors = (
                db.query(Doctor)
                .filter(
                    Doctor.SPECIALIZATION.ilike(f"%{specialization}%"),
                    Doctor.STATUS == "Active",
                )
                .limit(10)
                .all()
            )

            if not doctors:
                return f"No active doctors found for: '{specialization}'."

            lines = [f"Available {specialization.title()} Doctors:\n"]
            for doc in doctors:
                lines.append(
                    f"- Dr. {doc.NAME} | {doc.QUALIFICATION} | "
                    f"{doc.EXPERIENCE_YEARS} yrs | Fee: Rs.{doc.CONSULTATION_FEE}"
                )

            logger.info(f"Doctor Tool: Found {len(doctors)} doctors for '{specialization}'")
            return "\n".join(lines)

    except Exception as e:
        logger.error(f"Doctor Tool error: {e}")
        return "Doctor search unavailable. Please try again."

def get_doctor_schedule(doctor_name: str) -> str:
    if not doctor_name or len(doctor_name.strip()) < 2:
        return "Please specify a valid doctor name."

    try:
        with get_db() as db:
            # Look up all matches to check for ambiguity
            matching_doctors = (
                db.query(Doctor)
                .filter(Doctor.NAME.ilike(f"%{doctor_name}%"), Doctor.STATUS == "Active")
                .limit(5)
                .all()
            )

            if not matching_doctors:
                return f"Doctor '{doctor_name}' not found."

            if len(matching_doctors) > 1:
                names = ", ".join([f"Dr. {d.NAME}" for d in matching_doctors])
                return f"Multiple doctors found matching '{doctor_name}': {names}. Please specify the full name."

            doctor = matching_doctors[0]

            schedules = (
                db.query(DoctorSchedule)
                .filter(
                    DoctorSchedule.DOCTOR_ID == doctor.ID,
                    DoctorSchedule.STATUS == "Available",
                )
                .all()
            )

            if not schedules:
                return f"No schedule available for Dr. {doctor.NAME}."

            # Chronological day ordering mapping
            day_order = {"Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5, "Saturday": 6, "Sunday": 7}
            schedules_sorted = sorted(schedules, key=lambda s: day_order.get(s.DAY_OF_WEEK, 8))

            lines = [f"Schedule for Dr. {doctor.NAME} ({doctor.SPECIALIZATION}):\n"]
            for s in schedules_sorted:
                lines.append(f"  - {s.DAY_OF_WEEK}: {s.START_TIME} to {s.END_TIME}")

            return "\n".join(lines)

    except Exception as e:
        logger.error(f"Doctor schedule error: {e}")
        return "Schedule lookup unavailable. Please try again."
