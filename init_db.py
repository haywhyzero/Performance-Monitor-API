import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables from .env file for local execution
load_dotenv()

# Add the project root to the Python path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_monitor_api import DatabaseManager, Config, logger

def initialize_database():
    """
    Connects to the database and initializes tables and indexes.
    This is intended to be run as a one-time setup task.
    """
    if not Config.DATABASE_URL:
        logger.critical("DATABASE_URL environment variable not set. Cannot initialize database.")
        sys.exit(1)
    
    logger.info("Starting database initialization...")
    db_manager = DatabaseManager(db_url=Config.DATABASE_URL, initialize=True)
    logger.info("Database initialization script finished.")

if __name__ == "__main__":
    initialize_database()