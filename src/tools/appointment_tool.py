from src.core.domain_exceptions import AshaBaseException
from src.db.session import get_db, get_db_readonly
from src.services.booking_service import BookingService
from src.utils.logger import custom_logger as logger


async def check_slot_availability(doctor_name: str, date_str: str, time_str: str) -> str:
    """
    Checks if a slot is available for booking.
    """
    try:
        async with get_db_readonly() as db:
            service = BookingService(db)
            return await service.check_slot_availability(
                doctor_name=doctor_name,
                date_str=date_str,
                time_str=time_str
            )
    except AshaBaseException as e:
        return e.message
    except Exception as e:
        logger.error(f"Slot check tool error: {e}")
        return "Slot availability check failed. Please try again."

async def book_appointment(patient_name: str, patient_phone: str, doctor_name: str, date_str: str, time_str: str) -> str:
    """
    Books an appointment slot for a patient with a doctor.
    """
    try:
        async with get_db() as db:
            service = BookingService(db)
            return await service.book_appointment(
                patient_name=patient_name,
                patient_phone=patient_phone,
                doctor_name=doctor_name,
                date_str=date_str,
                time_str=time_str
            )
    except AshaBaseException as e:
        return e.message
    except Exception as e:
        logger.error(f"Booking tool error: {e}")
        return "Booking failed. Please try again."

async def cancel_appointment(appointment_id: int) -> str:
    """
    Cancels a booked appointment.
    """
    try:
        async with get_db() as db:
            service = BookingService(db)
            return await service.cancel_appointment(appointment_id=appointment_id)
    except AshaBaseException as e:
        return e.message
    except Exception as e:
        logger.error(f"Cancel tool error for ID {appointment_id}: {e}")
        return "Cancellation failed. Please try again."
