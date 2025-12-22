import os
from datetime import datetime
from .sql_manager import SQLManager

class TickManager:    
    def __init__(self, table='stock_ticks', db_file="ticks.db"):    
        self.table = table    
        self.create_db_file(db_file)
        self.sql = SQLManager(False, self.db_file)

    def create_db_file(self, db_file):
        now = datetime.now()
        month_year = now.strftime("%b%Y").lower()  # e.g., 'sep2025'
        dir_path = os.path.join(os.getcwd(), month_year)
        os.makedirs(dir_path, exist_ok=True)
        today_str = now.strftime("%d%b%y").lower()
        self.db_file = os.path.join(dir_path, f"{today_str}_{db_file}")

    def log_tick(self, tick: dict):
        self.sql.insert_data(tick, self.table)

    def get_all_ticks(self):
        return self.sql.get_data(self.table)

    def get_ticks_by_symbol(self, symbol):
        return self.sql.get_data(symbol, self.table)