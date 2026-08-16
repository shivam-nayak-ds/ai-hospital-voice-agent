import sys
import asyncio
from sqlalchemy import text
from src.db.session import engine
from src.utils.logger import custom_logger as logger

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def check_database_integrity():
    logger.info("=========================================")
    logger.info("🏥 ASHA DATABASE INTEGRITY CHECKER")
    logger.info("=========================================")
    
    try:
        async with engine.connect() as conn:
            # 1. Check basic connection
            logger.info("🔗 Testing PostgreSQL connection pool...")
            result = await conn.execute(text("SELECT 1"))
            if result.scalar() == 1:
                logger.success("✅ Database connection verified successfully.")
            
            # 2. Check and print statistics from each table
            tables = [
                ("DEPARTMENTS", "Departments"),
                ("DOCTORS", "Doctors"),
                ("DOCTOR_SCHEDULES", "Schedules"),
                ("PATIENTS", "Patients"),
                ("APPOINTMENTS", "Appointments"),
                ("BILLING_CATALOG", "Billing Catalog items"),
                ("INSURANCE_PROVIDERS", "Insurance Providers"),
                ("WARD_MANAGEMENT", "Wards"),
                ("LAB_REPORTS", "Lab Reports"),
                ("AUDIT_LOGS", "Audit Logs")
            ]
            
            logger.info("\n📊 DATABASE STATISTICS:")
            logger.info("-----------------------------------------")
            
            all_tables_exist = True
            for table_name, display_name in tables:
                try:
                    res = await conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                    count = res.scalar()
                    logger.info(f"👉 {display_name:<25}: {count} records")
                except Exception as table_err:
                    logger.error(f"❌ {display_name:<25}: Table is missing or inaccessible! ({table_err})")
                    all_tables_exist = False
            
            logger.info("-----------------------------------------")
            if all_tables_exist:
                logger.success("🎉 DATABASE INTEGRITY VERIFIED! Schema is 100% complete and healthy.")
                return True
            else:
                logger.warning("⚠️ Schema incomplete. Run 'scripts/db_seed.py' to recreate and seed tables.")
                return False
                
    except Exception as e:
        logger.critical(f"🚨 DATABASE CONNECTION FAILED: {e}")
        logger.critical("👉 Make sure your PostgreSQL server is running and .env credentials are correct.")
        return False

if __name__ == "__main__":
    success = asyncio.run(check_database_integrity())
    sys.exit(0 if success else 1)
