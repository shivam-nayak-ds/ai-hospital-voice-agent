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

    async def get_by_name_fuzzy(self, name_query: str, threshold: int = 3, limit: int = 5) -> List[Doctor]:
        """
        Retrieves active doctors matching within a Levenshtein distance threshold.
        Enables speech transcription error-tolerance for phonetic misspelling.
        """
        query_clean = name_query.lower().replace("dr.", "").replace("dr", "").strip()
        if not query_clean:
            return []

        # Fetch all active doctors for in-memory comparison (safe since registry size is small)
        stmt = select(Doctor).filter(Doctor.STATUS == "Active")
        result = await self.db.execute(stmt)
        all_doctors = result.scalars().all()

        matches = []
        for doc in all_doctors:
            doc_name_clean = doc.NAME.lower().replace("dr.", "").replace("dr", "").strip()

            # 1. Exact substring shortcut
            if query_clean in doc_name_clean or doc_name_clean in query_clean:
                matches.append((0, doc))
                continue

            # 2. Levenshtein edit distance check
            full_dist = levenshtein_distance(query_clean, doc_name_clean)
            min_dist = full_dist

            # Word-level comparison to catch first/last name matches
            query_words = query_clean.split()
            doc_words = doc_name_clean.split()
            for qw in query_words:
                for dw in doc_words:
                    dist = levenshtein_distance(qw, dw)
                    min_dist = min(min_dist, dist)

            if min_dist <= threshold:
                matches.append((min_dist, doc))

        # Sort matches by closest distance
        matches.sort(key=lambda x: x[0])
        return [doc for _, doc in matches[:limit]]

    async def get_schedules(self, doctor_id: int) -> List[DoctorSchedule]:
        """Queries the active availability schedules for a specific doctor ID."""
        stmt = select(DoctorSchedule).filter(
            DoctorSchedule.DOCTOR_ID == doctor_id,
            DoctorSchedule.STATUS == "Available"
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculates edit distance between two strings using standard DP row optimization."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

