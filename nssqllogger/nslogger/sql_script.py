CREATE_TICK_DATA_TABLE = """
CREATE TABLE IF NOT EXISTS tick_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument REAL,
    datetime DATETIME,
    price REAL,
    volume REAL,
    oi REAL
)
"""
CREATE_INSTRUMENT_TABLE = """
CREATE TABLE IF NOT EXISTS instrument_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_token REAL,
    exchange_token REAL,
    tradingsymbol TEXT,
    name TEXT,
    last_price REAL,
    expiry DATETIME,
    strike REAL,
    tick_size REAL,
    lot_size INTEGER,
    instrument_type TEXT,
    segment TEXT,
    exchange TEXT
)
"""
CREATE_NFO_TABLE = """
CREATE TABLE IF NOT EXISTS nfo_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    oi INTEGER,
    symbol TEXT,
    name TEXT,
    expiry TEXT,
    strike REAL,
    instrument_type TEXT
)
"""
CREATE_BFO_TABLE = """
CREATE TABLE IF NOT EXISTS bfo_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATETIME,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    oi INTEGER,
    symbol TEXT,
    name TEXT,
    expiry DATETIME,
    strike REAL,
    instrument_type TEXT
)
"""
CREATE_EXPIRY_DATES_TABLE = """
CREATE TABLE IF NOT EXISTS ExpiryDates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    expiry INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_INDIAVIXDATA_TABLE = """
CREATE TABLE IF NOT EXISTS IndiavixData (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ask REAL,
    bid REAL,
    description TEXT,
    ex_symbol TEXT,
    exchange TEXT,
    fyToken TEXT,
    ltp REAL,
    ltpch REAL,
    ltpchp REAL,
    option_type TEXT,
    strike_price REAL,
    symbol TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_OPTIONCHAINS_TABLE = """
CREATE TABLE IF NOT EXISTS OptionChains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ask REAL,
    bid REAL,
    description TEXT,
    ex_symbol TEXT,
    exchange TEXT,
    fp REAL,
    fpch REAL,
    fpchp REAL,
    fyToken TEXT,
    ltp REAL,
    ltpch REAL,
    ltpchp REAL,
    oi INTEGER,
    oich INTEGER,
    oichp REAL,
    option_type TEXT,
    prev_oi INTEGER,
    strike_price REAL,
    symbol TEXT,
    volume INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_METADATA_TABLE = """
CREATE TABLE IF NOT EXISTS Metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    callOi INTEGER,
    putOi INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""
CREATE_DATA_DEPTH_TICKS_TABLE = """
CREATE TABLE IF NOT EXISTS data_depth_ticks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bid_price1 REAL,
    bid_price2 REAL,
    bid_price3 REAL,
    bid_price4 REAL,
    bid_price5 REAL,
    ask_price1 REAL,
    ask_price2 REAL,
    ask_price3 REAL,
    ask_price4 REAL,
    ask_price5 REAL,
    bid_size1 INTEGER,
    bid_size2 INTEGER,
    bid_size3 INTEGER,
    bid_size4 INTEGER,
    bid_size5 INTEGER,
    ask_size1 INTEGER,
    ask_size2 INTEGER,
    ask_size3 INTEGER,
    ask_size4 INTEGER,
    ask_size5 INTEGER,
    bid_order1 INTEGER,
    bid_order2 INTEGER,
    bid_order3 INTEGER,
    bid_order4 INTEGER,
    bid_order5 INTEGER,
    ask_order1 INTEGER,
    ask_order2 INTEGER,
    ask_order3 INTEGER,
    ask_order4 INTEGER,
    ask_order5 INTEGER,
    type TEXT,
    symbol TEXT,
    created_at TEXT,
    UNIQUE (
        symbol, type, bid_price1, bid_price2, bid_price3, bid_price4, bid_price5,
        ask_price1, ask_price2, ask_price3, ask_price4, ask_price5
    )
)
"""
CREATE_STOCK_TICKS_TABLE = """
CREATE TABLE IF NOT EXISTS stock_ticks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ltp REAL,
    vol_traded_today INTEGER,
    last_traded_time INTEGER,
    exch_feed_time INTEGER,
    bid_size INTEGER,
    ask_size INTEGER,
    bid_price REAL,
    ask_price REAL,
    last_traded_qty INTEGER,
    tot_buy_qty INTEGER,
    tot_sell_qty INTEGER,
    avg_trade_price REAL,
    low_price REAL,
    high_price REAL,
    lower_ckt REAL,
    upper_ckt REAL,
    open_price REAL,
    prev_close_price REAL,
    type TEXT,
    symbol TEXT,
    ch REAL,
    chp REAL,
    created_at TEXT,
    UNIQUE (
        ltp, vol_traded_today, last_traded_time, exch_feed_time, bid_size, ask_size,
        bid_price, ask_price, last_traded_qty, tot_buy_qty, tot_sell_qty, avg_trade_price,
        low_price, high_price, lower_ckt, upper_ckt, open_price, prev_close_price, type, symbol, ch, chp
    )
)
"""

CREATE_INDEX_TICKS_TABLE = """
CREATE TABLE IF NOT EXISTS index_ticks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    ch REAL,
    high_price REAL,
    ltp REAL,
    exch_feed_time INTEGER,
    chp REAL,
    low_price REAL,
    open_price REAL,
    type TEXT,
    prev_close_price REAL,
    created_at TEXT,
    UNIQUE (
        symbol, ch, high_price, ltp, exch_feed_time, chp, low_price, open_price, type, prev_close_price
    )
)
"""