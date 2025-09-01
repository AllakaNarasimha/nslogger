import os
from datetime import datetime
import sqlite3

from nslogger.sql_script import CREATE_TICK_DATA_TABLE, CREATE_INSTRUMENT_TABLE, CREATE_NFO_TABLE, CREATE_BFO_TABLE  
from nslogger.sql_manager import SQLManager

class HistoryDataManager:    
    def __init__(self, db_path="history_data.db"):        
        #self.create_db_file(db_file)
        self.sql = SQLManager(True, db_path)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()
    
    def _create_tables(self):
        table_scripts = [
            CREATE_BFO_TABLE,
            CREATE_NFO_TABLE,
            CREATE_INSTRUMENT_TABLE,
            CREATE_TICK_DATA_TABLE,
        ]
        self.sql.create_tables(table_scripts)

    def create_db_file(self, db_file):
        now = datetime.now()
        month_year = now.strftime("%d%b%Y").lower()  # e.g., 'sep2025'
        dir_path = os.path.join(os.getcwd(), month_year)
        os.makedirs(dir_path, exist_ok=True)
        today_str = now.strftime("%d%b%y").lower()
        self.db_file = os.path.join(dir_path, f"{today_str}_{db_file}")

    def insert_df_to_table(self, df, table='bfo_data'):
        # Remove 'id' column if present
        cols = [col for col in df.columns if col != 'id']
        columns = ','.join(cols)
        placeholders = ','.join(['?'] * len(cols))
        sql = f'INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})'
        for row in df[cols].itertuples(index=False, name=None):
            try:
                    self.sql.cursor.execute(sql, row)
            except Exception as e:
                print(f"Error inserting row {row}: {e}")
        self.sql.conn.commit()
    # end def
    