from src.db.session import get_db
from src.db.models import LabReport, Patient
from src.utils.logger import custom_logger as logger

def check_lab_report_status(patient_phone: str) -> str:
    if not patient_phone:
        return "Please provide a phone number."

    try:
        phone_clean = patient_phone.strip().replace("-", "").replace(" ", "")
        # Remove country code prefix if added
        if phone_clean.startswith("+91"):
            phone_clean = phone_clean[3:]
        elif phone_clean.startswith("91") and len(phone_clean) > 10:
            phone_clean = phone_clean[2:]
            
        if len(phone_clean) < 10:
            return "Please provide a valid 10-digit phone number."

        with get_db() as db:
            # Strict equality comparison to prevent privacy/security leak
            patient = (
                db.query(Patient)
                .filter(Patient.PHONE == phone_clean)
                .first()
            )

            if not patient:
                return (
                    f"No patient found with phone number ending in {phone_clean[-4:]}. "
                    f"Please verify the number or visit the lab reception."
                )

            reports = (
                db.query(LabReport)
                .filter(LabReport.PATIENT_ID == patient.ID)
                .order_by(LabReport.ORDERED_DATE.desc())
                .all()
            )

            if not reports:
                return (
                    f"No lab reports found for {patient.NAME}. "
                    f"If you recently gave a sample, results may take 24-48 hours."
                )

            lines = [f"Lab Reports for {patient.NAME}:\n"]
            for report in reports:
                result_info = ""
                if report.STATUS == "Completed" and report.RESULT:
                    result_info = f" | Result: {report.RESULT}"

                report_url = ""
                if report.REPORT_URL:
                    report_url = f" | URL: {report.REPORT_URL}"

                lines.append(
                    f"  - {report.TEST_NAME} | Date: {report.ORDERED_DATE} | "
                    f"Status: {report.STATUS}{result_info}{report_url}"
                )

            logger.info(f"Lab Tool: {len(reports)} reports for {patient.NAME}")
            return "\n".join(lines)

    except Exception as e:
        logger.error(f"Lab Tool error for phone '{patient_phone}': {e}")
        return "Lab report lookup unavailable. Please try again."
