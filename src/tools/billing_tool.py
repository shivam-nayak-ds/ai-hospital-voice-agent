from src.db.session import get_db
from src.services.billing_service import BillingService
from src.core.domain_exceptions import AshaBaseException
from src.utils.logger import custom_logger as logger

async def get_test_or_procedure_price(item_name: str) -> str:
    """
    Retrieves the price for a test or procedure from the billing catalog.
    """
    try:
        async with get_db() as db:
            service = BillingService(db)
            results = await service.get_test_or_procedure_price(item_name)

            if not results:
                return (
                    f"No pricing found for '{item_name}'. "
                    f"Please contact billing desk at extension 101."
                )

            lines = [f"Billing Info for '{item_name}' (showing top {len(results)} matches):\n"]
            for item in results:
                lines.append(
                    f"  - {item.ITEM_NAME} ({item.CATEGORY}): Rs. {item.PRICE} "
                    f"[Code: {item.CODE}]"
                )

            logger.info(f"Billing Tool: Found {len(results)} results for '{item_name}'")
            return "\n".join(lines)

    except AshaBaseException as e:
        return e.message
    except Exception as e:
        logger.error(f"Billing Tool price error: {e}")
        return "Billing information unavailable. Please try again."

async def check_ward_rates() -> str:
    """
    Checks the availability and pricing of hospital wards.
    """
    try:
        async with get_db() as db:
            service = BillingService(db)
            wards = await service.check_ward_rates()

            if not wards:
                return "Ward information is currently unavailable."

            lines = ["Ward Availability and Rates at City Care Hospital:\n"]
            for ward in wards:
                available_beds = ward.TOTAL_BEDS - ward.OCCUPIED_BEDS
                status = "Available" if available_beds > 0 else "Full"
                lines.append(
                    f"  - {ward.WARD_TYPE}: Rs. {ward.PRICE_PER_DAY}/day | "
                    f"Beds Available: {available_beds}/{ward.TOTAL_BEDS} [{status}]"
                )

            logger.info("Billing Tool: Ward rates fetched successfully")
            return "\n".join(lines)

    except AshaBaseException as e:
        return e.message
    except Exception as e:
        logger.error(f"Billing Tool ward rates error: {e}")
        return "Ward information unavailable. Please try again."

async def check_insurance_cashless(provider_name: str) -> str:
    """
    Checks if an insurance provider offers cashless network support.
    """
    try:
        async with get_db() as db:
            service = BillingService(db)
            provider = await service.check_insurance_cashless(provider_name)

            if provider.CASHLESS_AVAILABLE:
                helpline = provider.HELPLINE or "Contact billing desk"
                return (
                    f"{provider.NAME} is part of our cashless network. "
                    f"Helpline: {helpline}. "
                    f"Please carry your insurance card and photo ID at admission."
                )
            else:
                return (
                    f"{provider.NAME} does not have cashless tie-up with City Care Hospital. "
                    f"You can get reimbursement after settling the bill. "
                    f"We will provide all necessary documents for your claim."
                )

    except AshaBaseException as e:
        return e.message
    except Exception as e:
        logger.error(f"Billing Tool insurance error: {e}")
        return "Insurance information unavailable. Please try again."
