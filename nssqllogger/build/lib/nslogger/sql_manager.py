import sqlite3
from datetime import datetime
from sql_script import CREATE_INDIAVIXDATA_TABLE, CREATE_METADATA_TABLE, CREATE_OPTIONCHAINS_TABLE, CREATE_DATA_DEPTH_TICKS_TABLE, CREATE_EXPIRY_DATES_TABLE, CREATE_STOCK_TICKS_TABLE, CREATE_INDEX_TICKS_TABLE

class SQLManager:
    def __init__(self, skip_db_creation=False, db_path="ticks.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        if not skip_db_creation:
            self._create_tables()

    def _create_tables(self):
        table_creates = [
            CREATE_STOCK_TICKS_TABLE,
            CREATE_INDEX_TICKS_TABLE,
            CREATE_DATA_DEPTH_TICKS_TABLE,
            CREATE_EXPIRY_DATES_TABLE,
            CREATE_INDIAVIXDATA_TABLE,
            CREATE_METADATA_TABLE,
            CREATE_OPTIONCHAINS_TABLE,
        ]
        self.create_tables(table_creates)

    def create_tables(self, tables):
        for create_sql in tables:
            self.cursor.execute(create_sql)
        self.conn.commit()    
    
    def insert_data(self, index_tick: dict, table='stock_ticks'):
        index_tick['created_at'] = datetime.now().isoformat()
        columns = ','.join(index_tick.keys())
        placeholders = ','.join(['?'] * len(index_tick))
        sql = f'INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})'
        self.cursor.execute(sql, tuple(index_tick.values()))
        self.conn.commit()

    def get_data(self, symbol=None, table='stock_ticks'):
        if symbol:
            return self.cursor.execute(f"SELECT * FROM {table} WHERE symbol=?", (symbol,)).fetchall()
        return self.cursor.execute(f"SELECT * FROM {table}").fetchall()
    
    def get_data(self, query, params=(), one_or_all='all'):
        if one_or_all == 'one':
            return self.cursor.execute(query, params).fetchone()
        return self.cursor.execute(query, params).fetchall()
