import mysql.connector
import os
from dotenv import load_dotenv
from src.utils.logger import custom_logger as logger

def upgrade_database():
    load_dotenv()
    
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password=os.getenv("DB_PASSWORD"),
            database="Ai_hospital_agent"
        )
        cursor = connection.cursor()

        logger.info("Starting Database Upgrade for Multi-Agent Architecture...")

        # 1. Add missing APPOINTMENT_DATE column to APPOINTMENTS if it doesn't exist
        try:
            cursor.execute("ALTER TABLE APPOINTMENTS ADD COLUMN APPOINTMENT_DATE DATE")
            # Update existing rows to have today's date
            cursor.execute("UPDATE APPOINTMENTS SET APPOINTMENT_DATE = CURRENT_DATE WHERE APPOINTMENT_DATE IS NULL")
            logger.success("Added APPOINTMENT_DATE column to APPOINTMENTS table.")
        except mysql.connector.Error as err:
            if err.errno == 1060: # Duplicate column name
                logger.info("APPOINTMENT_DATE column already exists.")
            else:
                logger.error(f"Error altering APPOINTMENTS: {err}")

        # 2. Create PHARMACY_INVENTORY Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS PHARMACY_INVENTORY (
            ID INT AUTO_INCREMENT PRIMARY KEY,
            MEDICINE_NAME VARCHAR(255) NOT NULL,
            CATEGORY VARCHAR(100),
            PRICE DECIMAL(10, 2),
            STOCK_QUANTITY INT,
            LAST_RESTOCKED TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """)
        logger.success("PHARMACY_INVENTORY table created.")

        # 3. Create BILLING_CATALOG Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS BILLING_CATALOG (
            ID INT AUTO_INCREMENT PRIMARY KEY,
            SERVICE_NAME VARCHAR(255) NOT NULL,
            DEPARTMENT VARCHAR(100),
            COST DECIMAL(10, 2),
            IS_COVERED_BY_INSURANCE BOOLEAN DEFAULT TRUE
        )
        """)
        logger.success("BILLING_CATALOG table created.")

        # 4. Insert Dummy Data into Pharmacy
        pharmacy_data = [
            ("Paracetamol 500mg", "General", 25.00, 500),
            ("Azithromycin 250mg", "Antibiotic", 120.00, 150),
            ("Cough Syrup (Benadryl)", "General", 85.00, 45),
            ("Insulin Glargine", "Diabetic", 450.00, 20),
            ("Vitamin C Supplements", "Vitamins", 150.00, 200)
        ]
        
        cursor.execute("SELECT COUNT(*) FROM PHARMACY_INVENTORY")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO PHARMACY_INVENTORY (MEDICINE_NAME, CATEGORY, PRICE, STOCK_QUANTITY) VALUES (%s, %s, %s, %s)",
                pharmacy_data
            )
            logger.success("Inserted dummy data into PHARMACY_INVENTORY.")

        # 5. Insert Dummy Data into Billing
        billing_data = [
            ("MRI Scan (Brain)", "Radiology", 4500.00, True),
            ("X-Ray (Chest)", "Radiology", 800.00, True),
            ("Complete Blood Count (CBC)", "Pathology", 400.00, True),
            ("Lipid Profile", "Pathology", 750.00, True),
            ("ICU Bed Charges (Per Day)", "IPD", 6000.00, True),
            ("Private Suite (Per Day)", "IPD", 12000.00, False)
        ]
        
        cursor.execute("SELECT COUNT(*) FROM BILLING_CATALOG")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO BILLING_CATALOG (SERVICE_NAME, DEPARTMENT, COST, IS_COVERED_BY_INSURANCE) VALUES (%s, %s, %s, %s)",
                billing_data
            )
            logger.success("Inserted dummy data into BILLING_CATALOG.")

        # 6. Create DEPARTMENTS Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS DEPARTMENTS (
            ID INT AUTO_INCREMENT PRIMARY KEY,
            NAME VARCHAR(100) NOT NULL UNIQUE,
            FLOOR INT,
            HEAD_OF_DEPT VARCHAR(255),
            CONTACT_EXT VARCHAR(10)
        )
        """)
        logger.success("DEPARTMENTS table created.")

        # 7. Create INSURANCE_PROVIDERS Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS INSURANCE_PROVIDERS (
            ID INT AUTO_INCREMENT PRIMARY KEY,
            NAME VARCHAR(100) NOT NULL UNIQUE,
            CASHLESS_AVAILABLE BOOLEAN DEFAULT TRUE,
            CONTACT_PERSON VARCHAR(100),
            HELPLINE VARCHAR(20)
        )
        """)
        logger.success("INSURANCE_PROVIDERS table created.")

        # 8. Create AUDIT_LOGS Table (For Enterprise Monitoring)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS AUDIT_LOGS (
            ID INT AUTO_INCREMENT PRIMARY KEY,
            ACTION_TYPE VARCHAR(50), -- BOOKING, SEARCH, EMERGENCY, BILLING
            USER_ID VARCHAR(255),
            ACTION_DETAILS TEXT,
            TIMESTAMP TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        logger.success("AUDIT_LOGS table created.")

        # 9. Create WARD_MANAGEMENT Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS WARD_MANAGEMENT (
            ID INT AUTO_INCREMENT PRIMARY KEY,
            WARD_TYPE VARCHAR(100), -- ICU, GENERAL, PRIVATE, SEMI-PRIVATE
            TOTAL_BEDS INT,
            OCCUPIED_BEDS INT,
            PRICE_PER_DAY DECIMAL(10, 2)
        )
        """)
        logger.success("WARD_MANAGEMENT table created.")

        # 10. Insert Realistic Seed Data
        dept_data = [
            ("Cardiology", 1, "Dr. Rajesh Sharma", "101"),
            ("Radiology", 0, "Dr. Sunita Verma", "002"),
            ("Pathology", 0, "Dr. Amit Khurana", "005"),
            ("Oncology", 2, "Dr. Vikram Seth", "201"),
            ("Pediatrics", 1, "Dr. Megha Singh", "105")
        ]
        
        cursor.execute("SELECT COUNT(*) FROM DEPARTMENTS")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO DEPARTMENTS (NAME, FLOOR, HEAD_OF_DEPT, CONTACT_EXT) VALUES (%s, %s, %s, %s)",
                dept_data
            )

        insurance_data = [
            ("HDFC Ergo", True, "Rahul Mehta", "1800-2666"),
            ("Star Health", True, "Priya Das", "1800-425-2255"),
            ("Niva Bupa", True, "Sanjay Jha", "1860-500-8888"),
            ("LIC Health", False, "Ramesh Kumar", "022-6827")
        ]
        
        cursor.execute("SELECT COUNT(*) FROM INSURANCE_PROVIDERS")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO INSURANCE_PROVIDERS (NAME, CASHLESS_AVAILABLE, CONTACT_PERSON, HELPLINE) VALUES (%s, %s, %s, %s)",
                insurance_data
            )

        ward_data = [
            ("ICU", 15, 12, 6500.00),
            ("General Ward", 50, 38, 1200.00),
            ("Semi-Private", 20, 15, 3500.00),
            ("Private Suite", 10, 4, 8500.00)
        ]
        
        cursor.execute("SELECT COUNT(*) FROM WARD_MANAGEMENT")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO WARD_MANAGEMENT (WARD_TYPE, TOTAL_BEDS, OCCUPIED_BEDS, PRICE_PER_DAY) VALUES (%s, %s, %s, %s)",
                ward_data
            )

        connection.commit()
        logger.success("🎉 Enterprise Database Expansion Complete!")

    except Exception as e:
        logger.error(f"Database Upgrade Failed: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    upgrade_database()
