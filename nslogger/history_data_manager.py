import os
import pandas as pd
from datetime import datetime
from functools import lru_cache

from .sql_script import CREATE_TICK_DATA_TABLE, CREATE_INSTRUMENT_TABLE, CREATE_NFO_TABLE, CREATE_BFO_TABLE, CREATE_HISTORICAL_DATA_TABLE
from .sql_manager import SQLManager
from .db_util import DBUtil

class HistoryDataManager:    
    def __init__(self, db_file="history.db", db_path=None):
        self.db_file = DBUtil.create_db_file(db_file, db_path)
        skip_db_creation = False
        if os.path.exists(self.db_file):
            skip_db_creation = True
        self.sql = SQLManager(skip_db_creation, self.db_file)        
        self.conn = self.sql.conn
        self.cursor = self.sql.cursor
        
        # Check connection health on initialization
        if not self.sql.check_connection_health():
            print("Connection unhealthy during initialization, refreshing...")
            self.sql.refresh_connection()
        
        self._instrument_cache = {}
        self._tick_cache = {}
        self._expiry_cache = {}
        self._tick_full_cache = {}
        self._option_cache = {}        # Cache option subsets by (symbol, expiry)
        self._agg_cache = {}           # Cache aggregated results
        self._atm_strike_cache = {}    # Cache ATM strike calculations

    def check_connection_health(self):
        """Check if the database connection is healthy."""
        return self.sql.check_connection_health()
    
    def refresh_connection(self):
        """Refresh the database connection for long-running processes."""
        self.sql.refresh_connection() 

    def _create_tables(self):
        table_scripts = [
            CREATE_BFO_TABLE,
            CREATE_NFO_TABLE,
            CREATE_INSTRUMENT_TABLE,
            CREATE_TICK_DATA_TABLE,
            CREATE_HISTORICAL_DATA_TABLE,
        ]
        self.sql.create_tables(table_scripts)    

    def insert_df_to_table(self, df, table='bfo_data'):
        # Check connection health for long-running processes
        if not self.sql.check_connection_health():
            print("Connection unhealthy, refreshing...")
            self.sql.refresh_connection()
        
        # Clear caches when data changes
        self._clear_caches()
        
        # Remove 'id' column if present
        cols = [col for col in df.columns if col != 'id']
        columns = ','.join(cols)
        placeholders = ','.join(['?'] * len(cols))
        sql = f'INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})'
        
        # Use executemany for bulk insert to avoid recursive cursor errors
        rows = [tuple(row) for row in df[cols].itertuples(index=False, name=None)]
        try:
            before_count = self.sql._get_row_count(table)
            self.sql.conn.execute('BEGIN')
            self.sql.cursor.executemany(sql, rows)
            self.sql.conn.commit()
            after_count = self.sql._get_row_count(table)
            inserted_count = after_count - before_count
            print(f"Successfully inserted {inserted_count} records into {table} (Total: {after_count})")
        except Exception as e:
            print(f"Error inserting rows into {table}: {e}")
            try:
                self.sql.conn.rollback()
            except Exception as rollback_error:
                print(f"Error during rollback: {rollback_error}")
    # end def

    def insert_historical_data(self, data, table='historical_data'):
        """Insert historical data (OHLCV) into the historical_data table.
        
        Args:
            data: Can be a dict, list of dicts, or pandas DataFrame
            table: Target table name (default: 'historical_data')
        """
        # Check connection health for long-running processes
        if not self.sql.check_connection_health():
            print("Connection unhealthy, refreshing...")
            self.sql.refresh_connection()
        
        try:
            status_message = ""
                        
            # Clear caches when data changes
            self._clear_caches()
            
            # Convert to DataFrame if it's a dict or list of dicts
            if isinstance(data, dict):
                df = pd.DataFrame([data])
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, pd.DataFrame):
                df = data
            else:
                status_message = f"Unsupported data type: {type(data)}"
                print(status_message)
                return status_message
            
            if df.empty:
                status_message = "No data to insert"
                print(status_message)
                return status_message
            
            # Remove 'id' column if present
            cols = [col for col in df.columns if col != 'id']
            columns = ','.join(cols)
            placeholders = ','.join(['?'] * len(cols))
            sql = f'INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})'
            
            # Use executemany for bulk insert to avoid recursive cursor errors
            rows = [tuple(row) for row in df[cols].itertuples(index=False, name=None)]
            try:
                before_count = self.sql._get_row_count(table)
                self.sql.conn.execute('BEGIN')
                self.sql.cursor.executemany(sql, rows)
                self.sql.conn.commit()
                after_count = self.sql._get_row_count(table)
                inserted_count = after_count - before_count
                message = f"Successfully inserted {inserted_count} records into {table} (Total: {after_count})"                
            except Exception as e:
                message = f"Error inserting rows into {table}: {e}"
                try:
                    self.sql.conn.rollback()
                except Exception as rollback_error:
                    print(f"Error during rollback: {rollback_error}")
            
        except Exception as e:
            message = f"Error in insert_historical_data: {e}"
            
        print(message)
        return message

    def _clear_caches(self):
        """Clear all instance caches when data changes"""
        self._instrument_cache.clear()
        self._tick_cache.clear()
        self._expiry_cache.clear()
        self._tick_full_cache.clear()
        self._option_cache.clear()
        self._agg_cache.clear()
        self._atm_strike_cache.clear()
        # Clear lru_cache decorated methods
        if hasattr(self, '_get_time_range_cached'):
            self._get_time_range_cached.cache_clear()

    def _build_instrument_cache(self, symbol: str):
        query = (
            "select instrument_token, tradingsymbol, name, expiry, strike, lot_size, instrument_type, segment "
            "from instrument_data where tradingsymbol like ?"
        )
        result = self.sql.get_data(query, (symbol + '%',))
        if isinstance(result, pd.DataFrame):
            instrument_df = result
        else:
            columns = [
                'instrument_token', 'tradingsymbol', 'name', 'expiry', 'strike',
                'lot_size', 'instrument_type', 'segment'
            ]
            instrument_df = pd.DataFrame(result, columns=columns)

        # Normalize types where useful
        if not instrument_df.empty:
            # Ensure expiry as datetime where possible (ignore errors) for consistent sorting
            if 'expiry' in instrument_df.columns:
                try:
                    instrument_df['expiry'] = pd.to_datetime(instrument_df['expiry'], errors='ignore')
                except Exception:
                    pass
        future_df = instrument_df[instrument_df['instrument_type'] == 'FUT'] if not instrument_df.empty else instrument_df.head(0)
        option_df = instrument_df[instrument_df['instrument_type'].isin(['CE', 'PE'])] if not instrument_df.empty else instrument_df.head(0)
        expiries = sorted(option_df['expiry'].dropna().unique().tolist()) if not option_df.empty else []
        self._instrument_cache[symbol] = {
            'instrument_df': instrument_df,
            'future_df': future_df,
            'option_df': option_df,
            'expiries': expiries,
        }
        return self._instrument_cache[symbol]

    def get_instrument_info(self, symbol: str):
        """Return the full instrument DataFrame for a symbol (prefix match).

        Uses unified cache that also stores futures, options, and expiries.
        """
        if symbol not in self._instrument_cache:
            self._build_instrument_cache(symbol)
        return self._instrument_cache[symbol]['instrument_df']

    def get_price_info_from_tick_data(self, dt_value, instrument_token):
        """
        Return a pandas DataFrame (0 or 1 row) for a specific timestamp & instrument.
        Caches the full tick_data for each instrument on first access, then filters in-memory.
        """
        # Normalize timestamp
        if isinstance(dt_value, str):
            dt_obj = datetime.strptime(dt_value, '%Y-%m-%d %H:%M:%S')
        else:
            dt_obj = dt_value

        ts_key = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
        cache_key = (ts_key, instrument_token)

        # Fast small cache
        if cache_key in self._tick_cache:
            return self._tick_cache[cache_key]

        # Load full instrument ticks if not cached
        if instrument_token not in self._tick_full_cache:
            query_all = """
                SELECT id, instrument, datetime, price, volume, oi
                FROM tick_data
                WHERE instrument = ?
                ORDER BY datetime
            """
            full_df = self.sql.get_data(query_all, (instrument_token,))
            if not isinstance(full_df, pd.DataFrame):
                columns = ['id', 'instrument', 'datetime', 'price', 'volume', 'oi']
                if isinstance(full_df, tuple):
                    full_df = [full_df]
                full_df = pd.DataFrame(full_df, columns=columns)
            if full_df.empty:
                # Cache empty to avoid repeated DB hits
                self._tick_full_cache[instrument_token] = full_df
            else:
                full_df['datetime'] = pd.to_datetime(full_df['datetime'])
                full_df.set_index('datetime', inplace=True)  # Enable fast datetime lookup
                self._tick_full_cache[instrument_token] = full_df

        full_df = self._tick_full_cache[instrument_token]
        if full_df.empty:
            empty = pd.DataFrame(columns=['id','instrument','datetime','price','volume','oi'])
            self._tick_cache[cache_key] = empty
            return empty

        # Filter in-memory using index for O(1) lookup
        try:
            row_df = full_df.loc[[dt_obj]]
            result_df = row_df.reset_index()
        except KeyError:
            result_df = pd.DataFrame(columns=['datetime','id','instrument','price','volume','oi'])

        self._tick_cache[cache_key] = result_df
        return result_df
    
    def _get_expiries_for_symbol(self, symbol):
        """Return cached expiries list for a symbol, building cache if needed."""
        if symbol not in self._instrument_cache:
            self._build_instrument_cache(symbol)
        return self._instrument_cache[symbol]['expiries']

    @lru_cache(maxsize=128)
    def _get_time_range_cached(self, instrument_token):
        """Cache time range for instrument"""
        query_time_range = """
        SELECT MIN(datetime), MAX(datetime)
        FROM tick_data
        WHERE instrument = ?
        """
        return self.sql.get_data(query_time_range, (instrument_token,), one_or_all='one')

    def get_option_info(self, timestamp, underlying, symbol, segment, atm_strike, expiry_index, strike_count=5):
        if isinstance(timestamp, str):
            timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        
        instrument_df = self.get_instrument_info(symbol)
        # Access unified cache for option_df & expiries
        cache_entry = self._instrument_cache[symbol]
        option_df = cache_entry['option_df']
        if option_df.empty:
            raise ValueError(f"No expiry found for expiry_index {expiry_index}")

        expiries = cache_entry['expiries']
        if len(expiries) <= expiry_index:
            raise ValueError(f"No expiry found for expiry_index {expiry_index}")

        target_expiry = expiries[expiry_index]

        instrument_token_df  = instrument_df[(instrument_df['name'] == underlying) & (instrument_df['segment'] == segment)]
        if instrument_token_df.empty:
            raise ValueError(f"No instrument found for underlying {underlying} and segment {segment}")

        index_token = int(instrument_token_df['instrument_token'].iloc[0])

        underlying_df = self.get_price_info_from_tick_data(timestamp, index_token)
        underlying_price = underlying_df['price'].iloc[0] if not underlying_df.empty else None

        # Ensure we have a valid underlying price before arithmetic
        if underlying_price is None or pd.isna(underlying_price):
            return None
            #raise ValueError(f"No underlying price available for underlying '{underlying}' at {timestamp} (instrument_token={index_token}). Cannot compute ATM strike")

        # Cache ATM strike calculation
        atm_cache_key = (symbol, underlying_price)
        if atm_cache_key in self._atm_strike_cache:
            atm_strike = self._atm_strike_cache[atm_cache_key]
        else:
            try:
                atm_idx = (instrument_df['strike'] - underlying_price).abs().argmin()
                atm_strike = int(instrument_df['strike'].iloc[atm_idx])
                self._atm_strike_cache[atm_cache_key] = atm_strike
            except Exception as e:
                raise ValueError(f"Failed to compute ATM strike: {e}")
        
        # Cache option subset by symbol + expiry using the already filtered option_df
        opt_cache_key = (symbol, str(target_expiry))
        if opt_cache_key not in self._option_cache:
            self._option_cache[opt_cache_key] = option_df[option_df['expiry'] == target_expiry]
        option_subset = self._option_cache[opt_cache_key]
            
        available_strikes = sorted(option_subset['strike'].unique())

        try:
            target_strike_index = available_strikes.index(atm_strike)
        except ValueError:
            raise ValueError(f"Strike {atm_strike} not found for symbol {symbol}, segment {segment}, expiry {target_expiry}")

        # Select strikes within strike_count before and after
        start_index = max(0, target_strike_index - strike_count)
        end_index = min(len(available_strikes), target_strike_index + strike_count + 1)
        strike_range = available_strikes[start_index:end_index]
        
        options = option_subset[
            option_subset['strike'].isin(strike_range)
        ]

        #options.to_csv('options_raw.csv', index=False)

        results = []
        for _, row in options.iterrows():
            instrument_token = int(row['instrument_token'])
            instrument_type = row['instrument_type']

            # Get option price from tick_data using get_price_info_from_tick_data (now cached)
            option_df = self.get_price_info_from_tick_data(timestamp, instrument_token)
            if option_df.empty:
                #print(f"no data for {row['tradingsymbol']} at {timestamp}")
                continue
            option_price = option_df['price'].iloc[0] if not option_df.empty else None
            strike_series = instrument_df['strike']
            strike = float(strike_series.iloc[(strike_series - int(row['strike'])).abs().argmin()])
            # Classify moneyness
            if instrument_type == 'CE':
                if strike < atm_strike:
                    moneyness = 'ITM'
                elif strike > atm_strike:
                    moneyness = 'OTM'
                else:
                    moneyness = 'ATM'
            elif instrument_type == 'PE':
                if strike > atm_strike:
                    moneyness = 'ITM'
                elif strike < atm_strike:
                    moneyness = 'OTM'
                else:
                    moneyness = 'ATM'

            results.append({
                'timestamp': timestamp,
                'instrument_token': instrument_token,
                'tradingsymbol': row['tradingsymbol'],
                'instrument_type': instrument_type,
                'expiry': row['expiry'],
                'strike': strike,
                'lot_size': row['lot_size'],
                'segment': row['segment'],
                'option_price': float(option_price),
                'option_type': moneyness,
                'underlying_price': underlying_price
            })   
        result_df = pd.DataFrame(results)
        #result_df.to_csv('optionchain.csv', index=False)
        return result_df

    def get_future_info(self, symbol: str, segment: str, future_index: int = 0):
        if symbol not in self._instrument_cache:
            self._build_instrument_cache(symbol)
        cache_entry = self._instrument_cache[symbol]
        future_df = cache_entry['future_df']
        if future_df.empty:
            return None
        # Restrict to requested segment if present
        if 'segment' in future_df.columns:
            seg_filtered = future_df[future_df['segment'] == segment]
            if not seg_filtered.empty:
                future_df = seg_filtered
        # Sort by expiry (already datetime or comparable) then pick index
        if 'expiry' in future_df.columns:
            future_df = future_df.sort_values('expiry')
        if future_index < 0 or future_index >= len(future_df):
            return None
        return future_df.iloc[future_index]

    def get_aggregated_tick_data(self, underlying, symbol, segment, start_time = None, end_time = None, interval = 5, unit='seconds', enable_volume: bool = False, fut_index: int = 0):
        instrument_df = self.get_instrument_info(symbol)

        instrument_token_df  = instrument_df[(instrument_df['name'] == underlying) & (instrument_df['segment'] == segment)]
        if instrument_token_df.empty:
            raise ValueError(f"No instrument found for underlying {underlying} and segment {segment}")

        instrument_token = int(instrument_token_df['instrument_token'].iloc[0])

        if start_time is None or end_time is None:
            # Use cached time range
            (min_time, max_time) = self._get_time_range_cached(instrument_token)
            if min_time is None or max_time is None:
                raise ValueError(f"No tick data found for instrument {symbol}")
            
            start_time = datetime.strptime(min_time, '%Y-%m-%d %H:%M:%S') if start_time is None else \
                         datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S') if isinstance(start_time, str) else start_time
            end_time = datetime.strptime(max_time, '%Y-%m-%d %H:%M:%S') if end_time is None else \
                       datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S') if isinstance(end_time, str) else end_time

        # Convert times to datetime if strings
        if isinstance(start_time, str):
            start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        if isinstance(end_time, str):
            end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')             
        
        # Get instrument_token for the symbol (already cached)
        instrument_df = self.get_instrument_info(symbol)
        if instrument_df.empty:
            raise ValueError(f"No instrument found for symbol {symbol}")
        
        instrument_token_df  = instrument_df[(instrument_df['name'] == underlying) & (instrument_df['segment'] == segment)]
        if instrument_token_df.empty:
            raise ValueError(f"No instrument found for underlying {underlying} and segment {segment}")

        instrument_token = int(instrument_token_df['instrument_token'].iloc[0])

        # Cache aggregated results (include enable_volume & fut_index in key because output may differ)
        agg_cache_key = (instrument_token, 
                        start_time.strftime('%Y-%m-%d %H:%M:%S'), 
                        end_time.strftime('%Y-%m-%d %H:%M:%S'), 
                        interval, unit, enable_volume, fut_index)
        if agg_cache_key in self._agg_cache:
            return self._agg_cache[agg_cache_key].copy()

        # Query tick_data for the time range and instrument
        query = f"""
            SELECT * FROM tick_data WHERE instrument = ? AND datetime BETWEEN ? AND ?
        """
        params = (instrument_token, start_time.strftime('%Y-%m-%d %H:%M:%S'), end_time.strftime('%Y-%m-%d %H:%M:%S'))
        res = self.sql.get_data(query, params)
        if isinstance(res, pd.DataFrame):
            df = res
        else:
            columns = ['id', 'instrument', 'datetime', 'price', 'volume', 'oi']
            if isinstance(res, tuple):
                res = [res]
            df = pd.DataFrame(res, columns=columns)
            
        if df.empty:
            return pd.DataFrame(columns=['datetime', 'open', 'high', 'low', 'close', 'volume', 'oi'])

        # Convert datetime to pandas datetime
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        # Set index for resampling
        df.set_index('datetime', inplace=True)
        
        # Define resampling frequency (lowercase 's' to avoid FutureWarning)
        freq = f'{interval}s' if unit == 'seconds' else f'{interval}min'
        
        # Resample and aggregate
        ohlc = df['price'].resample(freq).ohlc()
        volume = df['volume'].resample(freq).sum()
        oi = df['oi'].resample(freq).last()  # Use last oi in the interval
        
        # Combine into a single DataFrame
        result_df = pd.DataFrame({
            'instrument': instrument_token,
            'open': ohlc['open'],
            'high': ohlc['high'],
            'low': ohlc['low'],
            'close': ohlc['close'],
            'volume': volume,
            'oi': oi
        }).reset_index()

        # Optional: replace volume with future contract aggregated volume when enabled
        if enable_volume and fut_index == 0:
            # Try to get the nearest future instrument for this symbol/segment
            fut_row = self.get_future_info(symbol, "NFO-FUT", future_index=fut_index)
            if fut_row is not None:
                fut_token = int(fut_row['instrument_token']) if 'instrument_token' in fut_row else None
                if fut_token is not None:
                    # Load all future ticks in time range
                    fut_query = """
                        SELECT datetime, volume FROM tick_data 
                        WHERE instrument = ? AND datetime BETWEEN ? AND ?
                    """
                    fut_params = (fut_token, start_time.strftime('%Y-%m-%d %H:%M:%S'), end_time.strftime('%Y-%m-%d %H:%M:%S'))
                    fut_res = self.sql.get_data(fut_query, fut_params)
                    if not isinstance(fut_res, pd.DataFrame):
                        fut_cols = ['datetime','volume'] if fut_res and len(fut_res) and isinstance(fut_res[0], tuple) and len(fut_res[0])==2 else ['datetime','volume']
                        if isinstance(fut_res, tuple):
                            fut_res = [fut_res]
                        fut_df = pd.DataFrame(fut_res, columns=fut_cols)
                    else:
                        fut_df = fut_res[['datetime','volume']]
                    if not fut_df.empty:
                        fut_df['datetime'] = pd.to_datetime(fut_df['datetime'])
                        fut_df.set_index('datetime', inplace=True)
                        fut_vol = fut_df['volume'].resample(freq).sum()
                        # Align indexes
                        fut_vol = fut_vol.reindex(result_df['datetime']).fillna(0)
                        # Replace volume column
                        result_df['volume'] = fut_vol.values
                        result_df.rename(columns={'volume': 'volume_fut'}, inplace=True)
                        # Optionally keep original? Could add original as separate col; currently replaced.
        
        # Ensure correct types and fill missing oi with 0
        result_df[['open', 'high', 'low', 'close']] = result_df[['open', 'high', 'low', 'close']].astype(float)
        vol_col = 'volume_fut' if enable_volume and fut_index == 0 and 'volume_fut' in result_df.columns else 'volume'
        result_df[[vol_col, 'oi']] = result_df[[vol_col, 'oi']].astype(float).fillna(0)
        
        # Cache the result
        self._agg_cache[agg_cache_key] = result_df
        
        #result_df.to_csv('aggregated_ticks.csv', index=False)
        return result_df.copy()

    def get_historical_data(self, symbol, start_timestamp=None, end_timestamp=None):        
        try:
            query = "SELECT * FROM historical_data WHERE symbol = ?"
            params = [symbol]
            
            if start_timestamp is not None and end_timestamp is not None:
                query += " AND timestamp BETWEEN ? AND ?"
                params.extend([start_timestamp, end_timestamp])
            
            query += " ORDER BY timestamp"
            
            return pd.read_sql(query, self.conn, params=params) 
        except Exception as e:
            print(f"Error retrieving historical data for {symbol}: {e}")
            return pd.DataFrame()

    def get_historical_data_range(self, symbol, start_timestamp, end_timestamp):
        """Retrieve historical data within a specific timestamp range.
        
        Args:
            symbol: Stock symbol
            start_timestamp: Start timestamp
            end_timestamp: End timestamp
            
        Returns:
            pandas DataFrame with historical data
        """
        return self.get_historical_data(symbol, start_timestamp, end_timestamp)

    def clear_all_caches(self):
        """Public method to clear all caches"""
        self._clear_caches()

if __name__ == "__main__":   
    # Create HistoryDataManager with date-based filename
    hdm = HistoryDataManager("history.db")
    res = hdm.get_option_info('2025-09-05 09:10:00', 'NIFTY 50', "NIFTY", "INDICES", 19500, 0)
    print(res)
    res = hdm.get_aggregated_tick_data(
        symbol='NIFTY',
        underlying='NIFTY 50',
        segment='INDICES',
        start_time=None,
        end_time=None,
        interval=1,
        unit='seconds',
        enable_volume=False, fut_index=0
    )
    print(res)
