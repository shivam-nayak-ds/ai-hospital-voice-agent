from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Doctor, DoctorSchedule

class DoctorRepository:
    """
    Encapsulates all database query logic for Doctor profiles and availability schedules.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_by_specialty(self, specialty: str, limit: int = 10) -> List[Doctor]:
        """Queries active doctors matching the given medical specialization."""
        stmt = select(Doctor).filter(
            Doctor.SPECIALIZATION.ilike(f"%{specialty}%"),
            Doctor.STATUS == "Active"
        ).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name_substring(self, name_query: str, limit: int = 5) -> List[Doctor]:
        """Queries active doctors matching a partial string query for name resolution."""
        stmt = select(Doctor).filter(
            Doctor.NAME.ilike(f"%{name_query}%"),
            Doctor.STATUS == "Active"
        ).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_schedules(self, doctor_id: int) -> List[DoctorSchedule]:
        """Queries the active availability schedules for a specific doctor ID."""
        stmt = select(DoctorSchedule).filter(
            DoctorSchedule.DOCTOR_ID == doctor_id,
            DoctorSchedule.STATUS == "Available"
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
