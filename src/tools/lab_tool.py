from src.db.session import get_db
from src.services.lab_service import LabService
from src.core.domain_exceptions import AshaBaseException
from src.utils.logger import custom_logger as logger

async def check_lab_report_status(patient_phone: str) -> str:
    """
    Checks the status of lab reports ordered for a patient phone number.
    """
    try:
        async with get_db() as db:
            service = LabService(db)
            reports, patient = await service.get_patient_reports(patient_phone)

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

    except AshaBaseException as e:
        return e.message
    except Exception as e:
        logger.error(f"Lab Tool error for phone '{patient_phone}': {e}")
        return "Lab report lookup unavailable. Please try again."
