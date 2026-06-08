from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.billing_repository import BillingRepository
from src.db.models import BillingCatalog, WardManagement, InsuranceProvider
from src.core.domain_exceptions import ValidationError, InsuranceVerificationError
from src.schemas.billing import BillingQuerySchema, InsuranceQuerySchema

class BillingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.billing_repo = BillingRepository(db)

    async def get_test_or_procedure_price(self, item_name: str) -> List[BillingCatalog]:
        """
        Retrieves pricing information for tests/procedures matching item_name.
        """
        try:
            schema = BillingQuerySchema(item_name=item_name)
        except Exception as e:
            raise ValidationError(field="item_name", message=str(e))

        return await self.billing_repo.search_catalog_items(schema.item_name)

    async def check_ward_rates(self) -> List[WardManagement]:
        """
        Retrieves all ward types and rates.
        """
        return await self.billing_repo.get_all_wards()

    async def check_insurance_cashless(self, provider_name: str) -> InsuranceProvider:
        """
        Retrieves cashless status for a specific insurance provider.
        """
        try:
            schema = InsuranceQuerySchema(provider_name=provider_name)
        except Exception as e:
            raise ValidationError(field="provider_name", message=str(e))

        provider = await self.billing_repo.get_insurance_provider(schema.provider_name)
        if not provider:
            raise InsuranceVerificationError(provider=schema.provider_name)
        return provider
