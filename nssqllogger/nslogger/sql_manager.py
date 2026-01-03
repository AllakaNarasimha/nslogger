import sqlite3
import pandas as pd
from datetime import datetime, timezone
from .sql_script import CREATE_INDIAVIX_DATA_TABLE, CREATE_METADATA_TABLE, CREATE_OPTION_CHAINS_TABLE, CREATE_EXPIRY_DATES_TABLE, CREATE_HISTORICAL_DATA_TABLE, CREATE_LIVE_DATA_TABLE

class SQLManager:
    def __init__(self, skip_db_creation=False, db_path="ticks.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        if not skip_db_creation:
            self._create_tables()

    def _create_tables(self):        
        table_creates = [
            # CREATE_STOCK_TICKS_TABLE,
            # CREATE_INDEX_TICKS_TABLE,
            # CREATE_DATA_DEPTH_TICKS_TABLE,
            # CREATE_BFO_TABLE,
            # CREATE_NFO_TABLE,
            # CREATE_INSTRUMENT_TABLE,
            # CREATE_TICK_DATA_TABLE,
            CREATE_EXPIRY_DATES_TABLE,
            CREATE_INDIAVIX_DATA_TABLE,
            CREATE_METADATA_TABLE,
            CREATE_OPTION_CHAINS_TABLE,
            CREATE_HISTORICAL_DATA_TABLE,
            CREATE_LIVE_DATA_TABLE,
        ]
        self.create_tables(table_creates)

    def create_tables(self, tables):
        for create_sql in tables:
            self.cursor.execute(create_sql)
        self.conn.commit()    
    
    def insert_data(self, index_tick: dict, table='stock_ticks', exclude_columns=None):
        if exclude_columns is None:
            exclude_columns = {'created_at'}
        # Get current time in UTC
        index_tick['created_at'] = datetime.now(timezone.utc).isoformat()
        filtered_items = {k: v for k, v in index_tick.items() if k not in exclude_columns}
        columns = ','.join(filtered_items.keys())
        placeholders = ','.join(['?'] * len(filtered_items))
        sql = f'INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})'
        self.cursor.execute(sql, tuple(filtered_items.values()))
        self.conn.commit()
    
    def insert_live_data(self, data, table='live_data'):
        """Insert live data (OHLCV) into the live_data table.
        
        Args:
            data: Can be a dict, list of dicts, or pandas DataFrame
            table: Target table name (default: 'live_data')
        """
        try:
            # Convert to DataFrame if it's a dict or list of dicts
            if isinstance(data, dict):
                df = pd.DataFrame([data])
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, pd.DataFrame):
                df = data
            else:
                print(f"Unsupported data type: {type(data)}")
                return
            
            if df.empty:
                print("No data to insert")
                return
            
            cols = [col for col in df.columns if col != 'id']
            columns = ','.join(cols)
            placeholders = ','.join(['?'] * len(cols))
            sql = f'INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})'
            
            before_count = self._get_row_count(table)
            # Use executemany for bulk insert to avoid recursive cursor errors
            rows = [tuple(row) for row in df[cols].itertuples(index=False, name=None)]
            try:
                before_count = self._get_row_count(table)
                self.cursor.executemany(sql, rows)
                self.conn.commit()
                after_count = self._get_row_count(table)
                inserted_count = after_count - before_count
                print(f"Successfully inserted {inserted_count} records into {table} (Total: {after_count})")
            except Exception as e:
                print(f"Error inserting rows into {table}: {e}")
                self.conn.rollback()
            
        except Exception as e:
            print(f"Error in insert_live_data: {e}")
            raise

    def get_data(self, symbol=None, table='stock_ticks'):
        if symbol:
            return self.cursor.execute(f"SELECT * FROM {table} WHERE symbol=?", (symbol,)).fetchall()
        return self.cursor.execute(f"SELECT * FROM {table}").fetchall()
    
    def get_data(self, query, params=(), one_or_all='all'):
        if one_or_all == 'one':
            return self.cursor.execute(query, params).fetchone()
        return self.cursor.execute(query, params).fetchall()
    
    def _get_row_count(self, table: str) -> int:        
        try:
            count = self.cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            return count
        except Exception as e:
            print(f"Could not get count for {table}: {e}")
            return -1