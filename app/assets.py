#---------------------beginning-of-code------------------------#
#--------------------------------------------------------------#

# Global Variables 
MARKETS = {
    "crypto": {"trading_days": 365, "currency": "USD", "max_gap_days": 1},
    "us_equity": {"trading_days": 252, "currency": "USD", "max_gap_days": 4},
    "in_equity": {"trading_days": 252, "currency": "INR", "max_gap_days": 5},
    "uk_equity": {"trading_days": 252, "currency": "GBP", "max_gap_days": 5},
    "commodity": {"trading_days": 252, "currency": "USD", "max_gap_days": 4}
}

# NB: 
    # max_gap_days measured from yfinance history, 2020-01-01 to 2025-12-31.
    # Observed maxima: BTC-USD 1, AAPL 4, RELIANCE.NS 5 (Diwali), GC=F 4.
    # uk_equity set to 5 on Easter (LSE closes Good Friday and Easter Monday).

ASSET_SPECS = {
    # Crypto Assets 
    "BTC-USD": {"display": "Bitcoin", "market": "crypto"},
    "ETH-USD": {"display": "Ethereum", "market": "crypto"},
    "SOL-USD": {"display": "Solana", "market": "crypto"},
    "HYPE-USD": {"display": "Hype", "market": "crypto"},
    "USDT-USD": {"display": "USDT", "market": "crypto"},
    "BNB-USD": {"display": "BNB", "market": "crypto"},
    "XRP-USD": {"display": "XRP", "market": "crypto"},
    "ZEC-USD": {"display": "ZEC", "market": "crypto"},
    "WETH-USD": {"display": "WETH", "market": "crypto"},
    "TRX-USD": {"display": "TRX", "market": "crypto"},
    "NEAR-USD": {"display": "Near", "market": "crypto"}, 
    "LSK-USD": {"display": "LSK", "market": "crypto"},
    #--------------------------------------------------------------#
    
    # US Equity 
    "AAPL": {"display": "Apple", "market": "us_equity"},
    "SPY": {"display": "S&P500", "market": "us_equity"},
    "MSFT": {"display": "Microsoft", "market": "us_equity"},
    #--------------------------------------------------------------#

    # Indian Equity
    "RELIANCE.NS": {"display": "Reliance Industries", "market": "in_equity"},
    "TCS.NS": {"display": "TATA Consultancy Services", "market": "in_equity"},
    "INFY.NS": {"display": "Infosys", "market": "in_equity"},
    #--------------------------------------------------------------#

    # Commodity
    "GC=F": {"display": "Gold Futures", "market": "commodity"},
    "GLD": {"display": "Gold", "market": "commodity"},
    "SLV": {"display": "Silver", "market": "commodity"}
    #--------------------------------------------------------------#
}

def get_spec(ticker): 
    asset = ASSET_SPECS[ticker]
    return {**MARKETS[asset["market"]], **asset, "ticker": ticker}