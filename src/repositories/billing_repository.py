from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import BillingCatalog, WardManagement, InsuranceProvider

class BillingRepository:
    """
    Encapsulates database lookup operations for prices, ward occupancies, and insurance coverage.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_catalog_items(self, query: str, limit: int = 10) -> List[BillingCatalog]:
        """Queries billing catalog items matching partial string criteria."""
        stmt = select(BillingCatalog).filter(
            BillingCatalog.ITEM_NAME.ilike(f"%{query}%")
        ).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_all_wards(self) -> List[WardManagement]:
        """Queries all hospital ward types and current bed occupancy rates."""
        stmt = select(WardManagement)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_insurance_provider(self, provider_name: str) -> Optional[InsuranceProvider]:
        """Queries cashless insurance network status for the provider name."""
        stmt = select(InsuranceProvider).filter(
            InsuranceProvider.NAME.ilike(f"%{provider_name}%")
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()
