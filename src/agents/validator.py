"""
validator.py
------------
Handles semantic and database validations for extracted session entities:
- Patient Phone: Cleans and ensures exact 10 digits.
- Appointment Date: Validates date format, resolves relative days (e.g. "tomorrow"), 
  and rejects any past dates.
- Doctor Name: Queries database to resolve partial names to canonical Active doctor profiles
  and detects ambiguous matches.
"""

import re
from datetime import datetime, date, timedelta
from typing import Dict, Any, Tuple, List, Optional
from src.db.session import get_db
from src.db.models import Doctor
from src.utils.logger import custom_logger as logger

class AshaValidator:
    """
    Validates and cleans entities extracted during conversation turns.
    """
    
    @staticmethod
    def validate_phone(phone: Optional[str]) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Cleans and validates the phone number.
        Returns:
            (is_valid, cleaned_phone_number, error_message)
        """
        if not phone:
            return False, None, "Phone number is missing."
            
        # Clean the input: keep only digits
        clean_phone = "".join(filter(str.isdigit, str(phone)))
        
        # Remove country code prefix if present (91 or +91)
        if len(clean_phone) > 10 and (clean_phone.startswith("91") or clean_phone.startswith("0")):
            clean_phone = clean_phone[-10:]
            
        if len(clean_phone) != 10:
            return False, None, "Please provide a valid ten-digit mobile number."
            
        return True, clean_phone, None

    @staticmethod
    def validate_date(date_str: Optional[str], reference_date: Optional[date] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates date strings and resolves relative date words to YYYY-MM-DD.
        Returns:
            (is_valid, formatted_date_str, error_message)
        """
        if not date_str:
            return False, None, "Date is missing."
            
        if reference_date is None:
            reference_date = date.today()
            
        date_str_clean = date_str.strip().lower()
        resolved_date = None
        
        # Handle relative phrases
        if date_str_clean in ["today", "aaj"]:
            resolved_date = reference_date
        elif date_str_clean in ["tomorrow", "kal", "next day"]:
            resolved_date = reference_date + timedelta(days=1)
        elif date_str_clean in ["day after tomorrow", "parso"]:
            resolved_date = reference_date + timedelta(days=2)
        else:
            # Try to parse YYYY-MM-DD
            try:
                # Remove common sentence framing around date
                match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", date_str_clean)
                if match:
                    resolved_date = datetime.strptime(match.group(0), "%Y-%m-%d").date()
                else:
                    # Try other formats e.g. "June 10" or "10 June"
                    # For simplicity, if it's already a clean string let's try dateutil or simple patterns
                    # We will support standard parsing for common formats
                    for fmt in ["%d-%m-%Y", "%m-%d-%Y", "%Y/%m/%d", "%d/%m/%Y"]:
                        try:
                            resolved_date = datetime.strptime(date_str_clean, fmt).date()
                            break
                        except ValueError:
                            continue
            except Exception:
                pass
                
        if not resolved_date:
            return False, None, "Please specify the date in YYYY-MM-DD format (for example, 2026-06-15)."
            
        if resolved_date < reference_date:
            return False, None, "We cannot check slots or book appointments in the past."
            
        return True, resolved_date.strftime("%Y-%m-%d"), None

    @staticmethod
    async def validate_doctor(doctor_name: Optional[str]) -> Tuple[bool, Optional[str], Optional[str], List[str]]:
        """
        Resolves partial doctor name to a canonical active doctor in the database.
        Returns:
            (is_resolved, canonical_name_or_none, error_message, list_of_ambiguous_matches)
        """
        if not doctor_name or len(doctor_name.strip()) < 2:
            return False, None, "Please specify a valid doctor name.", []
            
        clean_name = doctor_name.replace("Dr.", "").replace("Dr", "").strip()
        
        try:
            from sqlalchemy import select
            async with get_db() as db:
                stmt = select(Doctor).filter(Doctor.NAME.ilike(f"%{clean_name}%"), Doctor.STATUS == "Active").limit(5)
                result = await db.execute(stmt)
                matching_doctors = list(result.scalars().all())
                
                if not matching_doctors:
                    # Fallback to fuzzy/phonetic matching (Phase 3 Voice Spelling Tolerance)
                    from src.repositories.doctor_repository import DoctorRepository
                    repo = DoctorRepository(db)
                    matching_doctors = await repo.get_by_name_fuzzy(clean_name, threshold=3)

                if not matching_doctors:
                    return False, None, f"Dr. {doctor_name} was not found in our directory or is currently inactive.", []
                    
                if len(matching_doctors) > 1:
                    matches = [f"Dr. {d.NAME}" for d in matching_doctors]
                    names_str = ", ".join(matches)
                    return False, None, f"Multiple doctors found matching your query: {names_str}. Could you specify the full name?", matches
                    
                # Exact resolved doctor
                resolved_doc = matching_doctors[0]
                return True, resolved_doc.NAME, None, []
                
        except Exception as e:
            logger.error(f"Validator Doctor search error: {e}")
            return False, None, "We encountered an issue checking the doctor directory. Please try again.", []

