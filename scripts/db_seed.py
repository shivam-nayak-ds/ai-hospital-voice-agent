import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import time
from pathlib import Path


from src.db.models import (
    AdminUser,
    BillingCatalog,
    Department,
    Doctor,
    DoctorSchedule,
    DocumentRecord,
    InsuranceProvider,
    LabReportMetadata,
    PharmacyInventory,
    WardManagement,
)
from src.db.session import SessionLocal
from src.utils.logger import custom_logger as logger


def _get_or_create(session, model, lookup: dict, defaults: dict | None = None):
    instance = session.query(model).filter_by(**lookup).first()
    if instance:
        return instance

    instance = model(**lookup, **(defaults or {}))
    session.add(instance)
    session.flush()
    return instance


def seed_departments(session):
    departments = [
        {"NAME": "Cardiology", "FLOOR": 1, "HEAD_OF_DEPT": "Dr. Rajesh Sharma", "CONTACT_EXT": "101"},
        {"NAME": "Radiology", "FLOOR": 0, "HEAD_OF_DEPT": "Dr. Sunita Verma", "CONTACT_EXT": "002"},
        {"NAME": "Pathology", "FLOOR": 0, "HEAD_OF_DEPT": "Dr. Amit Khurana", "CONTACT_EXT": "005"},
        {"NAME": "Pediatrics", "FLOOR": 1, "HEAD_OF_DEPT": "Dr. Megha Singh", "CONTACT_EXT": "105"},
        {"NAME": "General Medicine", "FLOOR": 1, "HEAD_OF_DEPT": "Dr. Anil Kumar", "CONTACT_EXT": "110"},
    ]

    return {
        item["NAME"]: _get_or_create(
            session,
            Department,
            {"NAME": item["NAME"]},
            {k: v for k, v in item.items() if k != "NAME"},
        )
        for item in departments
    }


def seed_doctors(session, departments):
    doctors = [
        {
            "NAME": "Dr. Rajesh Sharma",
            "SPECIALIZATION": "Cardiologist",
            "DEPARTMENT_ID": departments["Cardiology"].ID,
            "ROOM_NUMBER": "C-101",
            "CONSULTATION_FEE": 900,
        },
        {
            "NAME": "Dr. Sunita Verma",
            "SPECIALIZATION": "Radiologist",
            "DEPARTMENT_ID": departments["Radiology"].ID,
            "ROOM_NUMBER": "R-002",
            "CONSULTATION_FEE": 700,
        },
        {
            "NAME": "Dr. Amit Khurana",
            "SPECIALIZATION": "Pathologist",
            "DEPARTMENT_ID": departments["Pathology"].ID,
            "ROOM_NUMBER": "P-005",
            "CONSULTATION_FEE": 600,
        },
        {
            "NAME": "Dr. Megha Singh",
            "SPECIALIZATION": "Pediatrician",
            "DEPARTMENT_ID": departments["Pediatrics"].ID,
            "ROOM_NUMBER": "P-105",
            "CONSULTATION_FEE": 800,
        },
        {
            "NAME": "Dr. Anil Kumar",
            "SPECIALIZATION": "General Physician",
            "DEPARTMENT_ID": departments["General Medicine"].ID,
            "ROOM_NUMBER": "G-110",
            "CONSULTATION_FEE": 500,
        },
    ]

    created = {}
    for item in doctors:
        doctor = _get_or_create(
            session,
            Doctor,
            {"NAME": item["NAME"]},
            {
                "SPECIALIZATION": item["SPECIALIZATION"],
                "DEPARTMENT_ID": item["DEPARTMENT_ID"],
                "ROOM_NUMBER": item["ROOM_NUMBER"],
                "CONSULTATION_FEE": item["CONSULTATION_FEE"],
                "STATUS": "available",
            },
        )
        created[item["NAME"]] = doctor
    return created


def seed_schedules(session, doctors):
    for doctor in doctors.values():
        for day in range(0, 6):
            _get_or_create(
                session,
                DoctorSchedule,
                {
                    "DOCTOR_ID": doctor.ID,
                    "DAY_OF_WEEK": day,
                    "START_TIME": time(9, 0),
                    "END_TIME": time(17, 0),
                },
                {"SLOT_DURATION_MINUTES": 30, "IS_ACTIVE": True},
            )


def seed_billing(session):
    services = [
        ("MRI Scan (Brain)", "Radiology", 4500, True),
        ("X-Ray (Chest)", "Radiology", 800, True),
        ("Complete Blood Count (CBC)", "Pathology", 400, True),
        ("Lipid Profile", "Pathology", 750, True),
        ("ICU Bed Charges (Per Day)", "IPD", 6000, True),
        ("Private Suite (Per Day)", "IPD", 12000, False),
    ]

    for name, department, cost, covered in services:
        _get_or_create(
            session,
            BillingCatalog,
            {"SERVICE_NAME": name},
            {"DEPARTMENT": department, "COST": cost, "IS_COVERED_BY_INSURANCE": covered},
        )


def seed_pharmacy(session):
    medicines = [
        ("Paracetamol 500mg", "General", 25, 500),
        ("Azithromycin 250mg", "Antibiotic", 120, 150),
        ("Cough Syrup", "General", 85, 45),
        ("Insulin Glargine", "Diabetic", 450, 20),
        ("Vitamin C Supplements", "Vitamins", 150, 200),
    ]

    for name, category, price, stock in medicines:
        _get_or_create(
            session,
            PharmacyInventory,
            {"MEDICINE_NAME": name},
            {"CATEGORY": category, "PRICE": price, "STOCK_QUANTITY": stock},
        )


def seed_insurance(session):
    providers = [
        ("HDFC Ergo", True, "Rahul Mehta", "1800-2666"),
        ("Star Health", True, "Priya Das", "1800-425-2255"),
        ("Niva Bupa", True, "Sanjay Jha", "1860-500-8888"),
        ("LIC Health", False, "Ramesh Kumar", "022-6827"),
    ]

    for name, cashless, contact, helpline in providers:
        _get_or_create(
            session,
            InsuranceProvider,
            {"NAME": name},
            {"CASHLESS_AVAILABLE": cashless, "CONTACT_PERSON": contact, "HELPLINE": helpline},
        )


def seed_wards(session):
    wards = [
        ("ICU", 15, 12, 6500),
        ("General Ward", 50, 38, 1200),
        ("Semi-Private", 20, 15, 3500),
        ("Private Suite", 10, 4, 8500),
    ]

    for ward_type, total, occupied, price in wards:
        _get_or_create(
            session,
            WardManagement,
            {"WARD_TYPE": ward_type},
            {"TOTAL_BEDS": total, "OCCUPIED_BEDS": occupied, "PRICE_PER_DAY": price},
        )


def seed_documents(session):
    for path in Path("data").glob("*"):
        if path.suffix.lower() not in {".pdf", ".md", ".txt"}:
            continue

        _get_or_create(
            session,
            DocumentRecord,
            {"SOURCE_NAME": path.name},
            {
                "SOURCE_PATH": str(path),
                "CATEGORY": "GENERAL",
                "VERSION": "1",
            },
        )


def seed_admin(session):
    _get_or_create(
        session,
        AdminUser,
        {"EMAIL": "admin@citycare.local"},
        {
            "FULL_NAME": "City Care Admin",
            "ROLE": "super_admin",
            "PASSWORD_HASH": "change-this-before-production",
            "IS_ACTIVE": True,
        },
    )


def seed_lab_reports(session):
    reports = [
        {"PATIENT_NAME": "Amit Kumar", "TEST_NAME": "Complete Blood Count (CBC)", "STATUS": "completed", "REPORT_DATE": "2026-05-28"},
        {"PATIENT_NAME": "Amit Kumar", "TEST_NAME": "Lipid Profile", "STATUS": "pending", "REPORT_DATE": None},
        {"PATIENT_NAME": "Meera Nair", "TEST_NAME": "X-Ray (Chest)", "STATUS": "completed", "REPORT_DATE": "2026-05-30"},
    ]

    from datetime import datetime
    for item in reports:
        report_date = datetime.strptime(item["REPORT_DATE"], "%Y-%m-%d").date() if item["REPORT_DATE"] else None
        _get_or_create(
            session,
            LabReportMetadata,
            {"PATIENT_NAME": item["PATIENT_NAME"], "TEST_NAME": item["TEST_NAME"]},
            {"STATUS": item["STATUS"], "REPORT_DATE": report_date}
        )


def seed_database():
    with SessionLocal() as session:
        departments = seed_departments(session)
        doctors = seed_doctors(session, departments)
        seed_schedules(session, doctors)
        seed_billing(session)
        seed_pharmacy(session)
        seed_insurance(session)
        seed_wards(session)
        seed_documents(session)
        seed_admin(session)
        seed_lab_reports(session)
        session.commit()

    logger.success("Database seed completed.")


if __name__ == "__main__":
    seed_database()

