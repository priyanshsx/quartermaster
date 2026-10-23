#--------------------beginning-of-code-------------------------#
#--------------------------------------------------------------#

# Imports libraries
import yfinance as yf
#--------------------------------------------------------------#

# Checks for data that each ticker fetches from yf
# tickers = [
#     "BTC-USD", "ETH-USD", "AAPL", "SPY", "MSFT", "RELIANCE.NS", "TCS.NS", "INFY.NS", "GLD", "SLV", "GC=F", "CL=F"
# ]

# for t in tickers:
#    try:
#        df = yf.download(t, period="1mo", auto_adjust=True, progress=False)
#        print(f"{t:14} rows={df.shape[0]:3} cols={list(df.columns)}")
#    except Exception as e:
#        print(f"{t:14} FAILED - {e}")

#--------------------------------------------------------------#
# Checks for the max missing days for each of the assets
# for t in ["BTC-USD", "AAPL", "RELIANCE.NS", "GC=F"]:
#    df = yf.download(t, start="2020-01-01", end="2025-12-31",
#                     auto_adjust=True, progress=False)
#    gaps = df.index.to_series().diff().dt.days.dropna()
#    print(f"{t:14} distinct gaps: {sorted(gaps.unique())}")
#--------------------------------------------------------------#

# Date caching checks 

df = yf.download("BTC-USD", start="2026-10-15", end="2026-10-24",
                 auto_adjust=True, progress=False)
print("download has:", df.index[-4:])

t = yf.Ticker("BTC-USD").history(period="max")
print("bounds max:", t.index.max())
#--------------------end-of-code-------------------------------#