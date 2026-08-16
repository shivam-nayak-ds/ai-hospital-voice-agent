
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import LabReport


class LabRepository:
    """
    Encapsulates database access operations for Patient Lab Test Reports.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_patient_reports(self, patient_id: int) -> list[LabReport]:
        """Queries all lab test reports ordered for a specific patient ID."""
        stmt = (
            select(LabReport)
            .filter(LabReport.PATIENT_ID == patient_id)
            .order_by(LabReport.ORDERED_DATE.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
