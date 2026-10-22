#---------------------beginning-of-code------------------------#
#--------------------------------------------------------------#

# Global Variables 
MARKETS = {
    "crypto": {"trading_days": 365, "currency": "USD", "max_gap_days": 1},
    "us_equity": {"trading_days": 252, "currency": "USD", "max_gap_days": 4},
    "in_equity": {"trading_days": 252, "currency": "INR", "max_gap_days": 4},
    "uk_equity": {"trading_days": 252, "currency": "GBP", "max_gap_days": 4},
    "commodity": {"trading_days": 252, "currency": "USD", "max_gap_days": 4}
}

ASSET_SPECS = {
    "BTC-USD": {"display": "Bitcoin", "market": "crypto"},
    "AAPL": {"display": "Apple", "market": "us_equity"},
    "RELIANCE.NS": {"display": "Reliance Industries", "market": "in_equity"},
    "GC=F": {"display": "Gold Futures", "market": "commodity"},
    "ETH-USD": {"display": "Ethereum", "market": "crypto"},
    "SPY": {"display": "S&P500", "market": "us_equity"},
    "MSFT": {"display": "Microsoft", "market": "us_equity"},
    "TCS.NS": {"display": "TATA Consultancy Services", "market": "in_equity"},
    "INFY.NS": {"display": "Infosys", "market": "in_equity"},
    "GLD": {"display": "Gold", "market": "commodity"},
    "SLV": {"display": "Silver", "market": "commodity"}
}

def get_spec(ticker): 
    asset = ASSET_SPECS[ticker]
    return {**MARKETS[asset["market"]], **asset, "ticker": ticker}