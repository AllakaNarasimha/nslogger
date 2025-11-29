import os
from datetime import datetime, timezone
from .sql_manager import SQLManager

class OptionChainManager:    
    def __init__(self, db_file="options.db"):
        self.create_db_file(db_file)
        skip_db_creation = False
        if os.path.exists(self.db_file):
            skip_db_creation = True
        self.sql = SQLManager(skip_db_creation, self.db_file)

    def create_db_file(self, db_file):
        now = datetime.now()
        month_year = now.strftime("%b%Y").lower()  # e.g., 'sep2025'
        dir_path = os.path.join(os.getcwd(), month_year)
        os.makedirs(dir_path, exist_ok=True)
        today_str = now.strftime("%d%b%y").lower()
        self.db_file = os.path.join(dir_path, f"{today_str}_{db_file}")

    def log_option_chain(self, oi: dict):
        # Generate a single timestamp for all inserts
        common_timestamp = datetime.now(timezone.utc).isoformat()

        expiry_data = oi.get('expiryData', [])
        indiavix = oi.get('indiavixData', {})
        options = oi.get('optionsChain', [])

        # Insert expiry data (list of dicts)
        if isinstance(expiry_data, list):
            for item in expiry_data:
                item['created_at'] = common_timestamp
                self.sql.insert_data(item, "ExpiryDates")
        elif isinstance(expiry_data, dict):
            expiry_data['created_at'] = common_timestamp
            self.sql.insert_data(expiry_data, "ExpiryDates")

        # Insert indiavix data (dict)
        if isinstance(indiavix, dict):
            indiavix['created_at'] = common_timestamp
            self.sql.insert_data(indiavix, "IndiavixData")

        # Insert options data (list of dicts)
        if isinstance(options, list):
            for item in options:
                item['created_at'] = common_timestamp
                self.sql.insert_data(item, "OptionChains")
        elif isinstance(options, dict):
            options['created_at'] = common_timestamp
            self.sql.insert_data(options, "OptionChains")
        
        callOi = oi.get('callOi', 0)
        putOi = oi.get('putOi', 0)
        metadata = {
            "callOi": callOi,
            "putOi": putOi,
            "created_at": common_timestamp
        }
        self.sql.insert_data(metadata, "Metadata")    
    
    def get_expiry_by_index(self, symbol, index):
        query = """
        WITH OrderedExpiries AS (
            SELECT id, date, expiry_timestamp, symbol,
                   ROW_NUMBER() OVER (ORDER BY expiry_timestamp) AS rn
            FROM ExpiryDates
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
        
    def get_option_chain_by_price_range(self, symbol, expiry_index, min_price, max_price):
        expiry = self.get_expiry_by_index(symbol, expiry_index)
        if expiry:
            expiry_timestamp = expiry[1]  # assuming (date, expiry_timestamp)
            query = "SELECT * FROM OptionChains WHERE expiry_timestamp = ? AND ltp BETWEEN ? AND ?"
            return self.sql.get_data(query, (expiry_timestamp, min_price, max_price))
        else:
            return []

    def get_nearest_price_option(self, symbol, expiry_index, target_price):
        expiry = self.get_expiry_by_index(symbol, expiry_index)
        if expiry:
            expiry_timestamp = expiry[1]  # (date, expiry_timestamp)
            query = """
            SELECT * FROM OptionChains WHERE expiry_timestamp = ? ORDER BY ABS(ltp - ?) LIMIT 1;
            """
            return self.sql.get_data(query, (expiry_timestamp, target_price))
        else:
            return []

    def get_option_chain_by_expiry(self, expiry_timestamp):
        expiry_date = self.sql.get_data("SELECT date FROM ExpiryDates WHERE expiry = ?", (expiry_timestamp,), one_or_all='one')
        if(not expiry_date):
            return []
        fetch_date = datetime.fromtimestamp(int(expiry_timestamp)).strftime("%d%b").upper() if expiry_date else None
        return self.sql.get_data("SELECT * FROM OptionChains WHERE symbol LIKE ?", (f"%{fetch_date}%",))

    def get_nearest_price_option(self, symbol, expiry_index, target_price):
        expiry = self.get_expiry_by_index(symbol, expiry_index)
        if expiry:
            expiry_timestamp = expiry[1]  # (date, expiry_timestamp)
            query = """
            SELECT * FROM OptionChains WHERE expiry_timestamp = ? ORDER BY ABS(ltp - ?) LIMIT 1;
            """
            return self.sql.get_data(query, (expiry_timestamp, target_price))
        else:
            return None

    def get_strike_rounded(price, round_to=50):
        return round(price / round_to) * round_to

    def get_atm_ce_pe_options(self, symbol, expiry_index, underlying_price, round_to=50):
        expiry = self.get_expiry_by_index(symbol, expiry_index)
        if expiry:
            expiry_timestamp = expiry[1]
            rounded_strike = self.get_strike_rounded(underlying_price, round_to)
            query = """
            SELECT *
            FROM OptionChains
            WHERE expiry_timestamp = ?
              AND option_type IN ('CE', 'PE')
              AND strike_price = (
                  SELECT strike_price FROM OptionChains
                  WHERE expiry_timestamp = ?
                  ORDER BY ABS(strike_price - ?) LIMIT 1
              )
            ORDER BY option_type;
            """
            return self.sql.get_data(query, (expiry_timestamp, expiry_timestamp, rounded_strike))
        else:
            return []

    def get_itm_otm_options(self, symbol, expiry_index, underlying_price, round_to=50, itm_index=0, otm_index=0):
        expiry = self.get_expiry_by_index(symbol, expiry_index)
        if not expiry:
            return None
        expiry_timestamp = expiry[1]  # (date, expiry_timestamp)
        rounded_strike = self.get_strike_rounded(underlying_price, round_to)

        results = {}

        # Step 2: Get ATM strike for expiry
        atm_strike_query = """
        SELECT strike_price
        FROM OptionChains
        WHERE expiry_timestamp = ?
        ORDER BY ABS(strike_price - ?) LIMIT 1;
        """
        atm_strike_row = self.sql.get_data(atm_strike_query, (expiry_timestamp, rounded_strike), one_or_all='one')
        if not atm_strike_row:
            return None
        atm_strike = atm_strike_row[0]

        # Step 3: Get ITM options by index
        if itm_index > 0:
            itm_ce_query = """
            SELECT * FROM OptionChains
            WHERE expiry_timestamp = ? AND option_type = 'CE' AND strike_price < ?
            ORDER BY strike_price DESC
            LIMIT 1 OFFSET ?;
            """
            results['ITM_CE'] = self.sql.get_data(itm_ce_query, (expiry_timestamp, atm_strike, itm_index - 1), one_or_all='one')

            itm_pe_query = """
            SELECT * FROM OptionChains
            WHERE expiry_timestamp = ? AND option_type = 'PE' AND strike_price > ?
            ORDER BY strike_price ASC
            LIMIT 1 OFFSET ?;
            """
            results['ITM_PE'] = self.sql.get_data(itm_pe_query, (expiry_timestamp, atm_strike, itm_index - 1), one_or_all='one')

        # Step 4: Get OTM options by index
        if otm_index > 0:
            otm_ce_query = """
            SELECT * FROM OptionChains
            WHERE expiry_timestamp = ? AND option_type = 'CE' AND strike_price > ?
            ORDER BY strike_price ASC
            LIMIT 1 OFFSET ?;
            """
            results['OTM_CE'] = self.sql.get_data(otm_ce_query, (expiry_timestamp, atm_strike, otm_index - 1), one_or_all='one')

            otm_pe_query = """
            SELECT * FROM OptionChains
            WHERE expiry_timestamp = ? AND option_type = 'PE' AND strike_price < ?
            ORDER BY strike_price DESC
            LIMIT 1 OFFSET ?;
            """
            results['OTM_PE'] = self.sql.get_data(otm_pe_query, (expiry_timestamp, atm_strike, otm_index - 1), one_or_all='one')

        return results
