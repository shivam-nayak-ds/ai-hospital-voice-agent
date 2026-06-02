import datetime
import random
from sqlalchemy import text
from src.db.session import engine, Base, SessionLocal
from src.db.models import (
    Department, Doctor, DoctorSchedule, Patient, Appointment,
    BillingCatalog, InsuranceProvider, WardManagement, LabReport,
    ConversationLog, AgentEvent, AuditLog
)
from src.utils.logger import custom_logger as logger
from config.settings import settings

# ═══════════════════════════════════════════════════════════════════════════════
# LIFELINE MULTI-SPECIALITY HOSPITAL — PRODUCTION DATABASE SEED
# Location: Vijay Nagar, Sector 26, Indore, Madhya Pradesh
# 250 Beds | 16 Departments | 48 Doctors | 24x7 Emergency, ICU, NICU, Pharmacy
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Fixed Department Data ──────────────────────────────────────────────────

DEPARTMENTS_DATA = [
    {"name": "Cardiology",              "description": "Comprehensive cardiac care including interventional cardiology, electrophysiology, cardiac imaging, heart failure management, and preventive cardiology.", "location": "Building A, 2nd Floor"},
    {"name": "Neurology",               "description": "Diagnosis and treatment of disorders of the brain, spinal cord, and peripheral nerves including stroke, epilepsy, Parkinson's, dementia, and headache disorders.", "location": "Building A, 3rd Floor"},
    {"name": "Orthopedics",             "description": "Musculoskeletal care including joint replacement, arthroscopy, sports medicine, spine surgery, trauma surgery, and fracture management.", "location": "Building B, 1st Floor"},
    {"name": "General Medicine",        "description": "Primary and internal medicine services covering fever, infections, diabetes, hypertension, thyroid disorders, and comprehensive health check-ups.", "location": "Building A, Ground Floor"},
    {"name": "General Surgery",         "description": "Surgical services including laparoscopic surgery, hernia repair, appendectomy, cholecystectomy, breast surgery, and wound management.", "location": "Building B, Ground Floor"},
    {"name": "Pediatrics",              "description": "Complete child healthcare from newborn to adolescent including neonatology, immunization, growth monitoring, and pediatric emergencies.", "location": "Building C, 1st Floor"},
    {"name": "Gynecology & Obstetrics", "description": "Women's health services including antenatal care, high-risk pregnancy management, normal and cesarean delivery, laparoscopic gynae surgery, and infertility treatment.", "location": "Building C, 2nd Floor"},
    {"name": "Oncology",                "description": "Cancer diagnosis and treatment including medical oncology, surgical oncology, radiation therapy, chemotherapy, and palliative care.", "location": "Building B, 3rd Floor"},
    {"name": "Dermatology",             "description": "Skin, hair, and nail disorder management including medical dermatology, cosmetic procedures, laser treatments, and allergy testing.", "location": "Building A, 1st Floor"},
    {"name": "Gastroenterology",        "description": "Digestive system care including endoscopy, colonoscopy, ERCP, liver disease management, and treatment of IBD, IBS, and peptic ulcers.", "location": "Building B, 2nd Floor"},
    {"name": "Ophthalmology",           "description": "Eye care services including cataract surgery (phaco), glaucoma management, retina clinic, LASIK, squint correction, and pediatric ophthalmology.", "location": "Building C, Ground Floor"},
    {"name": "ENT",                     "description": "Ear, nose, and throat care including hearing assessment, sinus surgery, tonsillectomy, adenoidectomy, voice disorders, and vertigo management.", "location": "Building C, Ground Floor"},
    {"name": "Nephrology",              "description": "Kidney care including dialysis, kidney transplant evaluation, CKD management, hypertension related to kidney disease, and electrolyte disorders.", "location": "Building A, 4th Floor"},
    {"name": "Pulmonology",             "description": "Respiratory care including asthma, COPD, tuberculosis, pneumonia, lung function testing, bronchoscopy, and sleep disorders.", "location": "Building A, 4th Floor"},
    {"name": "Psychiatry",              "description": "Mental health services including depression, anxiety disorders, OCD, schizophrenia, addiction treatment, counselling, and psychotherapy.", "location": "Building C, 3rd Floor"},
    {"name": "Emergency Medicine",      "description": "24x7 emergency and trauma care including triage, resuscitation, acute medical emergencies, polytrauma management, and critical care stabilisation.", "location": "Building A, Ground Floor"},
]

# ─── Fixed Doctor Data (48 Doctors — 3 per department) ─────────────────────

DOCTORS_DATA = [
    # ── Cardiology (3) ──
    {"name": "Dr. Rajesh Sharma",       "spec": "Interventional Cardiologist",  "qual": "MBBS, MD (Medicine), DM (Cardiology)", "exp": 18, "fee": 1200, "lang": "Hindi, English",          "dept": "Cardiology",              "status": "Active"},
    {"name": "Dr. Priya Malhotra",      "spec": "Clinical Cardiologist",        "qual": "MBBS, MD (Medicine), DNB (Cardiology)", "exp": 12, "fee": 1000, "lang": "Hindi, English, Punjabi",  "dept": "Cardiology",              "status": "Active"},
    {"name": "Dr. Amit Joshi",          "spec": "Electrophysiologist",          "qual": "MBBS, MD (Medicine), DM (Cardiology), Fellowship (EP)", "exp": 10, "fee": 1200, "lang": "Hindi, English, Marathi", "dept": "Cardiology", "status": "Active"},

    # ── Neurology (3) ──
    {"name": "Dr. Suresh Verma",        "spec": "Neurologist",                  "qual": "MBBS, MD (Medicine), DM (Neurology)", "exp": 20, "fee": 1200, "lang": "Hindi, English",           "dept": "Neurology",               "status": "Active"},
    {"name": "Dr. Kavita Reddy",        "spec": "Stroke Specialist",            "qual": "MBBS, MD (Medicine), DM (Neurology), Fellowship (Stroke)", "exp": 14, "fee": 1000, "lang": "Hindi, English, Telugu", "dept": "Neurology", "status": "Active"},
    {"name": "Dr. Rohit Pandey",        "spec": "Epilepsy Specialist",          "qual": "MBBS, MD (Medicine), DM (Neurology)", "exp": 9, "fee": 1000, "lang": "Hindi, English",            "dept": "Neurology",               "status": "Active"},

    # ── Orthopedics (3) ──
    {"name": "Dr. Vikram Singh",        "spec": "Joint Replacement Surgeon",    "qual": "MBBS, MS (Orthopedics), Fellowship (Arthroplasty)", "exp": 22, "fee": 1000, "lang": "Hindi, English",  "dept": "Orthopedics",             "status": "Active"},
    {"name": "Dr. Anjali Mehta",        "spec": "Sports Medicine Specialist",   "qual": "MBBS, DNB (Orthopedics), Fellowship (Sports Medicine)", "exp": 11, "fee": 800, "lang": "Hindi, English, Gujarati", "dept": "Orthopedics", "status": "Active"},
    {"name": "Dr. Karan Trivedi",       "spec": "Spine Surgeon",                "qual": "MBBS, MS (Orthopedics), Fellowship (Spine Surgery)", "exp": 15, "fee": 1200, "lang": "Hindi, English",  "dept": "Orthopedics",             "status": "Active"},

    # ── General Medicine (3) ──
    {"name": "Dr. Sanjay Gupta",        "spec": "General Physician",            "qual": "MBBS, MD (General Medicine)",         "exp": 25, "fee": 500,  "lang": "Hindi, English",           "dept": "General Medicine",        "status": "Active"},
    {"name": "Dr. Meera Iyer",          "spec": "Internal Medicine Specialist",  "qual": "MBBS, MD (Internal Medicine), FICP", "exp": 16, "fee": 600,  "lang": "Hindi, English, Tamil",    "dept": "General Medicine",        "status": "Active"},
    {"name": "Dr. Harish Mishra",       "spec": "Diabetologist",                "qual": "MBBS, MD (Medicine), Fellowship (Diabetology)", "exp": 13, "fee": 600, "lang": "Hindi, English",   "dept": "General Medicine",        "status": "Active"},

    # ── General Surgery (3) ──
    {"name": "Dr. Vijay Kumar",         "spec": "Laparoscopic Surgeon",         "qual": "MBBS, MS (General Surgery), Fellowship (Minimal Access Surgery)", "exp": 19, "fee": 800, "lang": "Hindi, English", "dept": "General Surgery", "status": "Active"},
    {"name": "Dr. Deepa Das",           "spec": "General Surgeon",              "qual": "MBBS, MS (General Surgery)",          "exp": 14, "fee": 700,  "lang": "Hindi, English, Bengali",  "dept": "General Surgery",         "status": "Active"},
    {"name": "Dr. Manish Patel",        "spec": "Surgical Oncologist",          "qual": "MBBS, MS (Surgery), MCh (Surgical Oncology)", "exp": 10, "fee": 1000, "lang": "Hindi, English, Gujarati", "dept": "General Surgery", "status": "Active"},

    # ── Pediatrics (3) ──
    {"name": "Dr. Sunita Rao",          "spec": "General Pediatrician",         "qual": "MBBS, MD (Pediatrics)",               "exp": 17, "fee": 600,  "lang": "Hindi, English",           "dept": "Pediatrics",              "status": "Active"},
    {"name": "Dr. Abhishek Nair",       "spec": "Neonatologist",                "qual": "MBBS, MD (Pediatrics), DM (Neonatology)", "exp": 12, "fee": 800, "lang": "Hindi, English, Malayalam", "dept": "Pediatrics",          "status": "Active"},
    {"name": "Dr. Ritu Chawla",         "spec": "Pediatric Cardiologist",       "qual": "MBBS, MD (Pediatrics), DM (Pediatric Cardiology)", "exp": 8, "fee": 1000, "lang": "Hindi, English, Punjabi", "dept": "Pediatrics", "status": "Active"},

    # ── Gynecology & Obstetrics (3) ──
    {"name": "Dr. Neha Saxena",         "spec": "Obstetrician & Gynaecologist", "qual": "MBBS, MS (OBG), FRCOG",              "exp": 20, "fee": 800,  "lang": "Hindi, English",           "dept": "Gynecology & Obstetrics", "status": "Active"},
    {"name": "Dr. Pooja Agarwal",       "spec": "High-Risk Pregnancy Specialist","qual": "MBBS, MD (OBG), Fellowship (Maternal-Fetal Medicine)", "exp": 14, "fee": 1000, "lang": "Hindi, English", "dept": "Gynecology & Obstetrics", "status": "Active"},
    {"name": "Dr. Divya Tiwari",        "spec": "Infertility Specialist",       "qual": "MBBS, MS (OBG), Fellowship (Reproductive Medicine)", "exp": 11, "fee": 1000, "lang": "Hindi, English, Marathi", "dept": "Gynecology & Obstetrics", "status": "Active"},

    # ── Oncology (3) ──
    {"name": "Dr. Arjun Sen",           "spec": "Medical Oncologist",           "qual": "MBBS, MD (Medicine), DM (Medical Oncology)", "exp": 16, "fee": 1200, "lang": "Hindi, English, Bengali", "dept": "Oncology", "status": "Active"},
    {"name": "Dr. Sneha Kulkarni",      "spec": "Radiation Oncologist",         "qual": "MBBS, MD (Radiation Oncology)",       "exp": 12, "fee": 1000, "lang": "Hindi, English, Marathi",  "dept": "Oncology",                "status": "Active"},
    {"name": "Dr. Kabir Bose",          "spec": "Surgical Oncologist",          "qual": "MBBS, MS (Surgery), MCh (Surgical Oncology)", "exp": 15, "fee": 1200, "lang": "Hindi, English, Bengali", "dept": "Oncology", "status": "Active"},

    # ── Dermatology (3) ──
    {"name": "Dr. Aditi Deshmukh",      "spec": "Dermatologist",                "qual": "MBBS, MD (Dermatology, Venereology & Leprosy)", "exp": 13, "fee": 700, "lang": "Hindi, English, Marathi", "dept": "Dermatology", "status": "Active"},
    {"name": "Dr. Rahul Kapoor",        "spec": "Cosmetologist",                "qual": "MBBS, DVD, Fellowship (Cosmetic Dermatology)", "exp": 9, "fee": 800, "lang": "Hindi, English, Punjabi", "dept": "Dermatology", "status": "Active"},
    {"name": "Dr. Kiran Saxena",        "spec": "Trichologist",                 "qual": "MBBS, MD (Dermatology), Fellowship (Trichology)", "exp": 7, "fee": 600, "lang": "Hindi, English",  "dept": "Dermatology",             "status": "Active"},

    # ── Gastroenterology (3) ──
    {"name": "Dr. Vivek Bhatt",         "spec": "Gastroenterologist",           "qual": "MBBS, MD (Medicine), DM (Gastroenterology)", "exp": 18, "fee": 1000, "lang": "Hindi, English",  "dept": "Gastroenterology",        "status": "Active"},
    {"name": "Dr. Jyoti Sharma",        "spec": "Hepatologist",                 "qual": "MBBS, MD (Medicine), DM (Hepatology)", "exp": 14, "fee": 1000, "lang": "Hindi, English",          "dept": "Gastroenterology",        "status": "Active"},
    {"name": "Dr. Ramesh Dubey",        "spec": "Endoscopist",                  "qual": "MBBS, MD (Medicine), DM (Gastroenterology), Fellowship (Therapeutic Endoscopy)", "exp": 11, "fee": 800, "lang": "Hindi, English", "dept": "Gastroenterology", "status": "Active"},

    # ── Ophthalmology (3) ──
    {"name": "Dr. Aisha Khan",          "spec": "Cataract & Refractive Surgeon","qual": "MBBS, MS (Ophthalmology), Fellowship (Phaco & IOL)", "exp": 15, "fee": 800, "lang": "Hindi, English, Urdu", "dept": "Ophthalmology", "status": "Active"},
    {"name": "Dr. Rohan Desai",         "spec": "Retina Specialist",            "qual": "MBBS, MS (Ophthalmology), Fellowship (Vitreo-Retina)", "exp": 12, "fee": 1000, "lang": "Hindi, English, Gujarati", "dept": "Ophthalmology", "status": "Active"},
    {"name": "Dr. Swati Patil",         "spec": "Glaucoma Specialist",          "qual": "MBBS, DNB (Ophthalmology), Fellowship (Glaucoma)", "exp": 10, "fee": 800, "lang": "Hindi, English, Marathi", "dept": "Ophthalmology", "status": "Active"},

    # ── ENT (3) ──
    {"name": "Dr. Nikhil Soni",         "spec": "ENT Surgeon",                  "qual": "MBBS, MS (ENT)",                     "exp": 16, "fee": 700,  "lang": "Hindi, English",           "dept": "ENT",                     "status": "Active"},
    {"name": "Dr. Megha Jain",          "spec": "Audiologist & ENT Specialist",  "qual": "MBBS, MS (ENT), Fellowship (Otology)", "exp": 11, "fee": 700, "lang": "Hindi, English",           "dept": "ENT",                     "status": "Active"},
    {"name": "Dr. Siddharth Tomar",     "spec": "Head & Neck Surgeon",          "qual": "MBBS, MS (ENT), MCh (Head & Neck Surgery)", "exp": 13, "fee": 800, "lang": "Hindi, English",    "dept": "ENT",                     "status": "Active"},

    # ── Nephrology (3) ──
    {"name": "Dr. Ashok Shrivastava",   "spec": "Nephrologist",                 "qual": "MBBS, MD (Medicine), DM (Nephrology)", "exp": 21, "fee": 1000, "lang": "Hindi, English",          "dept": "Nephrology",              "status": "Active"},
    {"name": "Dr. Pallavi Mishra",      "spec": "Transplant Nephrologist",      "qual": "MBBS, MD (Medicine), DM (Nephrology), Fellowship (Transplant)", "exp": 14, "fee": 1200, "lang": "Hindi, English", "dept": "Nephrology", "status": "Active"},
    {"name": "Dr. Gaurav Chouhan",      "spec": "Dialysis Specialist",          "qual": "MBBS, MD (Medicine), DM (Nephrology)", "exp": 9, "fee": 800,  "lang": "Hindi, English",           "dept": "Nephrology",              "status": "Active"},

    # ── Pulmonology (3) ──
    {"name": "Dr. Anand Shukla",        "spec": "Pulmonologist",                "qual": "MBBS, MD (Pulmonary Medicine)",       "exp": 17, "fee": 800,  "lang": "Hindi, English",           "dept": "Pulmonology",             "status": "Active"},
    {"name": "Dr. Rekha Dwivedi",       "spec": "Chest & TB Specialist",        "qual": "MBBS, MD (TB & Respiratory Diseases)", "exp": 22, "fee": 700, "lang": "Hindi, English",           "dept": "Pulmonology",             "status": "Active"},
    {"name": "Dr. Tarun Agrawal",       "spec": "Interventional Pulmonologist", "qual": "MBBS, MD (Pulmonary Medicine), Fellowship (Interventional Pulmonology)", "exp": 10, "fee": 1000, "lang": "Hindi, English", "dept": "Pulmonology", "status": "Active"},

    # ── Psychiatry (3) ──
    {"name": "Dr. Anurag Dubey",        "spec": "Psychiatrist",                 "qual": "MBBS, MD (Psychiatry)",               "exp": 15, "fee": 800,  "lang": "Hindi, English",           "dept": "Psychiatry",              "status": "Active"},
    {"name": "Dr. Nandini Rao",         "spec": "Clinical Psychologist",        "qual": "M.Phil (Clinical Psychology), RCI Registered", "exp": 10, "fee": 600, "lang": "Hindi, English, Kannada", "dept": "Psychiatry", "status": "Active"},
    {"name": "Dr. Mohit Kashyap",       "spec": "Addiction Specialist",         "qual": "MBBS, MD (Psychiatry), Fellowship (Addiction Medicine)", "exp": 12, "fee": 800, "lang": "Hindi, English", "dept": "Psychiatry", "status": "Active"},

    # ── Emergency Medicine (3) ──
    {"name": "Dr. Sameer Rathore",      "spec": "Emergency Medicine Specialist","qual": "MBBS, MD (Emergency Medicine)",       "exp": 13, "fee": 500,  "lang": "Hindi, English",           "dept": "Emergency Medicine",      "status": "Active"},
    {"name": "Dr. Priyanka Chauhan",    "spec": "Trauma Specialist",            "qual": "MBBS, MS (General Surgery), Fellowship (Trauma)", "exp": 11, "fee": 500, "lang": "Hindi, English",  "dept": "Emergency Medicine",      "status": "Active"},
    {"name": "Dr. Akash Yadav",         "spec": "Critical Care Specialist",     "qual": "MBBS, MD (Medicine), FNB (Critical Care)", "exp": 8, "fee": 500, "lang": "Hindi, English",       "dept": "Emergency Medicine",      "status": "Active"},
]

# ─── Indore-Specific Patient Data ──────────────────────────────────────────

INDORE_LOCALITIES = [
    "Vijay Nagar", "Palasia", "Sapna Sangeeta", "Bhawarkuan", "Rajwada",
    "Scheme No. 54", "Scheme No. 78", "MR-10 Road", "AB Road",
    "Sudama Nagar", "Annapurna Road", "Rau", "Dewas Naka", "Banganga",
    "Mahalaxmi Nagar", "Bhanwarkuan", "LIG Colony", "Mhow",
    "Aerodrome Road", "Ring Road", "New Palasia", "South Tukoganj",
    "Geeta Bhawan", "Khajrana", "Musakhedi", "Pipliyahana",
    "Tilak Nagar", "Sneh Nagar", "Nanda Nagar", "Saket Nagar"
]

MALE_FIRST_NAMES = [
    "Ramesh", "Suresh", "Amit", "Rahul", "Vikram", "Karan", "Rajesh", "Arjun",
    "Vijay", "Kabir", "Rohan", "Sanjay", "Harish", "Manish", "Abhishek", "Vivek",
    "Gaurav", "Nitin", "Prakash", "Mohan", "Ashok", "Deepak", "Ravi", "Anil"
]

FEMALE_FIRST_NAMES = [
    "Priya", "Sunita", "Anjali", "Sneha", "Pooja", "Neha", "Aisha", "Meera",
    "Aditi", "Jyoti", "Divya", "Kiran", "Deepa", "Ritu", "Kavita", "Suman",
    "Geeta", "Rekha", "Lata", "Nisha", "Shobha", "Anita", "Seema", "Usha"
]

LAST_NAMES = [
    "Sharma", "Patel", "Verma", "Malhotra", "Kumar", "Singh", "Gupta", "Joshi",
    "Chawla", "Nair", "Rao", "Das", "Sen", "Bose", "Mehta", "Trivedi",
    "Mishra", "Pandey", "Iyer", "Dubey", "Agrawal", "Soni", "Shukla", "Tiwari"
]

# ─── Lab Tests ─────────────────────────────────────────────────────────────

LAB_TESTS = [
    ("Complete Blood Count (CBC)", "Hemoglobin: {hb} g/dL (Normal: 12-16), WBC: {wbc} /cumm (Normal: 4000-11000)"),
    ("Thyroid Profile (T3, T4, TSH)", "TSH: {tsh} uIU/mL (Normal: 0.4-4.5)"),
    ("Lipid Profile", "Total Cholesterol: {chol} mg/dL (Normal: <200), HDL: {hdl} mg/dL (Normal: >40)"),
    ("HbA1c (Glycated Hemoglobin)", "HbA1c: {hba1c}% (Normal: <5.7%, Diabetic: >6.5%)"),
    ("Serum Vitamin D", "25-OH Vitamin D: {vitd} ng/mL (Normal: 30-100)"),
    ("Kidney Function Test (KFT)", "Serum Creatinine: {creat} mg/dL (Normal: 0.6-1.2), Urea: {urea} mg/dL"),
    ("Liver Function Test (LFT)", "SGOT: {sgot} U/L (Normal: <40), SGPT: {sgpt} U/L (Normal: <40)")
]


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SEED FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def seed_database():
    # ─── PRODUCTION SAFETY GUARDRAIL ───────────────────────────────────────
    if settings.APP_ENV == "production":
        logger.critical("SECURITY BLOCK: Cannot run seed script in production environment!")
        logger.critical("Set APP_ENV to 'local' or 'staging' in .env to run this script.")
        return

    logger.info("═══ Lifeline Multi-Speciality Hospital — Database Seeding ═══")
    
    # 1. Reset tables
    try:
        logger.info("Dropping all existing database tables with CASCADE...")
        with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                logger.info(f"Dropping table: {table.name}...")
                conn.execute(text(f'DROP TABLE IF EXISTS "{table.name}" CASCADE;'))
        
        logger.info("Rebuilding clean database schema...")
        Base.metadata.create_all(bind=engine)
        logger.success("Clean database schema created successfully.")
    except Exception as e:
        logger.error(f"Failed to rebuild schemas: {e}")
        return

    db = SessionLocal()
    try:
        # ─── A. Seed Departments (16 Departments) ─────────────────────────────
        logger.info("Seeding 16 clinical departments...")
        dept_map = {}  # name -> Department object
        departments = []
        for d in DEPARTMENTS_DATA:
            dept = Department(NAME=d["name"], DESCRIPTION=d["description"], LOCATION=d["location"])
            departments.append(dept)
        db.add_all(departments)
        db.commit()
        for dept in departments:
            dept_map[dept.NAME] = dept
        logger.success(f"✅ {len(departments)} departments seeded.")

        # ─── B. Seed Doctors (48 Doctors — 3 per department) ──────────────────
        logger.info("Seeding 48 specialist doctors with full profiles...")
        doctors = []
        for idx, d in enumerate(DOCTORS_DATA, start=1):
            first = d["name"].replace("Dr. ", "").split()[0].lower()
            last = d["name"].replace("Dr. ", "").split()[-1].lower()
            email = f"{first}.{last}@lifelinehospital.in"
            phone = f"+91 731 {idx:04d} {random.randint(100,999)}"
            
            doctor = Doctor(
                NAME=d["name"],
                SPECIALIZATION=d["spec"],
                QUALIFICATION=d["qual"],
                EXPERIENCE_YEARS=d["exp"],
                CONSULTATION_FEE=d["fee"],
                LANGUAGES=d["lang"],
                STATUS=d["status"],
                EMAIL=email,
                PHONE=phone,
                DEPARTMENT_ID=dept_map[d["dept"]].ID
            )
            doctors.append(doctor)
        db.add_all(doctors)
        db.commit()
        logger.success(f"✅ {len(doctors)} doctors seeded.")

        # ─── C. Seed Doctor Schedules (288 Schedules — 6 days per doctor) ─────
        logger.info("Generating doctor schedules (Mon–Sat)...")
        working_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        schedules = []
        for doc in doctors:
            # Emergency docs have different schedule patterns
            is_emergency = "Emergency" in (doc.department.NAME if doc.department else "")
            
            for day in working_days:
                if is_emergency:
                    # Emergency doctors work in shifts
                    shift = random.choice([
                        ("08:00 AM", "04:00 PM"),
                        ("04:00 PM", "12:00 AM"),
                        ("12:00 AM", "08:00 AM")
                    ])
                    start, end = shift
                elif day == "Saturday":
                    start = random.choice(["09:00 AM", "10:00 AM"])
                    end = random.choice(["01:00 PM", "02:00 PM"])
                else:
                    start = random.choice(["09:00 AM", "09:30 AM", "10:00 AM"])
                    end = random.choice(["05:00 PM", "05:30 PM", "06:00 PM"])
                
                schedules.append(
                    DoctorSchedule(
                        DOCTOR_ID=doc.ID,
                        DAY_OF_WEEK=day,
                        START_TIME=start,
                        END_TIME=end,
                        STATUS="Available"
                    )
                )
        db.add_all(schedules)
        logger.success(f"✅ {len(schedules)} doctor schedules seeded.")

        # ─── D. Seed Patients (50 Patients — Indore addresses) ────────────────
        logger.info("Seeding 50 patient profiles (Indore, MP)...")
        patients = []
        for i in range(1, 51):
            gender = random.choice(["Male", "Female"])
            first_name = random.choice(MALE_FIRST_NAMES if gender == "Male" else FEMALE_FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            p_name = f"{first_name} {last_name}"
            phone = f"+91 99887 {i:05d}"
            email = f"{first_name.lower()}.{last_name.lower()}{i}@gmail.com"
            age = random.randint(5, 82)
            locality = random.choice(INDORE_LOCALITIES)
            address = f"{random.randint(1, 200)}, {locality}, Indore, Madhya Pradesh"
            
            patients.append(
                Patient(
                    NAME=p_name, AGE=age, GENDER=gender,
                    PHONE=phone, EMAIL=email, ADDRESS=address
                )
            )
        db.add_all(patients)
        db.commit()
        logger.success(f"✅ {len(patients)} patients seeded.")

        # ─── E. Seed Appointments (100 Appointments) ──────────────────────────
        logger.info("Seeding 100 patient appointments...")
        appointments = []
        time_slots = ["09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM",
                      "12:00 PM", "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM", "05:00 PM"]
        today = datetime.date.today()
        used_slots = set()
        
        # Exclude emergency doctors from appointments (they don't take OPD appointments)
        appointable_doctors = [d for d in doctors if d.department and d.department.NAME != "Emergency Medicine"]
        
        for i in range(1, 101):
            patient = random.choice(patients)
            doctor = random.choice(appointable_doctors)
            day_offset = random.randint(-15, 10)
            appt_date = today + datetime.timedelta(days=day_offset)
            time_slot = random.choice(time_slots)
            
            slot_key = (doctor.NAME, time_slot, str(appt_date))
            if slot_key in used_slots:
                continue
            used_slots.add(slot_key)
            
            status = "Confirmed" if day_offset >= -2 else "Completed"
            if day_offset < 0 and random.random() < 0.1:
                status = "Cancelled"
                
            appointments.append(
                Appointment(
                    PATIENT_NAME=patient.NAME,
                    DOCTOR_NAME=doctor.NAME,
                    APPOINTMENT_TIME=time_slot,
                    APPOINTMENT_DATE=appt_date,
                    PATIENT_ID=patient.ID,
                    DOCTOR_ID=doctor.ID,
                    STATUS=status
                )
            )
        db.add_all(appointments)
        logger.success(f"✅ {len(appointments)} appointments seeded.")

        # ─── F. Seed Billing Catalog (35 Items) ──────────────────────────────
        logger.info("Seeding billing catalog (35 items)...")
        billing_items = [
            # ── Consultations ──
            BillingCatalog(ITEM_NAME="General Physician Consultation",      CATEGORY="Consultation",    PRICE=500,    CODE="BILL_GEN_CONS"),
            BillingCatalog(ITEM_NAME="Specialist Doctor Consultation",      CATEGORY="Consultation",    PRICE=800,    CODE="BILL_SPEC_CONS"),
            BillingCatalog(ITEM_NAME="Super-Specialist Doctor Consultation",CATEGORY="Consultation",    PRICE=1200,   CODE="BILL_SUP_CONS"),
            BillingCatalog(ITEM_NAME="Emergency Consultation",             CATEGORY="Consultation",    PRICE=500,    CODE="BILL_ER_CONS"),
            
            # ── Wards (aligned with KB ipd_wards.md) ──
            BillingCatalog(ITEM_NAME="General Ward Bed Charge (per day)",   CATEGORY="Ward",            PRICE=1500,   CODE="BILL_GEN_BED"),
            BillingCatalog(ITEM_NAME="Semi-Private Room Charge (per day)",  CATEGORY="Ward",            PRICE=3000,   CODE="BILL_SEMI_BED"),
            BillingCatalog(ITEM_NAME="Private AC Room Charge (per day)",    CATEGORY="Ward",            PRICE=5000,   CODE="BILL_PVT_BED"),
            BillingCatalog(ITEM_NAME="Deluxe Room Charge (per day)",        CATEGORY="Ward",            PRICE=7500,   CODE="BILL_DEL_BED"),
            BillingCatalog(ITEM_NAME="Super Deluxe Suite Charge (per day)", CATEGORY="Ward",            PRICE=12000,  CODE="BILL_SUITE_BED"),
            BillingCatalog(ITEM_NAME="ICU Bed Charge (per day)",            CATEGORY="Ward",            PRICE=8000,   CODE="BILL_ICU_BED"),
            BillingCatalog(ITEM_NAME="NICU Bed Charge (per day)",           CATEGORY="Ward",            PRICE=10000,  CODE="BILL_NICU_BED"),
            BillingCatalog(ITEM_NAME="CCU Bed Charge (per day)",            CATEGORY="Ward",            PRICE=8000,   CODE="BILL_CCU_BED"),
            
            # ── Lab Tests ──
            BillingCatalog(ITEM_NAME="Complete Blood Count (CBC)",          CATEGORY="Lab Test",        PRICE=350,    CODE="BILL_CBC_TEST"),
            BillingCatalog(ITEM_NAME="Thyroid Profile (T3, T4, TSH)",       CATEGORY="Lab Test",        PRICE=750,    CODE="BILL_THY_TEST"),
            BillingCatalog(ITEM_NAME="Lipid Profile (Cholesterol)",         CATEGORY="Lab Test",        PRICE=650,    CODE="BILL_LIP_TEST"),
            BillingCatalog(ITEM_NAME="HbA1c Blood Glucose Test",            CATEGORY="Lab Test",        PRICE=450,    CODE="BILL_GLU_TEST"),
            BillingCatalog(ITEM_NAME="Liver Function Test (LFT)",           CATEGORY="Lab Test",        PRICE=900,    CODE="BILL_LFT_TEST"),
            BillingCatalog(ITEM_NAME="Kidney Function Test (KFT)",          CATEGORY="Lab Test",        PRICE=850,    CODE="BILL_KFT_TEST"),
            BillingCatalog(ITEM_NAME="Serum Vitamin D",                     CATEGORY="Lab Test",        PRICE=600,    CODE="BILL_VITD_TEST"),
            
            # ── Radiology ──
            BillingCatalog(ITEM_NAME="Chest X-Ray Digital",                 CATEGORY="Radiology",       PRICE=600,    CODE="BILL_XRAY_CHEST"),
            BillingCatalog(ITEM_NAME="Ultrasound (USG) Abdomen",            CATEGORY="Radiology",       PRICE=1200,   CODE="BILL_USG_ABD"),
            BillingCatalog(ITEM_NAME="CT Scan Head/Brain",                  CATEGORY="Radiology",       PRICE=3500,   CODE="BILL_CT_HEAD"),
            BillingCatalog(ITEM_NAME="MRI Brain",                           CATEGORY="Radiology",       PRICE=6000,   CODE="BILL_MRI_BRAIN"),
            BillingCatalog(ITEM_NAME="MRI Spine Lumbar",                    CATEGORY="Radiology",       PRICE=6000,   CODE="BILL_MRI_LUM"),
            BillingCatalog(ITEM_NAME="2D Echocardiography",                 CATEGORY="Radiology",       PRICE=1800,   CODE="BILL_ECHO"),
            BillingCatalog(ITEM_NAME="Color Doppler Ultrasound",            CATEGORY="Radiology",       PRICE=2000,   CODE="BILL_DOPPLER"),
            
            # ── Surgery Packages ──
            BillingCatalog(ITEM_NAME="Appendectomy (Laparoscopic)",         CATEGORY="Surgery",         PRICE=45000,  CODE="BILL_SURG_APPY"),
            BillingCatalog(ITEM_NAME="Cholecystectomy (Laparoscopic)",      CATEGORY="Surgery",         PRICE=55000,  CODE="BILL_SURG_CHOLE"),
            BillingCatalog(ITEM_NAME="Hernia Repair (Laparoscopic)",        CATEGORY="Surgery",         PRICE=50000,  CODE="BILL_SURG_HERNIA"),
            BillingCatalog(ITEM_NAME="Caesarean Section (LSCS)",            CATEGORY="Surgery",         PRICE=65000,  CODE="BILL_SURG_LSCS"),
            BillingCatalog(ITEM_NAME="Total Knee Replacement (Unilateral)", CATEGORY="Surgery",         PRICE=250000, CODE="BILL_SURG_TKR"),
            BillingCatalog(ITEM_NAME="Cataract Surgery (Phaco + IOL)",      CATEGORY="Surgery",         PRICE=25000,  CODE="BILL_SURG_CATA"),
            
            # ── Health Check-Up Packages ──
            BillingCatalog(ITEM_NAME="Silver Health Check-Up Package",      CATEGORY="Health Package",  PRICE=2999,   CODE="BILL_PKG_SILVER"),
            BillingCatalog(ITEM_NAME="Gold Health Check-Up Package",        CATEGORY="Health Package",  PRICE=5999,   CODE="BILL_PKG_GOLD"),
            BillingCatalog(ITEM_NAME="Platinum Health Check-Up Package",    CATEGORY="Health Package",  PRICE=11999,  CODE="BILL_PKG_PLAT"),
            
            # ── Emergency & Nursing ──
            BillingCatalog(ITEM_NAME="Emergency Room Admission Charge",     CATEGORY="Emergency",       PRICE=1500,   CODE="BILL_ER_ADM"),
            BillingCatalog(ITEM_NAME="General Ward Nursing Charges (per day)", CATEGORY="Nursing",      PRICE=500,    CODE="BILL_NURS_GEN"),
            BillingCatalog(ITEM_NAME="Private/Deluxe Nursing Charges (per day)", CATEGORY="Nursing",    PRICE=1000,   CODE="BILL_NURS_PVT"),
            BillingCatalog(ITEM_NAME="ICU/CCU Nursing Charges (per day)",   CATEGORY="Nursing",         PRICE=2000,   CODE="BILL_NURS_ICU"),
        ]
        db.add_all(billing_items)
        logger.success(f"✅ {len(billing_items)} billing catalog items seeded.")

        # ─── G. Seed Insurance Providers (6 Providers) ────────────────────────
        logger.info("Seeding 6 insurance partner records...")
        insurances = [
            InsuranceProvider(NAME="Star Health & Allied Insurance",   CASHLESS_AVAILABLE=True,  HELPLINE="1800-425-2255"),
            InsuranceProvider(NAME="HDFC ERGO General Insurance",      CASHLESS_AVAILABLE=True,  HELPLINE="1800-2700-700"),
            InsuranceProvider(NAME="Niva Bupa Health Insurance",       CASHLESS_AVAILABLE=True,  HELPLINE="1800-309-7575"),
            InsuranceProvider(NAME="Care Health Insurance",            CASHLESS_AVAILABLE=True,  HELPLINE="1800-102-4488"),
            InsuranceProvider(NAME="ICICI Lombard General Insurance",  CASHLESS_AVAILABLE=False, HELPLINE="1800-2666"),
            InsuranceProvider(NAME="Bajaj Allianz Health Insurance",   CASHLESS_AVAILABLE=False, HELPLINE="1800-209-0144"),
        ]
        db.add_all(insurances)
        logger.success(f"✅ {len(insurances)} insurance providers seeded.")

        # ─── H. Seed Ward Management (8 Wards — prices match KB) ─────────────
        logger.info("Seeding 8 ward configurations (prices aligned with KB)...")
        wards = [
            WardManagement(WARD_TYPE="General Ward",         TOTAL_BEDS=80,  OCCUPIED_BEDS=52,  PRICE_PER_DAY=1500),
            WardManagement(WARD_TYPE="Semi-Private Room",    TOTAL_BEDS=40,  OCCUPIED_BEDS=24,  PRICE_PER_DAY=3000),
            WardManagement(WARD_TYPE="Private AC Room",      TOTAL_BEDS=30,  OCCUPIED_BEDS=18,  PRICE_PER_DAY=5000),
            WardManagement(WARD_TYPE="Deluxe Room",          TOTAL_BEDS=20,  OCCUPIED_BEDS=10,  PRICE_PER_DAY=7500),
            WardManagement(WARD_TYPE="Super Deluxe Suite",   TOTAL_BEDS=5,   OCCUPIED_BEDS=2,   PRICE_PER_DAY=12000),
            WardManagement(WARD_TYPE="ICU",                  TOTAL_BEDS=20,  OCCUPIED_BEDS=12,  PRICE_PER_DAY=8000),
            WardManagement(WARD_TYPE="NICU",                 TOTAL_BEDS=10,  OCCUPIED_BEDS=5,   PRICE_PER_DAY=10000),
            WardManagement(WARD_TYPE="CCU",                  TOTAL_BEDS=10,  OCCUPIED_BEDS=6,   PRICE_PER_DAY=8000),
        ]
        db.add_all(wards)
        total_beds = sum(w.TOTAL_BEDS for w in wards)
        logger.success(f"✅ {len(wards)} wards seeded ({total_beds} total beds).")

        # ─── I. Seed Lab Reports (80 Lab Reports) ────────────────────────────
        logger.info("Generating 80 patient lab reports...")
        reports = []
        for i in range(1, 81):
            patient = random.choice(patients)
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
                
            reports.append(
                LabReport(
                    PATIENT_ID=patient.ID,
                    TEST_NAME=test_name,
                    RESULT=result,
                    STATUS=status,
                    ORDERED_DATE=ordered_date
                )
            )
        db.add_all(reports)
        logger.success(f"✅ {len(reports)} lab reports seeded.")

        # ─── J. Seed System Audit Log ────────────────────────────────────────
        logger.info("Recording system initialization event...")
        audit = AuditLog(
            ACTION_TYPE="SYSTEM_INITIALIZATION",
            USER_ID="system_admin",
            ACTION_DETAILS=(
                f"Lifeline Multi-Speciality Hospital database initialized. "
                f"Seeded {len(departments)} departments, {len(doctors)} doctors, "
                f"{len(schedules)} schedules, {len(patients)} patients, "
                f"{len(appointments)} appointments, {len(billing_items)} billing items, "
                f"{len(insurances)} insurance providers, {len(wards)} wards ({total_beds} beds), "
                f"and {len(reports)} lab reports."
            )
        )
        db.add(audit)

        db.commit()
        logger.success("═══════════════════════════════════════════════════════════")
        logger.success("🏥 LIFELINE HOSPITAL DATABASE SEEDED SUCCESSFULLY!")
        logger.success(f"   Departments: {len(departments)} | Doctors: {len(doctors)}")
        logger.success(f"   Schedules: {len(schedules)} | Patients: {len(patients)}")
        logger.success(f"   Appointments: {len(appointments)} | Billing Items: {len(billing_items)}")
        logger.success(f"   Insurance: {len(insurances)} | Wards: {len(wards)} ({total_beds} beds)")
        logger.success(f"   Lab Reports: {len(reports)}")
        logger.success("═══════════════════════════════════════════════════════════")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during database seeding: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
