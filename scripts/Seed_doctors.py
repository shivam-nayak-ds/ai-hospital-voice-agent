import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
load_dotenv()

def seed_database():
    connection = None
    try:
        connection = mysql.connector.connect(
            host = "localhost",
            user = "root",
            password = os.getenv("DB_PASSWORD"), 
            database = "Ai_hospital_agent"
        )

        if connection.is_connected():
            cursor = connection.cursor()

            # Purani table delete karna zaroori hai naya column add karne ke liye
            cursor.execute("DROP TABLE IF EXISTS DOCTORS;")
            
            # 1. Create DOCTORS Table with STATUS
            create_doctors_query = """
            CREATE TABLE DOCTORS (
                ID INT AUTO_INCREMENT PRIMARY KEY,
                NAME VARCHAR(255),
                SPECIALIZATION VARCHAR(255),
                GENDER VARCHAR(50),
                DEPARTMENT VARCHAR(255),
                CONSULTATION_FEE INT,
                AVAILABLE_SLOTS TEXT,
                STATUS VARCHAR(50) DEFAULT 'Available'
            );
            """
            cursor.execute(create_doctors_query)
            print("Table 'DOCTORS' is ready with STATUS column.")

            # 2. Create APPOINTMENTS Table
            create_appointments_query = """
            CREATE TABLE IF NOT EXISTS APPOINTMENTS (
                ID INT AUTO_INCREMENT PRIMARY KEY,
                PATIENT_NAME VARCHAR(255),
                DOCTOR_NAME VARCHAR(255),
                APPOINTMENT_TIME VARCHAR(100),
                BOOKING_DATE TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cursor.execute(create_appointments_query)
            print("Table 'APPOINTMENTS' is ready.")

            # 3. Data with STATUS
            doctors_data = [
                ('Dr. Sanjay Gupta', 'Cardiologist', 'Male', 'Heart', 1000, '10 AM - 6 PM', 'Available'),
                ('Dr. Priya Sharma', 'Pediatrician', 'Female', 'Children', 800, '9 AM - 5 PM', 'Away'),
                ('Dr. Amit Verma', 'General Physician', 'Male', 'General', 600, '10 AM - 8 PM', 'Available'),
                ('Dr. Neha Singh', 'Gynecologist', 'Female', 'Womens', 900, '11 AM - 7 PM', 'Holiday'),
                ('Dr. Rahul Mishra', 'Orthopedic', 'Male', 'Bones', 1200, '10 AM - 4 PM', 'Available'),
                ('Dr. Sneha Joshi', 'Dermatologist', 'Female', 'Skin', 700, '10 AM - 6 PM', 'Available'),
                ('Dr. Vikas Khanna', 'Neurologist', 'Male', 'Brain', 1500, '11 AM - 5 PM', 'Away'),
                ('Dr. Anjali Gupta', 'ENT Specialist', 'Female', 'ENT', 800, '10 AM - 6 PM', 'Available'),
                ('Dr. Rajesh Kumar', 'Ophthalmologist', 'Male', 'Eye', 700, '10 AM - 7 PM', 'Holiday'),
                ('Dr. Meera Iyer', 'Diabetologist', 'Female', 'Diabetes', 800, '9 AM - 5 PM', 'Available')
            ]

            sql_query = """INSERT INTO DOCTORS (NAME, SPECIALIZATION, GENDER, DEPARTMENT, CONSULTATION_FEE, AVAILABLE_SLOTS, STATUS) 
                           VALUES (%s, %s, %s, %s, %s, %s, %s)"""

            cursor.executemany(sql_query, doctors_data)
            connection.commit()
            print(f"Success: {cursor.rowcount} doctors added successfully!")

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")

    finally:
        if connection is not None and connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed")

if __name__ == "__main__":
    seed_database()
