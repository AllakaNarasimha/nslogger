import os
from datetime import datetime

class DBUtil:
    @staticmethod
    def create_db_file(db_file, db_path=None):        
        if db_path:
            # Use provided full path to load existing DB
            return db_path
        else:
            # Create new DB with auto-generated path
            now = datetime.now()
            month_year = now.strftime("%b%Y").lower()  # e.g., 'jan2026'
            dir_path = os.path.join(os.getcwd(), month_year)
            os.makedirs(dir_path, exist_ok=True)
            today_str = now.strftime("%d%b%y").lower()  # e.g., '03jan26'
            return os.path.join(dir_path, f"{today_str}_{db_file}")
