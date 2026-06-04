from src.db.session import get_db
from src.db.models import BillingCatalog, WardManagement, InsuranceProvider
from src.utils.logger import custom_logger as logger

def get_test_or_procedure_price(item_name: str) -> str:
    if not item_name or len(item_name.strip()) < 2:
        return "Please enter at least 2 characters to search prices."

    try:
        with get_db() as db:
            # Enforced limit to prevent OOM / context size issues
            results = (
                db.query(BillingCatalog)
                .filter(BillingCatalog.ITEM_NAME.ilike(f"%{item_name}%"))
                .limit(10)
                .all()
            )

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

    except Exception as e:
        logger.error(f"Billing Tool price error: {e}")
        return "Billing information unavailable. Please try again."

def check_ward_rates() -> str:
    try:
        with get_db() as db:
            wards = db.query(WardManagement).all()

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

    except Exception as e:
        logger.error(f"Billing Tool ward rates error: {e}")
        return "Ward information unavailable. Please try again."

def check_insurance_cashless(provider_name: str) -> str:
    if not provider_name or len(provider_name.strip()) < 2:
        return "Please enter a valid insurance provider name."

    try:
        with get_db() as db:
            # Look for exact or highly specific matches first
            provider = (
                db.query(InsuranceProvider)
                .filter(InsuranceProvider.NAME.ilike(f"%{provider_name}%"))
                .first()
            )

            if not provider:
                return (
                    f"'{provider_name}' not found in our network. "
                    f"Call TPA desk at extension 205 for reimbursement options."
                )

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

    except Exception as e:
        logger.error(f"Billing Tool insurance error: {e}")
        return "Insurance information unavailable. Please try again."
