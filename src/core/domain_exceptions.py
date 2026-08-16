from fastapi import status


class AshaBaseException(Exception):
    """Base application domain exception."""
    def __init__(self, message: str, error_code: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code

class DoctorNotFoundError(AshaBaseException):
    def __init__(self, doctor_name: str):
        super().__init__(
            message=f"Doctor '{doctor_name}' not found or is currently inactive.",
            error_code="DOCTOR_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )

class PatientNotFoundError(AshaBaseException):
    def __init__(self, identifier: str):
        super().__init__(
            message=f"Patient record matching '{identifier}' was not found.",
            error_code="PATIENT_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )

class AppointmentConflictError(AshaBaseException):
    def __init__(self, details: str):
        super().__init__(
            message=f"Appointment conflict: {details}",
            error_code="APPOINTMENT_CONFLICT",
            status_code=status.HTTP_409_CONFLICT
        )

class SlotUnavailableError(AshaBaseException):
    def __init__(self, doctor: str, date_str: str, time_str: str):
        super().__init__(
            message=f"Requested slot ({time_str} on {date_str}) with Dr. {doctor} is already booked.",
            error_code="SLOT_UNAVAILABLE",
            status_code=status.HTTP_409_CONFLICT
        )

class InvalidAppointmentDateError(AshaBaseException):
    def __init__(self, details: str):
        super().__init__(
            message=f"Invalid date selection: {details}",
            error_code="INVALID_DATE",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

class EmergencyEscalationError(AshaBaseException):
    def __init__(self, details: str):
        super().__init__(
            message=f"Critical emergency triage triggered: {details}",
            error_code="EMERGENCY_ESCALATION",
            status_code=status.HTTP_400_BAD_REQUEST
        )

class InsuranceVerificationError(AshaBaseException):
    def __init__(self, provider: str):
        super().__init__(
            message=f"Cashless insurance verification failed for: '{provider}'.",
            error_code="INSURANCE_VERIFICATION_FAILED",
            status_code=status.HTTP_400_BAD_REQUEST
        )

class KnowledgeBaseUnavailableError(AshaBaseException):
    def __init__(self, details: str = "Knowledge database is offline."):
        super().__init__(
            message=f"General hospital info lookup failed: {details}",
            error_code="KB_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

class RAGRetrievalError(AshaBaseException):
    def __init__(self, details: str):
        super().__init__(
            message=f"Knowledge retrieval error occurred: {details}",
            error_code="RAG_RETRIEVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# For backwards compatibility with exceptions.py references
class ValidationError(AshaBaseException):
    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"Validation error on field '{field}': {message}",
            error_code="VALIDATION_FAILED",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

class DatabaseOperationError(AshaBaseException):
    def __init__(self, operation: str):
        super().__init__(
            message=f"Database execution failed during: {operation}",
            error_code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
