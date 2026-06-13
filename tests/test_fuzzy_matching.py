import pytest
from src.agents.validator import AshaValidator

@pytest.mark.asyncio
async def test_doctor_name_fuzzy_match_exact_fallback():
    """Verify that a minor spelling transcription typo ('Ragesh') resolves to the canonical doctor name."""
    is_resolved, canonical_name, err, matches = await AshaValidator.validate_doctor("Ragesh")
    
    # Assert it resolved to Rajesh Sharma due to Levenshtein similarity
    assert is_resolved is True
    assert canonical_name == "Dr. Rajesh Sharma"
    assert err is None
    assert len(matches) == 0

@pytest.mark.asyncio
async def test_doctor_name_fuzzy_match_not_found():
    """Verify that completely unrecognizable names return a valid failure response."""
    is_resolved, canonical_name, err, matches = await AshaValidator.validate_doctor("Zzxxpp")
    
    assert is_resolved is False
    assert canonical_name is None
    assert "was not found" in err
