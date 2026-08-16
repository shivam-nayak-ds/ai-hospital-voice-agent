"""
panel.py
--------
Hospital Admin Panel API endpoints.
Feeds data to the frontend dashboard, appointments, doctors, wards, patients, billing tabs.
"""

from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from src.db.session import engine
from src.utils.logger import custom_logger as logger

router = APIRouter(prefix="/api/panel", tags=["Admin Panel"])


# ─── Helper: run sync DB query ────────────────────────────────────────────────

async def _run_query(sql: str, params: dict = None) -> list[dict]:
    """Execute a read-only SQL query and return list of dicts."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text(sql), params or {})
            rows = result.mappings().all()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Panel query error: {e}")
        return []


def _serialize_row(row: dict) -> dict:
    """Convert date/datetime objects to ISO strings for JSON serialization."""
    clean = {}
    for k, v in row.items():
        if isinstance(v, (date, datetime)):
            clean[k] = v.isoformat()
        else:
            clean[k] = v
    return clean


# ─── 1. DASHBOARD ─────────────────────────────────────────────────────────────

@router.get("/dashboard", summary="Dashboard stats for admin panel")
async def get_dashboard():
    """
    Returns aggregated stats for the dashboard landing page:
    today's appointments, total doctors, ward occupancy, billing summary,
    recent AI intents breakdown, and activity feed.
    """
    today = date.today().isoformat()

    # Today's appointments count
    appts = await _run_query(
        'SELECT COUNT(*) as cnt FROM "APPOINTMENTS" WHERE "APPOINTMENT_DATE" = :today',
        {"today": today}
    )
    today_appts = appts[0]["cnt"] if appts else 0

    # Total active doctors
    docs = await _run_query(
        'SELECT COUNT(*) as cnt FROM "DOCTORS" WHERE "STATUS" = \'Active\''
    )
    active_docs = docs[0]["cnt"] if docs else 0

    # Ward occupancy
    wards = await _run_query(
        'SELECT SUM("TOTAL_BEDS") as total, SUM("OCCUPIED_BEDS") as occupied FROM "WARD_MANAGEMENT"'
    )
    total_beds = wards[0]["total"] or 0 if wards else 0
    occupied_beds = wards[0]["occupied"] or 0 if wards else 0
    occupancy_pct = round((occupied_beds / total_beds * 100), 0) if total_beds > 0 else 0

    # Today's billing revenue (estimated from appointments × avg fee)
    revenue_rows = await _run_query(
        """SELECT COALESCE(SUM(d."CONSULTATION_FEE"), 0) as total_revenue
           FROM "APPOINTMENTS" a
           JOIN "DOCTORS" d ON a."DOCTOR_NAME" = d."NAME"
           WHERE a."APPOINTMENT_DATE" = :today""",
        {"today": today}
    )
    today_revenue = revenue_rows[0]["total_revenue"] if revenue_rows else 0

    # Top intents from agent events (last 24 hours)
    intents = await _run_query(
        """SELECT "EVENT_TYPE", COUNT(*) as cnt
           FROM "AGENT_EVENTS"
           WHERE "TIMESTAMP" >= NOW() - INTERVAL '24 hours'
           GROUP BY "EVENT_TYPE"
           ORDER BY cnt DESC
           LIMIT 5"""
    )

    # Recent activity (last 10 audit logs)
    activity = await _run_query(
        """SELECT "ACTION_TYPE", "USER_ID", "ACTION_DETAILS", "TIMESTAMP"
           FROM "AUDIT_LOGS"
           ORDER BY "TIMESTAMP" DESC
           LIMIT 10"""
    )
    activity = [_serialize_row(a) for a in activity]

    # Total patients
    patients = await _run_query('SELECT COUNT(*) as cnt FROM "PATIENTS"')
    total_patients = patients[0]["cnt"] if patients else 0

    return {
        "stats": {
            "today_appointments": today_appts,
            "active_doctors": active_docs,
            "total_patients": total_patients,
            "total_beds": total_beds,
            "occupied_beds": occupied_beds,
            "occupancy_pct": occupancy_pct,
            "today_revenue": today_revenue,
        },
        "top_intents": intents,
        "recent_activity": activity,
    }


# ─── 2. APPOINTMENTS ──────────────────────────────────────────────────────────

@router.get("/appointments", summary="List appointments")
async def list_appointments(
    date_filter: str | None = Query(None, alias="date", description="Filter by date (YYYY-MM-DD)"),
    doctor: str | None = Query(None, description="Filter by doctor name"),
    limit: int = Query(50, ge=1, le=200),
):
    """Returns appointment list with patient, doctor, time, date, status."""
    sql = """SELECT a."ID", a."PATIENT_NAME", a."DOCTOR_NAME",
                    a."APPOINTMENT_TIME", a."APPOINTMENT_DATE", a."STATUS"
             FROM "APPOINTMENTS" a WHERE 1=1"""
    params = {}

    if date_filter:
        sql += ' AND a."APPOINTMENT_DATE" = :date_filter'
        params["date_filter"] = date_filter
    else:
        sql += ' AND a."APPOINTMENT_DATE" = CURRENT_DATE'

    if doctor:
        sql += ' AND a."DOCTOR_NAME" ILIKE :doctor'
        params["doctor"] = f"%{doctor}%"

    sql += ' ORDER BY a."APPOINTMENT_TIME" ASC LIMIT :limit'
    params["limit"] = limit

    rows = await _run_query(sql, params)
    return [_serialize_row(r) for r in rows]


# ─── 3. DOCTORS ───────────────────────────────────────────────────────────────

@router.get("/doctors", summary="List all doctors")
async def list_doctors(
    specialization: str | None = Query(None),
    status: str | None = Query(None),
):
    """Returns doctor list with name, specialization, status, fee, experience."""
    sql = """SELECT d."ID", d."NAME", d."SPECIALIZATION", d."STATUS",
                    d."CONSULTATION_FEE", d."EXPERIENCE_YEARS",
                    d."QUALIFICATION", d."LANGUAGES",
                    dep."NAME" as "DEPARTMENT_NAME"
             FROM "DOCTORS" d
             LEFT JOIN "DEPARTMENTS" dep ON d."DEPARTMENT_ID" = dep."ID"
             WHERE 1=1"""
    params = {}

    if specialization:
        sql += ' AND d."SPECIALIZATION" ILIKE :spec'
        params["spec"] = f"%{specialization}%"

    if status:
        sql += ' AND d."STATUS" ILIKE :status'
        params["status"] = f"%{status}%"

    sql += ' ORDER BY d."NAME" ASC'

    return await _run_query(sql, params)


# ─── 4. WARDS ─────────────────────────────────────────────────────────────────

@router.get("/wards", summary="Ward bed occupancy")
async def get_wards():
    """Returns ward status: type, total beds, occupied, available, price."""
    rows = await _run_query(
        'SELECT "ID", "WARD_TYPE", "TOTAL_BEDS", "OCCUPIED_BEDS", "PRICE_PER_DAY" FROM "WARD_MANAGEMENT" ORDER BY "WARD_TYPE"'
    )
    result = []
    for r in rows:
        r["AVAILABLE_BEDS"] = r["TOTAL_BEDS"] - r["OCCUPIED_BEDS"]
        r["OCCUPANCY_PCT"] = round(r["OCCUPIED_BEDS"] / r["TOTAL_BEDS"] * 100, 0) if r["TOTAL_BEDS"] > 0 else 0
        result.append(r)
    return result


# ─── 5. PATIENTS ──────────────────────────────────────────────────────────────

@router.get("/patients", summary="Search patients")
async def list_patients(
    search: str | None = Query(None, description="Search by name or phone"),
    limit: int = Query(50, ge=1, le=200),
):
    """Returns patient list with basic info."""
    sql = 'SELECT "ID", "NAME", "AGE", "GENDER", "PHONE", "EMAIL" FROM "PATIENTS" WHERE 1=1'
    params = {}

    if search:
        sql += ' AND ("NAME" ILIKE :search OR "PHONE" ILIKE :search)'
        params["search"] = f"%{search}%"

    sql += ' ORDER BY "ID" DESC LIMIT :limit'
    params["limit"] = limit

    return await _run_query(sql, params)


# ─── 6. BILLING ───────────────────────────────────────────────────────────────

@router.get("/billing", summary="Billing catalog")
async def get_billing(
    category: str | None = Query(None, description="Filter by category"),
):
    """Returns billing catalog with item names, categories, prices."""
    sql = 'SELECT "ID", "ITEM_NAME", "CATEGORY", "PRICE", "CODE" FROM "BILLING_CATALOG" WHERE 1=1'
    params = {}

    if category:
        sql += ' AND "CATEGORY" ILIKE :category'
        params["category"] = f"%{category}%"

    sql += ' ORDER BY "CATEGORY", "ITEM_NAME"'

    return await _run_query(sql, params)


# ─── 7. INSURANCE ─────────────────────────────────────────────────────────────

@router.get("/insurance", summary="Insurance providers")
async def get_insurance():
    """Returns insurance provider list."""
    return await _run_query(
        'SELECT "ID", "NAME", "CASHLESS_AVAILABLE", "HELPLINE" FROM "INSURANCE_PROVIDERS" ORDER BY "NAME"'
    )


# ─── 8. LAB REPORTS ──────────────────────────────────────────────────────────

@router.get("/lab-reports", summary="Lab reports")
async def get_lab_reports(
    patient_id: int | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
):
    """Returns lab reports with patient info."""
    sql = """SELECT l."ID", l."TEST_NAME", l."RESULT", l."STATUS", l."ORDERED_DATE",
                    p."NAME" as "PATIENT_NAME"
             FROM "LAB_REPORTS" l
             JOIN "PATIENTS" p ON l."PATIENT_ID" = p."ID"
             WHERE 1=1"""
    params = {}

    if patient_id:
        sql += ' AND l."PATIENT_ID" = :patient_id'
        params["patient_id"] = patient_id

    if status_filter:
        sql += ' AND l."STATUS" ILIKE :status'
        params["status"] = f"%{status_filter}%"

    sql += ' ORDER BY l."ORDERED_DATE" DESC LIMIT 50'

    rows = await _run_query(sql, params)
    return [_serialize_row(r) for r in rows]


# ─── 9. TTS Endpoint (for voice mode in browser) ─────────────────────────────

@router.get("/tts", summary="Text-to-Speech audio")
async def get_tts_audio(text_input: str = Query(..., alias="text")):
    """
    Generates speech audio for the given text using Edge-TTS.
    Returns MP3 audio bytes.
    """
    from fastapi.responses import Response as FastAPIResponse

    try:
        from src.voice.tts import AshaTTS
        tts = AshaTTS()
        audio_data = await tts.generate_audio(text_input)
        if audio_data:
            return FastAPIResponse(
                content=audio_data,
                media_type="audio/mpeg",
                headers={"Content-Disposition": "inline; filename=tts.mp3"}
            )
        raise HTTPException(status_code=500, detail="TTS generation failed")
    except Exception as e:
        logger.error(f"TTS endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS error: {e!s}")
