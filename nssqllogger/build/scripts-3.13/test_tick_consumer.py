from nslogger.option_chain_manager import OptionChainManager
from nslogger.tick_manager import TickManager

def test_tick_manager():
    tm = TickManager(table='index_ticks', db_file='test_ticks.db')
    
    # Test logging a tick
    test_tick = {
        "symbol":"NSE:NIFTY50-INDEX",
        "ch":"-27.95",
        "high_price":"26277.35",
        "ltp":"26188.1",
        "exch_feed_time":"1727428424",
        "chp":"-0.11",
        "low_price":"26166.95",
        "open_price":"26248.25",
        "type":"if",
        "prev_close_price":"26216.05"
    }
    tm.log_tick(test_tick)
    
    # Test retrieving all ticks
    all_ticks = tm.get_all_ticks()
    assert len(all_ticks) > 0, "No ticks found in the database."
    
    # Test retrieving ticks by symbol
    test_symbol_ticks = tm.get_ticks_by_symbol('NSE:NIFTY50-INDEX')
    assert len(test_symbol_ticks) > 0, "No ticks found for symbol NSE:NIFTY50-INDEX."
    assert test_symbol_ticks[0][1] == 'NSE:NIFTY50-INDEX', "Retrieved tick symbol does not match."

def data_depth_tick_manager():
    tm = TickManager(table='data_depth_ticks', db_file='test_ticks.db')

    # Test logging a tick
    test_tick = {
        "bid_price1":606.25,
        "bid_price2":606.2,
        "bid_price3":606.15,
        "bid_price4":606.1,
        "bid_price5":606.05,
        "ask_price1":606.3,
        "ask_price2":606.35,
        "ask_price3":606.4,
        "ask_price4":606.45,
        "ask_price5":606.5,
        "bid_size1":20,
        "bid_size2":902,
        "bid_size3":111,
        "bid_size4":110,
        "bid_size5":979,
        "ask_size1":282,
        "ask_size2":568,
        "ask_size3":2910,
        "ask_size4":1676,
        "ask_size5":2981,
        "bid_order1":1,
        "bid_order2":3,
        "bid_order3":2,
        "bid_order4":2,
        "bid_order5":9,
        "ask_order1":4,
        "ask_order2":2,
        "ask_order3":12,
        "ask_order4":9,
        "ask_order5":17,
        "type":"dp",
        "symbol":"NSE:SBIN-EQ"
    }
    tm.log_tick(test_tick)
    
    # Test retrieving all ticks
    all_ticks = tm.get_all_ticks()
    assert len(all_ticks) > 0, "No ticks found in the database."
    
    # Test retrieving ticks by symbol
    test_symbol_ticks = tm.get_ticks_by_symbol('NSE:SBIN-EQ')
    assert len(test_symbol_ticks) > 0, "No ticks found for symbol NSE:SBIN-EQ."
    assert test_symbol_ticks[0][32] == 'NSE:SBIN-EQ', "Retrieved tick symbol does not match."

def option_chain_tick_manager():
    tm = OptionChainManager()

    # Test logging a tick
    test_tick = {
        "callOi": 9926700,
        "expiryData": [
            {
                "date": "25-04-2024",
                "expiry": "1714039200"
            },
            {
                "date": "30-05-2024",
                "expiry": "1717063200"
            },
            {
                "date": "27-06-2024",
                "expiry": "1719482400"
            }
        ],
        "indiavixData": {
            "ask": 0,
            "bid": 0,
            "description": "INDIAVIX-INDEX",
            "ex_symbol": "INDIAVIX",
            "exchange": "NSE",
            "fyToken": "101000000026017",
            "ltp": 10.34,
            "ltpch": -2.36,
            "ltpchp": -18.58,
            "option_type": "",
            "strike_price": -1,
            "symbol": "NSE:INDIAVIX-INDEX"
        },
        "optionsChain": [
            {
                "ask": 3889.2,
                "bid": 3889.1,
                "description": "TATA CONSULTANCY SERV LT",
                "ex_symbol": "TCS",
                "exchange": "NSE",
                "fp": 3884.1,
                "fpch": 21.65,
                "fpchp": 0.56,
                "fyToken": "101000000011536",
                "ltp": 3889.2,
                "ltpch": 24.6,
                "ltpchp": 0.64,
                "option_type": "",
                "strike_price": -1,
                "symbol": "NSE:TCS-EQ"
            },
            {
                "ask": 40.35,
                "bid": 39.55,
                "fyToken": "1011240425139431",
                "ltp": 40.5,
                "ltpch": 8.4,
                "ltpchp": 26.17,
                "oi": 93275,
                "oich": -9625,
                "oichp": -9.35,
                "option_type": "CE",
                "prev_oi": 102900,
                "strike_price": 3860,
                "symbol": "NSE:TCS24APR3860CE",
                "volume": 229950
            },
            {
                "ask": 15.85,
                "bid": 15.65,
                "fyToken": "1011240425139432",
                "ltp": 15.55,
                "ltpch": -15.9,
                "ltpchp": -50.56,
                "oi": 162225,
                "oich": 31675,
                "oichp": 24.26,
                "option_type": "PE",
                "prev_oi": 130550,
                "strike_price": 3860,
                "symbol": "NSE:TCS24APR3860PE",
                "volume": 347900
            },
            {
                "ask": 28.8,
                "bid": 28.45,
                "fyToken": "1011240425133432",
                "ltp": 28.75,
                "ltpch": 3.25,
                "ltpchp": 12.75,
                "oi": 162225,
                "oich": 6300,
                "oichp": 4.04,
                "option_type": "CE",
                "prev_oi": 155925,
                "strike_price": 3880,
                "symbol": "NSE:TCS24APR3880CE",
                "volume": 606200
            },
            {
                "ask": 24.85,
                "bid": 24.5,
                "fyToken": "1011240425133433",
                "ltp": 24.9,
                "ltpch": -18.4,
                "ltpchp": -42.49,
                "oi": 102550,
                "oich": 32725,
                "oichp": 46.87,
                "option_type": "PE",
                "prev_oi": 69825,
                "strike_price": 3880,
                "symbol": "NSE:TCS24APR3880PE",
                "volume": 223650
            },
            {
                "ask": 21,
                "bid": 20.85,
                "fyToken": "1011240425139433",
                "ltp": 21.1,
                "ltpch": 1.95,
                "ltpchp": 10.18,
                "oi": 614775,
                "oich": 7000,
                "oichp": 1.15,
                "option_type": "CE",
                "prev_oi": 607775,
                "strike_price": 3900,
                "symbol": "NSE:TCS24APR3900CE",
                "volume": 1166375
            },
            {
                "ask": 36.5,
                "bid": 36.05,
                "fyToken": "1011240425139434",
                "ltp": 35.7,
                "ltpch": -20.7,
                "ltpchp": -36.7,
                "oi": 344225,
                "oich": -3850,
                "oichp": -1.11,
                "option_type": "PE",
                "prev_oi": 348075,
                "strike_price": 3900,
                "symbol": "NSE:TCS24APR3900PE",
                "volume": 158900
            }
        ],
        "putOi": 3789100
    }
    tm.log_option_chain(test_tick)
    
    # Test retrieving option chains by symbol
    test_symbol_option_chains = tm.get_option_chain_by_expiry(1714039200)
    print(len(test_symbol_option_chains) > 0, "No option chains found for symbol NSE:TCS24APR3900PE.")
    

if __name__ == "__main__":
    #test_tick_manager()
    #data_depth_tick_manager()
    option_chain_tick_manager()

