import os
from datetime import datetime, timezone
from .sql_manager import SQLManager
from .db_util import DBUtil

class OptionChainManager:    
    def __init__(self, db_file="options.db", db_path=None):
        self.db_file = DBUtil.create_db_file(db_file, db_path)
        skip_db_creation = False
        if os.path.exists(self.db_file):
            skip_db_creation = True
        self.sql = SQLManager(skip_db_creation, self.db_file)

    def log_option_chain(self, oi: dict):
        # Generate a single timestamp for all inserts
        common_timestamp = datetime.now(timezone.utc).timestamp()

        expiry_data = oi.get('expiryData', [])
        indiavix = oi.get('indiavixData', {})
        options = oi.get('optionsChain', [])

        # Insert expiry data (list of dicts)
        if isinstance(expiry_data, list):
            for item in expiry_data:
                item['created_at'] = common_timestamp
                self.sql.insert_data(item, "expiry_dates")
        elif isinstance(expiry_data, dict):
            expiry_data['created_at'] = common_timestamp
            self.sql.insert_data(expiry_data, "expiry_dates")

        # Insert indiavix data (dict)
        if isinstance(indiavix, dict):
            indiavix['created_at'] = common_timestamp
            self.sql.insert_data(indiavix, "indiavix_data")

        # Insert options data (list of dicts)
        if isinstance(options, list):
            for item in options:
                item['created_at'] = common_timestamp
                self.sql.insert_data(item, "option_chains")
        elif isinstance(options, dict):
            options['created_at'] = common_timestamp
            self.sql.insert_data(options, "option_chains")
        
        callOi = oi.get('callOi', 0)
        putOi = oi.get('putOi', 0)
        metadata = {
            "callOi": callOi,
            "putOi": putOi,
            "created_at": common_timestamp
        }
        self.sql.insert_data(metadata, "metadata")    
    
    def get_expiry_by_index(self, symbol, index):
        query = """
        WITH OrderedExpiries AS (
            SELECT id, date, expiry_timestamp, symbol,
                   ROW_NUMBER() OVER (ORDER BY expiry_timestamp) AS rn
            FROM expiry_dates
            {symbol_filter}
        ),
        CurrentExpiry AS (
            SELECT * FROM OrderedExpiries
            WHERE expiry_timestamp >= strftime('%s', 'now')
            ORDER BY expiry_timestamp
            LIMIT 1
        ),
        TargetExpiry AS (
            SELECT * FROM OrderedExpiries, CurrentExpiry
            WHERE OrderedExpiries.rn = CurrentExpiry.rn + ?
        )
        SELECT date, expiry_timestamp FROM TargetExpiry;
        """
        symbol_filter = ""
        params = [index]
        if symbol:
            symbol_filter = "WHERE symbol = ?"
            params = [symbol, index]
        query = query.format(symbol_filter=symbol_filter)
        return self.sql.get_data(query, tuple(params), one_or_all='one')    
        
    def get_live_option_chain_by_price_range(self, symbol, expiry_index, min_price, max_price):
        """Get the latest option chain data filtered by price range"""
        expiry = self.get_expiry_by_index(symbol, expiry_index)
        if expiry:
            expiry_timestamp = expiry[1]  # assuming (date, expiry_timestamp)
            query = """
            SELECT * FROM option_chains 
            WHERE expiry_timestamp = ? 
              AND ltp BETWEEN ? AND ?
              AND created_at = (SELECT MAX(created_at) FROM option_chains)
            """
            return self.sql.get_data(query, (expiry_timestamp, min_price, max_price))
        else:
            return []

    def get_live_option_chain_by_expiry(self, expiry_timestamp):
        """Get the latest option chain data for a specific expiry"""
        expiry_date = self.sql.get_data("SELECT date FROM expiry_dates WHERE expiry = ?", (expiry_timestamp,), one_or_all='one')
        if(not expiry_date):
            return []
        fetch_date = datetime.fromtimestamp(int(expiry_timestamp)).strftime("%d%b").upper() if expiry_date else None
        query = """
        SELECT * FROM option_chains 
        WHERE symbol LIKE ? 
          AND created_at = (SELECT MAX(created_at) FROM option_chains)
        """
        return self.sql.get_data(query, (f"%{fetch_date}%",))

    def get_live_nearest_price_option(self, symbol, expiry_index, target_price):
        expiry = self.get_expiry_by_index(symbol, expiry_index)
        if expiry:
            expiry_timestamp = expiry[1]  # (date, expiry_timestamp)
            query = """
            SELECT * FROM option_chains 
            WHERE expiry_timestamp = ? 
              AND created_at = (SELECT MAX(created_at) FROM option_chains)
            ORDER BY ABS(ltp - ?) LIMIT 1;
            """
            return self.sql.get_data(query, (expiry_timestamp, target_price))
        else:
            return []
        
    def get_live_atm_ce_pe_options(self, symbol, expiry_index, underlying_price, round_to):
        expiry = self.get_expiry_by_index(symbol, expiry_index)
        if expiry:
            expiry_timestamp = expiry[1]
            rounded_strike = self.get_strike_rounded(underlying_price, round_to)
            query = """
            SELECT *
            FROM option_chains
            WHERE expiry_timestamp = ?
              AND option_type IN ('CE', 'PE')
              AND created_at = (SELECT MAX(created_at) FROM option_chains)
              AND strike_price = (
                  SELECT strike_price FROM option_chains
                  WHERE expiry_timestamp = ?
                    AND created_at = (SELECT MAX(created_at) FROM option_chains)
                  ORDER BY ABS(strike_price - ?) LIMIT 1
              )
            ORDER BY option_type;
            """
            return self.sql.get_data(query, (expiry_timestamp, expiry_timestamp, rounded_strike))
        else:
            return []

    def get_live_itm_otm_options(self, symbol, expiry_index, underlying_price, round_to, itm_index, otm_index):
        expiry = self.get_expiry_by_index(symbol, expiry_index)
        if not expiry:
            return None
        expiry_timestamp = expiry[1]  # (date, expiry_timestamp)
        rounded_strike = self.get_strike_rounded(underlying_price, round_to)

        results = {}

        # Step 2: Get ATM strike for expiry
        atm_strike_query = """
        SELECT strike_price
        FROM option_chains
        WHERE expiry_timestamp = ? AND created_at = (SELECT MAX(created_at) FROM option_chains)
        ORDER BY ABS(strike_price - ?) LIMIT 1;
        """
        atm_strike_row = self.sql.get_data(atm_strike_query, (expiry_timestamp, rounded_strike), one_or_all='one')
        
        if not atm_strike_row:
            return None
        atm_strike = atm_strike_row[0]

        # Step 3: Get ITM options by index
        if itm_index > 0:
            itm_ce_query = """
            SELECT * FROM option_chains
            WHERE expiry_timestamp = ? AND option_type = 'CE' AND strike_price < ? AND created_at = (SELECT MAX(created_at) FROM option_chains)
            ORDER BY strike_price DESC
            LIMIT 1 OFFSET ?;
            """
            results['ITM_CE'] = self.sql.get_data(itm_ce_query, (expiry_timestamp, atm_strike, itm_index - 1), one_or_all='one')

            itm_pe_query = """
            SELECT * FROM option_chains
            WHERE expiry_timestamp = ? AND option_type = 'PE' AND strike_price > ? AND created_at = (SELECT MAX(created_at) FROM option_chains)
            ORDER BY strike_price ASC
            LIMIT 1 OFFSET ?;
            """
            results['ITM_PE'] = self.sql.get_data(itm_pe_query, (expiry_timestamp, atm_strike, itm_index - 1), one_or_all='one')

        # Step 4: Get OTM options by index
        if otm_index > 0:
            otm_ce_query = """
            SELECT * FROM option_chains
            WHERE expiry_timestamp = ? AND option_type = 'CE' AND strike_price > ? AND created_at = (SELECT MAX(created_at) FROM option_chains)
            ORDER BY strike_price ASC
            LIMIT 1 OFFSET ?;
            """
            results['OTM_CE'] = self.sql.get_data(otm_ce_query, (expiry_timestamp, atm_strike, otm_index - 1), one_or_all='one')

            otm_pe_query = """
            SELECT * FROM option_chains
            WHERE expiry_timestamp = ? AND option_type = 'PE' AND strike_price < ? AND created_at = (SELECT MAX(created_at) FROM option_chains)
            ORDER BY strike_price DESC
            LIMIT 1 OFFSET ?;
            """
            results['OTM_PE'] = self.sql.get_data(otm_pe_query, (expiry_timestamp, atm_strike, otm_index - 1), one_or_all='one')

        return results

        
    def get_option_chain_by_price_range(self, symbol, created_at, expiry_index, min_price, max_price):
        expiry = self.get_expiry_by_index(symbol, expiry_index)
        if expiry:
            expiry_timestamp = expiry[1]  # assuming (date, expiry_timestamp)
            if created_at is not None:
                query = "SELECT * FROM option_chains WHERE expiry_timestamp = ? AND ltp BETWEEN ? AND ? AND created_at = ?"
                return self.sql.get_data(query, (expiry_timestamp, min_price, max_price, created_at))
            else:
                query = "SELECT * FROM option_chains WHERE expiry_timestamp = ? AND ltp BETWEEN ? AND ?"
                return self.sql.get_data(query, (expiry_timestamp, min_price, max_price))
        else:
            return []
        
    def get_nearest_price_option(self, symbol, created_at, expiry_index, target_price):
        expiry = self.get_expiry_by_index(symbol, expiry_index)
        if expiry:
            expiry_timestamp = expiry[1]  # (date, expiry_timestamp)
            if created_at is not None:
                query = """
                SELECT * FROM option_chains WHERE expiry_timestamp = ? AND created_at = ? ORDER BY ABS(ltp - ?) LIMIT 1;
                """
                return self.sql.get_data(query, (expiry_timestamp, created_at, target_price))
            else:
                query = """
                SELECT * FROM option_chains WHERE expiry_timestamp = ? ORDER BY ABS(ltp - ?) LIMIT 1;
                """
                return self.sql.get_data(query, (expiry_timestamp, target_price))
        else:
            return []

    def get_option_chain_by_expiry(self, created_at, expiry_timestamp):
        expiry_date = self.sql.get_data("SELECT date FROM expiry_dates WHERE expiry = ?", (expiry_timestamp,), one_or_all='one')
        if(not expiry_date):
            return []
        fetch_date = datetime.fromtimestamp(int(expiry_timestamp)).strftime("%d%b").upper() if expiry_date else None
        return self.sql.get_data("SELECT * FROM option_chains WHERE symbol LIKE ? AND created_at = ?", (f"%{fetch_date}%", created_at))

    def get_strike_rounded(price, round_to=50):
        return round(price / round_to) * round_to

    def get_atm_ce_pe_options(self, symbol, created_at, expiry_index, underlying_price, round_to):
        expiry = self.get_expiry_by_index(symbol, expiry_index)
        if expiry:
            expiry_timestamp = expiry[1]
            rounded_strike = self.get_strike_rounded(underlying_price, round_to)
            query = """
            SELECT *
            FROM option_chains
            WHERE expiry_timestamp = ?
              AND option_type IN ('CE', 'PE')
              AND created_at = ?
              AND strike_price = (
                  SELECT strike_price FROM option_chains
                  WHERE expiry_timestamp = ?
                    AND created_at = ?
                  ORDER BY ABS(strike_price - ?) LIMIT 1
              )
            ORDER BY option_type;
            """
            return self.sql.get_data(query, (expiry_timestamp, created_at, expiry_timestamp, created_at, rounded_strike))
        else:
            return []

    def get_itm_otm_options(self, symbol, created_at, expiry_index, underlying_price, round_to, itm_index, otm_index):
        expiry = self.get_expiry_by_index(symbol, expiry_index)
        if not expiry:
            return None
        expiry_timestamp = expiry[1]  # (date, expiry_timestamp)
        rounded_strike = self.get_strike_rounded(underlying_price, round_to)

        results = {}

        # Step 2: Get ATM strike for expiry
        atm_strike_query = """
        SELECT strike_price
        FROM option_chains
        WHERE expiry_timestamp = ? AND created_at = ?
        ORDER BY ABS(strike_price - ?) LIMIT 1;
        """
        atm_strike_row = self.sql.get_data(atm_strike_query, (expiry_timestamp, created_at, rounded_strike), one_or_all='one')
        
        if not atm_strike_row:
            return None
        atm_strike = atm_strike_row[0]

        # Step 3: Get ITM options by index
        if itm_index > 0:
            itm_ce_query = """
            SELECT * FROM option_chains
            WHERE expiry_timestamp = ? AND option_type = 'CE' AND strike_price < ? AND created_at = ?
            ORDER BY strike_price DESC
            LIMIT 1 OFFSET ?;
            """
            results['ITM_CE'] = self.sql.get_data(itm_ce_query, (expiry_timestamp, atm_strike, created_at, itm_index - 1), one_or_all='one')

            itm_pe_query = """
            SELECT * FROM option_chains
            WHERE expiry_timestamp = ? AND option_type = 'PE' AND strike_price > ? AND created_at = ?
            ORDER BY strike_price ASC
            LIMIT 1 OFFSET ?;
            """
            results['ITM_PE'] = self.sql.get_data(itm_pe_query, (expiry_timestamp, atm_strike, created_at, itm_index - 1), one_or_all='one')

        # Step 4: Get OTM options by index
        if otm_index > 0:
            otm_ce_query = """
            SELECT * FROM option_chains
            WHERE expiry_timestamp = ? AND option_type = 'CE' AND strike_price > ? AND created_at = ?
            ORDER BY strike_price ASC
            LIMIT 1 OFFSET ?;
            """
            results['OTM_CE'] = self.sql.get_data(otm_ce_query, (expiry_timestamp, atm_strike, created_at, otm_index - 1), one_or_all='one')

            otm_pe_query = """
            SELECT * FROM option_chains
            WHERE expiry_timestamp = ? AND option_type = 'PE' AND strike_price < ? AND created_at = ?
            ORDER BY strike_price DESC
            LIMIT 1 OFFSET ?;
            """
            results['OTM_PE'] = self.sql.get_data(otm_pe_query, (expiry_timestamp, atm_strike, created_at, otm_index - 1), one_or_all='one')

        return results
