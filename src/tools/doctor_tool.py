from src.core.domain_exceptions import AshaBaseException
from src.db.session import get_db_readonly
from src.services.doctor_service import DoctorService
from src.utils.logger import custom_logger as logger


async def search_doctors_by_specialty(specialization: str) -> str:
    """
    Finds active doctors by medical specialization.
    """
    try:
        async with get_db_readonly() as db:
            service = DoctorService(db)
            doctors = await service.search_doctors_by_specialty(specialization)

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

    except AshaBaseException as e:
        return e.message
    except Exception as e:
        logger.error(f"Doctor Tool error: {e}")
        return "Doctor search unavailable. Please try again."

async def get_doctor_schedule(doctor_name: str) -> str:
    """
    Gets the availability schedule of a doctor.
    """
    try:
        async with get_db_readonly() as db:
            service = DoctorService(db)
            schedules, doctor = await service.get_doctor_schedule(doctor_name)

            if not schedules:
                return f"No schedule available for Dr. {doctor.NAME}."

            # Chronological day ordering mapping
            day_order = {"Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5, "Saturday": 6, "Sunday": 7}
            schedules_sorted = sorted(schedules, key=lambda s: day_order.get(s.DAY_OF_WEEK, 8))

            lines = [f"Schedule for Dr. {doctor.NAME} ({doctor.SPECIALIZATION}):\n"]
            for s in schedules_sorted:
                lines.append(f"  - {s.DAY_OF_WEEK}: {s.START_TIME} to {s.END_TIME}")

            return "\n".join(lines)

    except AshaBaseException as e:
        return e.message
    except Exception as e:
        logger.error(f"Doctor schedule error: {e}")
        return "Schedule lookup unavailable. Please try again."
