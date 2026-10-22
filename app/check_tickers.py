import yfinance as yf

tickers = [
    "BTC-USD", "ETH-USD", "AAPL", "SPY", "MSFT", "RELIANCE.NS", "TCS.NS", "INFY.NS", "GLD", "SLV", "GC=F", "CL=F"
]

for t in tickers:
    try:
        df = yf.download(t, period="1mo", auto_adjust=True, progress=False)
        print(f"{t:14} rows={df.shape[0]:3} cols={list(df.columns)}")
    except Exception as e:
        print(f"{t:14} FAILED - {e}")
