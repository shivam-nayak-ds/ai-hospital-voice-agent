"""
Lifeline Multi-Speciality Hospital — Production Database Seed
Source of Truth: Knowledge Base (doctor_directory.json, departments_faqs.json)
Location: Bhopal, Madhya Pradesh
"""
import datetime
import random
import sys
import asyncio
from sqlalchemy import text
from src.db.session import engine, Base, AsyncSessionLocal
from src.db.models import (
    Department, Doctor, DoctorSchedule, Patient, Appointment,
    BillingCatalog, InsuranceProvider, WardManagement, LabReport,
    ConversationLog, AgentEvent, AuditLog
)
from src.utils.logger import custom_logger as logger
from config.settings import settings

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ═══════════════════════════════════════════════════════════════════════════════
# DEPARTMENTS — 15 departments (KB source: departments_faqs.json, excluding inconsistent entries)
# ═══════════════════════════════════════════════════════════════════════════════

DEPARTMENTS_DATA = [
    {"name": "Cardiology",              "desc": "Comprehensive cardiac care including interventional cardiology, electrophysiology, cardiac imaging, heart failure management, and preventive cardiology.", "location": "Building A, 2nd Floor"},
    {"name": "Neurology",               "desc": "Diagnosis and treatment of brain, spinal cord, and peripheral nerve disorders including stroke, epilepsy, Parkinson's, dementia, and headache disorders.", "location": "Building C, 1st Floor"},
    {"name": "Orthopedics",             "desc": "Musculoskeletal care including joint replacement, arthroscopy, sports medicine, spine surgery, trauma surgery, and fracture management.", "location": "Building B, 1st Floor"},
    {"name": "General Medicine",        "desc": "Primary and internal medicine covering fever, infections, diabetes, hypertension, thyroid disorders, and comprehensive health check-ups.", "location": "Building A, Ground Floor"},
    {"name": "General Surgery",         "desc": "Surgical services including laparoscopic surgery, hernia repair, appendectomy, cholecystectomy, breast surgery, and wound management.", "location": "Building A, 1st Floor"},
    {"name": "Pediatrics",              "desc": "Complete child healthcare from newborn to adolescent including neonatology, immunization, growth monitoring, and pediatric emergencies.", "location": "Building B, Ground Floor"},
    {"name": "Gynecology & Obstetrics", "desc": "Women's health including antenatal care, high-risk pregnancy, normal and cesarean delivery, laparoscopic gynae surgery, and infertility treatment.", "location": "Building B, 2nd Floor"},
    {"name": "Oncology",                "desc": "Cancer diagnosis and treatment including medical oncology, surgical oncology, radiation therapy, chemotherapy, and palliative care.", "location": "Building C, 3rd Floor"},
    {"name": "Dermatology",             "desc": "Skin, hair, and nail disorder management including medical dermatology, cosmetic procedures, laser treatments, and allergy testing.", "location": "Building B, 2nd Floor"},
    {"name": "Gastroenterology",        "desc": "Digestive system care including endoscopy, colonoscopy, ERCP, liver disease management, and treatment of IBD, IBS, and peptic ulcers.", "location": "Building B, 1st Floor"},
    {"name": "Ophthalmology",           "desc": "Eye care including cataract surgery (phaco), glaucoma management, retina clinic, LASIK, squint correction, and pediatric ophthalmology.", "location": "Building A, 3rd Floor"},
    {"name": "ENT",                     "desc": "Ear, nose, and throat care including hearing assessment, sinus surgery, tonsillectomy, adenoidectomy, voice disorders, and vertigo management.", "location": "Building A, 3rd Floor"},
    {"name": "Nephrology",              "desc": "Kidney care including dialysis, kidney transplant evaluation, CKD management, hypertension related to kidney disease, and electrolyte disorders.", "location": "Building A, Ground Floor"},
    {"name": "Pulmonology",             "desc": "Respiratory care including asthma, COPD, tuberculosis, pneumonia, lung function testing, bronchoscopy, and sleep disorders.", "location": "Building B, 1st Floor"},
    {"name": "Emergency Medicine",      "desc": "24x7 emergency and trauma care including triage, resuscitation, acute medical emergencies, polytrauma management, and critical care stabilisation.", "location": "Building A, Ground Floor"},
]

# ═══════════════════════════════════════════════════════════════════════════════
# DOCTORS — 38 doctors (KB source: doctor_directory.json DOC_001-DOC_014)
# Schedule patterns match KB exactly (Mon/Wed/Fri, Tue/Thu/Sat, Mon-Fri)
# ═══════════════════════════════════════════════════════════════════════════════

DOCTORS_DATA = [
    # ── Cardiology (DOC_001) ──
    {"name": "Dr. Rajesh Sharma",    "spec": "Senior Consultant, Interventional Cardiologist", "qual": "MD, DM Cardiology",              "exp": 20, "fee": 1200, "dept": "Cardiology",              "sched": "mwf_9_1"},
    {"name": "Dr. Priya Mehta",      "spec": "Consultant Interventional Cardiologist",          "qual": "MD, DM",                         "exp": 15, "fee": 1000, "dept": "Cardiology",              "sched": "tts_10_2"},
    {"name": "Dr. Anil Verma",       "spec": "Consultant, Electrophysiology",                   "qual": "MD, DM Cardiology",              "exp": 12, "fee": 1000, "dept": "Cardiology",              "sched": "mwf_2_5"},

    # ── Orthopedics (DOC_002) ──
    {"name": "Dr. Vikram Singh",     "spec": "Senior Consultant, Joint Replacement Surgeon",     "qual": "MS Ortho, Fellowship Joint Replacement", "exp": 22, "fee": 1000, "dept": "Orthopedics", "sched": "mwf_9_12"},
    {"name": "Dr. Neha Kapoor",      "spec": "Consultant, Spine Specialist",                    "qual": "MS Ortho, Spine Specialist",      "exp": 16, "fee": 800,  "dept": "Orthopedics",             "sched": "tts_10_1"},
    {"name": "Dr. Arjun Reddy",      "spec": "Consultant, Sports Medicine & Arthroscopy",       "qual": "MS Ortho, Sports Medicine",       "exp": 10, "fee": 800,  "dept": "Orthopedics",             "sched": "mwf_3_6"},

    # ── Gynecology & Obstetrics (DOC_003) ──
    {"name": "Dr. Sunita Gupta",     "spec": "Senior Consultant, High-Risk Pregnancy",          "qual": "MS OBG, High-Risk Pregnancy",     "exp": 25, "fee": 1000, "dept": "Gynecology & Obstetrics", "sched": "mwf_9_1"},
    {"name": "Dr. Meera Joshi",      "spec": "Consultant, Laparoscopic Surgeon",                "qual": "MD OBG, Laparoscopic Surgery",    "exp": 14, "fee": 800,  "dept": "Gynecology & Obstetrics", "sched": "tts_9_12"},
    {"name": "Dr. Kavita Rao",       "spec": "Consultant, Infertility Specialist",               "qual": "MD OBG, Reproductive Medicine",   "exp": 12, "fee": 1000, "dept": "Gynecology & Obstetrics", "sched": "mwf_2_5"},

    # ── Neurology (DOC_004) ──
    {"name": "Dr. Sanjay Patel",     "spec": "Senior Consultant, Neurologist",                  "qual": "MD, DM Neurology",                "exp": 20, "fee": 1200, "dept": "Neurology",               "sched": "mwf_10_1"},
    {"name": "Dr. Pooja Iyer",       "spec": "Consultant, Epilepsy & Movement Disorders",       "qual": "MD, Epilepsy Specialist",         "exp": 13, "fee": 1000, "dept": "Neurology",               "sched": "tth_10_1_sat_9_12"},
    {"name": "Dr. Rohan Desai",      "spec": "Consultant, Stroke Specialist",                   "qual": "MD, DM Neurology",                "exp": 11, "fee": 1000, "dept": "Neurology",               "sched": "mwf_3_6"},

    # ── Pediatrics (DOC_005) ──
    {"name": "Dr. Anita Deshmukh",   "spec": "Senior Consultant, Neonatologist",                "qual": "MD Pediatrics, Neonatology",      "exp": 22, "fee": 800,  "dept": "Pediatrics",              "sched": "mwf_9_12"},
    {"name": "Dr. Sameer Khan",      "spec": "Consultant, Pediatrician",                        "qual": "MD Pediatrics",                   "exp": 14, "fee": 600,  "dept": "Pediatrics",              "sched": "tts_10_1"},
    {"name": "Dr. Ritu Saxena",      "spec": "Consultant, Pediatric Pulmonology",               "qual": "MD Pediatrics, Pulmonology",      "exp": 10, "fee": 800,  "dept": "Pediatrics",              "sched": "mwf_4_7"},

    # ── General Surgery (DOC_006) ──
    {"name": "Dr. Mahesh Kumar",     "spec": "Senior Consultant, Laparoscopic Specialist",      "qual": "MS General Surgery, Laparoscopic","exp": 24, "fee": 1000, "dept": "General Surgery",         "sched": "mwf_9_12"},
    {"name": "Dr. Sandeep Malhotra", "spec": "Consultant, GI Surgery",                          "qual": "MS, GI Surgery",                  "exp": 16, "fee": 800,  "dept": "General Surgery",         "sched": "tts_9_12"},
    {"name": "Dr. Deepak Nair",      "spec": "Consultant, Surgical Oncology",                   "qual": "MS, Onco Surgery",                "exp": 12, "fee": 1000, "dept": "General Surgery",         "sched": "mwf_2_5"},

    # ── Gastroenterology (DOC_007) ──
    {"name": "Dr. Ashwin Kulkarni",  "spec": "Senior Consultant, Gastroenterologist",           "qual": "MD, DM Gastroenterology",         "exp": 18, "fee": 1000, "dept": "Gastroenterology",        "sched": "mwf_10_1"},
    {"name": "Dr. Pallavi Shinde",   "spec": "Consultant, Hepatologist",                        "qual": "MD, DM Hepatology",               "exp": 12, "fee": 1000, "dept": "Gastroenterology",        "sched": "tth_10_1_sat_9_12"},

    # ── Nephrology (DOC_008) ──
    {"name": "Dr. Rakesh Joshi",     "spec": "Senior Consultant, Nephrologist",                 "qual": "MD, DM Nephrology",               "exp": 20, "fee": 1000, "dept": "Nephrology",              "sched": "mwf_9_12"},
    {"name": "Dr. Swati Bhatt",      "spec": "Consultant, Transplant Nephrology",               "qual": "MD, DM Transplant Nephrology",    "exp": 14, "fee": 1200, "dept": "Nephrology",              "sched": "tts_10_1"},

    # ── ENT (DOC_009) ──
    {"name": "Dr. Vinod Agarwal",    "spec": "Senior Consultant, ENT Surgeon",                  "qual": "MS ENT",                          "exp": 20, "fee": 800,  "dept": "ENT",                     "sched": "mwf_9_12"},
    {"name": "Dr. Sneha Patil",      "spec": "Consultant, Head & Neck Surgery",                 "qual": "MS ENT, Head & Neck Surgery",     "exp": 11, "fee": 700,  "dept": "ENT",                     "sched": "tts_10_1"},

    # ── Ophthalmology (DOC_010) ──
    {"name": "Dr. Suresh Menon",     "spec": "Senior Consultant, Retina Specialist",            "qual": "MS Ophth, Retina Specialist",     "exp": 22, "fee": 1000, "dept": "Ophthalmology",           "sched": "mwf_9_12"},
    {"name": "Dr. Rekha Sharma",     "spec": "Consultant, Cornea & Refractive Surgery",         "qual": "MS Ophth, Cornea & Refractive",   "exp": 15, "fee": 800,  "dept": "Ophthalmology",           "sched": "tts_9_12"},
    {"name": "Dr. Amit Choudhary",   "spec": "Consultant, Glaucoma & Pediatric Ophth",          "qual": "MS Ophth, Glaucoma Specialist",   "exp": 10, "fee": 800,  "dept": "Ophthalmology",           "sched": "mwf_2_5"},

    # ── Dermatology (DOC_011) ──
    {"name": "Dr. Nisha Kapoor",     "spec": "Senior Consultant, Dermatologist",                "qual": "MD Dermatology",                  "exp": 18, "fee": 800,  "dept": "Dermatology",             "sched": "mwf_10_1"},
    {"name": "Dr. Rahul Tiwari",     "spec": "Consultant, Cosmetic Dermatology",                "qual": "MD, Cosmetic Dermatology",        "exp": 12, "fee": 700,  "dept": "Dermatology",             "sched": "tts_10_1"},

    # ── General Medicine (DOC_013) ──
    {"name": "Dr. Kamal Nath",       "spec": "Senior Consultant, General Physician",            "qual": "MD Medicine",                     "exp": 25, "fee": 500,  "dept": "General Medicine",        "sched": "ms_9_12"},
    {"name": "Dr. Preeti Singh",     "spec": "Consultant, Diabetologist",                       "qual": "MD Medicine, Diabetology",        "exp": 14, "fee": 600,  "dept": "General Medicine",        "sched": "mwf_2_5"},
    {"name": "Dr. Tarun Malhotra",   "spec": "Consultant, Pulmonology",                         "qual": "MD Medicine, Pulmonology",        "exp": 10, "fee": 600,  "dept": "General Medicine",        "sched": "tts_2_5"},

    # ── Oncology (DOC_014) ──
    {"name": "Dr. Prakash Iyer",     "spec": "Senior Consultant, Medical Oncologist",           "qual": "MD, DM Medical Oncology",         "exp": 22, "fee": 1200, "dept": "Oncology",                "sched": "mwf_10_1"},
    {"name": "Dr. Anjali Bhat",      "spec": "Consultant, Surgical Oncology",                   "qual": "MS Surgical Oncology",            "exp": 15, "fee": 1000, "dept": "Oncology",                "sched": "tth_10_1_sat_9_12"},
    {"name": "Dr. Ravi Kumar",       "spec": "Consultant, Radiation Oncology",                  "qual": "MD Radiation Oncology",           "exp": 12, "fee": 1000, "dept": "Oncology",                "sched": "mwf_9_5"},
]

# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULE PATTERNS — mapped from KB time slots
# ═══════════════════════════════════════════════════════════════════════════════

SCHEDULE_MAP = {
    "mwf_9_1":           [("Monday", "09:00 AM", "01:00 PM"), ("Wednesday", "09:00 AM", "01:00 PM"), ("Friday", "09:00 AM", "01:00 PM")],
    "tts_10_2":          [("Tuesday", "10:00 AM", "02:00 PM"), ("Thursday", "10:00 AM", "02:00 PM"), ("Saturday", "10:00 AM", "02:00 PM")],
    "mwf_2_5":           [("Monday", "02:00 PM", "05:00 PM"), ("Wednesday", "02:00 PM", "05:00 PM"), ("Friday", "02:00 PM", "05:00 PM")],
    "mwf_9_12":          [("Monday", "09:00 AM", "12:00 PM"), ("Wednesday", "09:00 AM", "12:00 PM"), ("Friday", "09:00 AM", "12:00 PM")],
    "tts_10_1":          [("Tuesday", "10:00 AM", "01:00 PM"), ("Thursday", "10:00 AM", "01:00 PM"), ("Saturday", "10:00 AM", "01:00 PM")],
    "tts_9_12":          [("Tuesday", "09:00 AM", "12:00 PM"), ("Thursday", "09:00 AM", "12:00 PM"), ("Saturday", "09:00 AM", "12:00 PM")],
    "mwf_3_6":           [("Monday", "03:00 PM", "06:00 PM"), ("Wednesday", "03:00 PM", "06:00 PM"), ("Friday", "03:00 PM", "06:00 PM")],
    "mwf_10_1":          [("Monday", "10:00 AM", "01:00 PM"), ("Wednesday", "10:00 AM", "01:00 PM"), ("Friday", "10:00 AM", "01:00 PM")],
    "tth_10_1_sat_9_12": [("Tuesday", "10:00 AM", "01:00 PM"), ("Thursday", "10:00 AM", "01:00 PM"), ("Saturday", "09:00 AM", "12:00 PM")],
    "mwf_4_7":           [("Monday", "04:00 PM", "07:00 PM"), ("Wednesday", "04:00 PM", "07:00 PM"), ("Friday", "04:00 PM", "07:00 PM")],
    "ms_9_12":           [("Monday", "09:00 AM", "12:00 PM"), ("Tuesday", "09:00 AM", "12:00 PM"), ("Wednesday", "09:00 AM", "12:00 PM"), ("Thursday", "09:00 AM", "12:00 PM"), ("Friday", "09:00 AM", "12:00 PM"), ("Saturday", "09:00 AM", "12:00 PM")],
    "mwf_10_1_4_7":      [("Monday", "10:00 AM", "01:00 PM"), ("Wednesday", "10:00 AM", "01:00 PM"), ("Friday", "10:00 AM", "01:00 PM"), ("Monday", "04:00 PM", "07:00 PM"), ("Wednesday", "04:00 PM", "07:00 PM"), ("Friday", "04:00 PM", "07:00 PM")],
    "mwf_9_5":           [("Monday", "09:00 AM", "05:00 PM"), ("Wednesday", "09:00 AM", "05:00 PM"), ("Friday", "09:00 AM", "05:00 PM")],
    "tts_2_5":           [("Tuesday", "02:00 PM", "05:00 PM"), ("Thursday", "02:00 PM", "05:00 PM"), ("Saturday", "02:00 PM", "05:00 PM")],
}

# ═══════════════════════════════════════════════════════════════════════════════
# PATIENTS — 50 patients (Indore/Bhopal, MP)
# ═══════════════════════════════════════════════════════════════════════════════

LOCALITIES = [
    "Vijay Nagar", "Palasia", "Sapna Sangeeta", "Bhawarkuan", "Rajwada",
    "Scheme No. 54", "Scheme No. 78", "MR-10 Road", "AB Road",
    "Sudama Nagar", "Annapurna Road", "Rau", "Dewas Naka", "Banganga",
    "Mahalaxmi Nagar", "Bhanwarkuan", "LIG Colony", "Mhow",
    "Aerodrome Road", "Ring Road", "New Palasia", "South Tukoganj",
    "Geeta Bhawan", "Khajrana", "Musakhedi", "Pipliyahana",
]

MALE_NAMES = ["Ramesh", "Suresh", "Amit", "Rahul", "Vikram", "Karan", "Rajesh", "Arjun",
              "Vijay", "Kabir", "Rohan", "Sanjay", "Harish", "Manish", "Abhishek", "Vivek",
              "Gaurav", "Nitin", "Prakash", "Mohan", "Ashok", "Deepak", "Ravi", "Anil"]
FEMALE_NAMES = ["Priya", "Sunita", "Anjali", "Sneha", "Pooja", "Neha", "Aisha", "Meera",
                "Aditi", "Jyoti", "Divya", "Kiran", "Deepa", "Ritu", "Kavita", "Suman",
                "Geeta", "Rekha", "Lata", "Nisha", "Shobha", "Anita", "Seema", "Usha"]
LAST_NAMES = ["Sharma", "Patel", "Verma", "Malhotra", "Kumar", "Singh", "Gupta", "Joshi",
              "Chawla", "Nair", "Rao", "Das", "Sen", "Bose", "Mehta", "Trivedi",
              "Mishra", "Pandey", "Iyer", "Dubey", "Agrawal", "Soni", "Shukla", "Tiwari"]

# ═══════════════════════════════════════════════════════════════════════════════
# BILLING CATALOG (KB source: diagnostics_pricing.json, surgery_pricing.json, billing_faqs.json)
# ═══════════════════════════════════════════════════════════════════════════════

BILLING_DATA = [
    ("General Physician Consultation",       "Consultation",   500,   "BILL_GEN_CONS"),
    ("Specialist Doctor Consultation",       "Consultation",   800,   "BILL_SPEC_CONS"),
    ("Super-Specialist Doctor Consultation", "Consultation",   1200,  "BILL_SUP_CONS"),
    ("Emergency Consultation",               "Consultation",   500,   "BILL_ER_CONS"),
    ("General Ward Bed Charge (per day)",    "Ward",           1500,  "BILL_GEN_BED"),
    ("Semi-Private Room Charge (per day)",   "Ward",           3000,  "BILL_SEMI_BED"),
    ("Private AC Room Charge (per day)",     "Ward",           5000,  "BILL_PVT_BED"),
    ("Deluxe Room Charge (per day)",         "Ward",           7500,  "BILL_DEL_BED"),
    ("Super Deluxe Suite Charge (per day)",  "Ward",           12000, "BILL_SUITE_BED"),
    ("ICU Bed Charge (per day)",             "Ward",           8000,  "BILL_ICU_BED"),
    ("NICU Bed Charge (per day)",            "Ward",           10000, "BILL_NICU_BED"),
    ("CCU Bed Charge (per day)",             "Ward",           8000,  "BILL_CCU_BED"),
    ("Complete Blood Count (CBC)",           "Lab Test",       350,   "BILL_CBC_TEST"),
    ("Thyroid Profile (T3, T4, TSH)",        "Lab Test",       750,   "BILL_THY_TEST"),
    ("Lipid Profile (Cholesterol)",          "Lab Test",       650,   "BILL_LIP_TEST"),
    ("HbA1c Blood Glucose Test",             "Lab Test",       450,   "BILL_GLU_TEST"),
    ("Liver Function Test (LFT)",            "Lab Test",       900,   "BILL_LFT_TEST"),
    ("Kidney Function Test (KFT)",           "Lab Test",       850,   "BILL_KFT_TEST"),
    ("Serum Vitamin D",                      "Lab Test",       600,   "BILL_VITD_TEST"),
    ("Chest X-Ray Digital",                  "Radiology",      600,   "BILL_XRAY_CHEST"),
    ("Ultrasound (USG) Abdomen",             "Radiology",      1200,  "BILL_USG_ABD"),
    ("CT Scan Head/Brain",                   "Radiology",      3500,  "BILL_CT_HEAD"),
    ("MRI Brain",                            "Radiology",      6000,  "BILL_MRI_BRAIN"),
    ("MRI Spine Lumbar",                     "Radiology",      6000,  "BILL_MRI_LUM"),
    ("2D Echocardiography",                  "Radiology",      1800,  "BILL_ECHO"),
    ("Color Doppler Ultrasound",             "Radiology",      2000,  "BILL_DOPPLER"),
    ("Appendectomy (Laparoscopic)",          "Surgery",        45000, "BILL_SURG_APPY"),
    ("Cholecystectomy (Laparoscopic)",       "Surgery",        55000, "BILL_SURG_CHOLE"),
    ("Hernia Repair (Laparoscopic)",         "Surgery",        50000, "BILL_SURG_HERNIA"),
    ("Caesarean Section (LSCS)",             "Surgery",        65000, "BILL_SURG_LSCS"),
    ("Total Knee Replacement (Unilateral)",  "Surgery",        250000,"BILL_SURG_TKR"),
    ("Cataract Surgery (Phaco + IOL)",       "Surgery",        25000, "BILL_SURG_CATA"),
    ("Silver Health Check-Up Package",       "Health Package", 2999,  "BILL_PKG_SILVER"),
    ("Gold Health Check-Up Package",         "Health Package", 5999,  "BILL_PKG_GOLD"),
    ("Platinum Health Check-Up Package",     "Health Package", 11999, "BILL_PKG_PLAT"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# INSURANCE PROVIDERS (KB source: insurance_tpa_list.json, insurance_faqs.json)
# ═══════════════════════════════════════════════════════════════════════════════

INSURANCE_DATA = [
    ("Star Health & Allied Insurance",  True,  "1800-425-2255"),
    ("HDFC ERGO General Insurance",     True,  "1800-2700-700"),
    ("Niva Bupa Health Insurance",      True,  "1800-309-7575"),
    ("Care Health Insurance",           True,  "1800-102-4488"),
    ("ICICI Lombard General Insurance", False, "1800-2666"),
    ("Bajaj Allianz Health Insurance",  False, "1800-209-0144"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# WARD MANAGEMENT (KB-aligned pricing)
# ═══════════════════════════════════════════════════════════════════════════════

WARD_DATA = [
    ("General Ward",       80, 52, 1500),
    ("Semi-Private Room",  40, 24, 3000),
    ("Private AC Room",    30, 18, 5000),
    ("Deluxe Room",        20, 10, 7500),
    ("Super Deluxe Suite",  5,  2, 12000),
    ("ICU",                20, 12, 8000),
    ("NICU",               10,  5, 10000),
    ("CCU",                10,  6, 8000),
]

# ═══════════════════════════════════════════════════════════════════════════════
# LAB TESTS
# ═══════════════════════════════════════════════════════════════════════════════

LAB_TESTS = [
    ("Complete Blood Count (CBC)", "Hemoglobin: {hb} g/dL (Normal: 12-16), WBC: {wbc} /cumm (Normal: 4000-11000)"),
    ("Thyroid Profile (T3, T4, TSH)", "TSH: {tsh} uIU/mL (Normal: 0.4-4.5)"),
    ("Lipid Profile", "Total Cholesterol: {chol} mg/dL (Normal: <200), HDL: {hdl} mg/dL (Normal: >40)"),
    ("HbA1c (Glycated Hemoglobin)", "HbA1c: {hba1c}% (Normal: <5.7%, Diabetic: >6.5%)"),
    ("Serum Vitamin D", "25-OH Vitamin D: {vitd} ng/mL (Normal: 30-100)"),
    ("Kidney Function Test (KFT)", "Serum Creatinine: {creat} mg/dL (Normal: 0.6-1.2), Urea: {urea} mg/dL"),
    ("Liver Function Test (LFT)", "SGOT: {sgot} U/L (Normal: <40), SGPT: {sgpt} U/L (Normal: <40)"),
]


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SEED FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

async def seed_database():
    logger.info("=" * 60)
    logger.info("LIFELINE MULTI-SPECIALITY HOSPITAL — DATABASE SEED")
    logger.info("=" * 60)

    # 1. Drop and recreate all tables
    try:
        logger.info("Dropping all existing tables...")
        async with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(text(f'DROP TABLE IF EXISTS "{table.name}" CASCADE;'))
            await conn.run_sync(Base.metadata.create_all)
        logger.success("Clean schema created.")
    except Exception as e:
        logger.error(f"Schema rebuild failed: {e}")
        return

    db = AsyncSessionLocal()
    try:
        # ─── A. DEPARTMENTS (16) ─────────────────────────────────────────────
        logger.info("Seeding 15 departments (from KB)...")
        dept_map = {}
        departments = []
        for d in DEPARTMENTS_DATA:
            dept = Department(NAME=d["name"], DESCRIPTION=d["desc"], LOCATION=d["location"])
            departments.append(dept)
        db.add_all(departments)
        await db.commit()
        dept_ids = {}  # name -> ID (plain ints, no ORM expiry issues)
        for dept in departments:
            await db.refresh(dept)
            dept_map[dept.NAME] = dept
            dept_ids[dept.NAME] = dept.ID
        logger.success(f"  {len(departments)} departments seeded.")

        # ─── B. DOCTORS (38, KB-exact) ──────────────────────────────────────
        logger.info("Seeding 35 doctors (from KB doctor_directory.json)...")
        doctors = []
        doc_ids = []  # parallel list of plain int IDs
        for idx, d in enumerate(DOCTORS_DATA, start=1):
            first = d["name"].replace("Dr. ", "").split()[0].lower()
            last = d["name"].replace("Dr. ", "").split()[-1].lower()
            email = f"{first}.{last}@lifelinehospital.in"
            phone = f"+91 755 {idx:04d} {random.randint(100,999)}"

            doctor = Doctor(
                NAME=d["name"],
                SPECIALIZATION=d["spec"],
                QUALIFICATION=d["qual"],
                EXPERIENCE_YEARS=d["exp"],
                CONSULTATION_FEE=d["fee"],
                LANGUAGES="Hindi, English",
                STATUS="Active",
                EMAIL=email,
                PHONE=phone,
                DEPARTMENT_ID=dept_ids[d["dept"]],
            )
            doctors.append(doctor)
        db.add_all(doctors)
        await db.commit()
        for doc in doctors:
            await db.refresh(doc)
            doc_ids.append(doc.ID)
        doc_names = [d.NAME for d in doctors]  # cache before next commit expires them
        logger.success(f"  {len(doctors)} doctors seeded.")

        # ─── C. DOCTOR SCHEDULES (KB-exact patterns) ─────────────────────────
        logger.info("Seeding doctor schedules (from KB availability)...")
        schedules = []
        for doc_data, doc in zip(DOCTORS_DATA, doctors):
            pattern = SCHEDULE_MAP.get(doc_data["sched"], [])
            for day, start, end in pattern:
                schedules.append(
                    DoctorSchedule(
                        DOCTOR_ID=doc_ids[doctors.index(doc)],
                        DAY_OF_WEEK=day,
                        START_TIME=start,
                        END_TIME=end,
                        STATUS="Available",
                    )
                )
        db.add_all(schedules)
        await db.commit()
        logger.success(f"  {len(schedules)} schedules seeded.")

        # ─── D. PATIENTS (50) ───────────────────────────────────────────────
        logger.info("Seeding 50 patients...")
        patients = []
        for i in range(1, 51):
            gender = random.choice(["Male", "Female"])
            first = random.choice(MALE_NAMES if gender == "Male" else FEMALE_NAMES)
            last = random.choice(LAST_NAMES)
            p_name = f"{first} {last}"
            phone = f"+91 99887 {i:05d}"
            email = f"{first.lower()}.{last.lower()}{i}@gmail.com"
            age = random.randint(5, 82)
            locality = random.choice(LOCALITIES)
            address = f"{random.randint(1, 200)}, {locality}, Bhopal, Madhya Pradesh"

            patients.append(Patient(
                NAME=p_name, AGE=age, GENDER=gender,
                PHONE=phone, EMAIL=email, ADDRESS=address,
            ))
        db.add_all(patients)
        await db.commit()
        pat_ids = []
        for p in patients:
            await db.refresh(p)
            pat_ids.append(p.ID)
        pat_names = [p.NAME for p in patients]  # cache before next commit expires them
        logger.success(f"  {len(patients)} patients seeded.")

        # ─── E. APPOINTMENTS (100) ──────────────────────────────────────────
        logger.info("Seeding 100 appointments...")
        time_slots = ["09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM",
                      "12:00 PM", "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM", "04:00 PM",
                      "04:30 PM", "05:00 PM"]
        today = datetime.date.today()
        used_slots = set()
        appointments = []

        # Exclude emergency doctors from OPD appointments
        emergency_dept_id = dept_ids["Emergency Medicine"]
        appointable_idx = [i for i, d in enumerate(DOCTORS_DATA) if d["dept"] not in ("Emergency Medicine",)]

        for i in range(1, 151):  # Generate extra to account for collisions
            if len(appointments) >= 100:
                break
            p_idx = random.randint(0, len(patients) - 1)
            d_idx = random.choice(appointable_idx)
            day_offset = random.randint(-15, 10)
            appt_date = today + datetime.timedelta(days=day_offset)
            time_slot = random.choice(time_slots)

            slot_key = (doc_names[d_idx], time_slot, str(appt_date))
            if slot_key in used_slots:
                continue
            used_slots.add(slot_key)

            status = "Confirmed" if day_offset >= -2 else "Completed"
            if day_offset < 0 and random.random() < 0.1:
                status = "Cancelled"

            appointments.append(Appointment(
                PATIENT_NAME=pat_names[p_idx],
                DOCTOR_NAME=doc_names[d_idx],
                APPOINTMENT_TIME=time_slot,
                APPOINTMENT_DATE=appt_date,
                PATIENT_ID=pat_ids[p_idx],
                DOCTOR_ID=doc_ids[d_idx],
                STATUS=status,
            ))
        db.add_all(appointments)
        await db.commit()
        logger.success(f"  {len(appointments)} appointments seeded.")

        # ─── F. BILLING CATALOG (35 items, KB-aligned pricing) ──────────────
        logger.info("Seeding 35 billing catalog items...")
        billing_items = [
            BillingCatalog(ITEM_NAME=name, CATEGORY=cat, PRICE=price, CODE=code)
            for name, cat, price, code in BILLING_DATA
        ]
        db.add_all(billing_items)
        await db.commit()
        logger.success(f"  {len(billing_items)} billing items seeded.")

        # ─── G. INSURANCE PROVIDERS (6) ─────────────────────────────────────
        logger.info("Seeding 6 insurance providers...")
        insurances = [
            InsuranceProvider(NAME=name, CASHLESS_AVAILABLE=cashless, HELPLINE=helpline)
            for name, cashless, helpline in INSURANCE_DATA
        ]
        db.add_all(insurances)
        await db.commit()
        logger.success(f"  {len(insurances)} insurance providers seeded.")

        # ─── H. WARD MANAGEMENT (8 wards) ───────────────────────────────────
        logger.info("Seeding 8 ward configurations...")
        wards = [
            WardManagement(WARD_TYPE=wtype, TOTAL_BEDS=total, OCCUPIED_BEDS=occ, PRICE_PER_DAY=price)
            for wtype, total, occ, price in WARD_DATA
        ]
        db.add_all(wards)
        await db.commit()
        total_beds = sum(t for _, t, _, _ in WARD_DATA)
        logger.success(f"  {len(wards)} wards seeded ({total_beds} total beds).")

        # ─── I. LAB REPORTS (80) ────────────────────────────────────────────
        logger.info("Generating 80 lab reports...")
        reports = []
        for i in range(1, 81):
            test = random.choice(LAB_TESTS)
            test_name = test[0]
            day_offset = random.randint(-30, 0)
            ordered_date = today + datetime.timedelta(days=day_offset)
            status = "Completed" if day_offset < -1 else random.choice(["Completed", "Pending"])

            if status == "Completed":
                if "CBC" in test_name:
                    result = test[1].format(hb=round(random.uniform(9.5, 15.5), 1), wbc=random.randint(3500, 12500))
                elif "Thyroid" in test_name:
                    result = test[1].format(tsh=round(random.uniform(0.2, 7.8), 2))
                elif "Lipid" in test_name:
                    result = test[1].format(chol=random.randint(150, 260), hdl=random.randint(32, 58))
                elif "HbA1c" in test_name:
                    result = test[1].format(hba1c=round(random.uniform(4.8, 8.2), 1))
                elif "Vitamin D" in test_name:
                    result = test[1].format(vitd=random.randint(12, 65))
                elif "Kidney" in test_name:
                    result = test[1].format(creat=round(random.uniform(0.5, 1.8), 2), urea=random.randint(15, 55))
                else:
                    result = test[1].format(sgot=random.randint(15, 75), sgpt=random.randint(12, 85))
            else:
                result = None

            p_idx = random.randint(0, len(patients) - 1)
            reports.append(LabReport(
                PATIENT_ID=pat_ids[p_idx], TEST_NAME=test_name,
                RESULT=result, STATUS=status, ORDERED_DATE=ordered_date,
            ))
        db.add_all(reports)
        await db.commit()
        logger.success(f"  {len(reports)} lab reports seeded.")

        # ─── J. AUDIT LOG (system init record) ──────────────────────────────
        audit = AuditLog(
            ACTION_TYPE="SYSTEM_INITIALIZATION",
            USER_ID="system_admin",
            ACTION_DETAILS=(
                f"Lifeline Multi-Speciality Hospital DB initialized. "
                f"{len(departments)} departments, {len(doctors)} doctors, "
                f"{len(schedules)} schedules, {len(patients)} patients, "
                f"{len(appointments)} appointments, {len(billing_items)} billing items, "
                f"{len(insurances)} insurance, {len(wards)} wards ({total_beds} beds), "
                f"{len(reports)} lab reports."
            ),
        )
        db.add(audit)
        await db.commit()

        logger.success("=" * 60)
        logger.success("LIFELINE HOSPITAL DATABASE SEEDED SUCCESSFULLY!")
        logger.success(f"  Departments: {len(departments)} | Doctors: {len(doctors)}")
        logger.success(f"  Schedules: {len(schedules)} | Patients: {len(patients)}")
        logger.success(f"  Appointments: {len(appointments)} | Billing: {len(billing_items)}")
        logger.success(f"  Insurance: {len(insurances)} | Wards: {len(wards)} ({total_beds} beds)")
        logger.success(f"  Lab Reports: {len(reports)}")
        logger.success("=" * 60)

    except Exception as e:
        await db.rollback()
        logger.error(f"Seed failed: {e}")
        raise
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
