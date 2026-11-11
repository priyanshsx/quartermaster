# Quartermaster Methodology

Every number Quartermaster shows, and exactly how it is calculated. Nothing here is
proprietary — the point is that you can check the work.

This file is the single source of truth. The published docs page is generated from it.
If the two ever disagree, this file is right and the page is stale.

**Version 1.1 · Applies to the live app**

---

## Scope

Quartermaster downloads daily market data for a selected asset, audits that data before
doing any arithmetic, and then computes a small set of risk and return figures. All
calculations run on pandas and NumPy using the daily closing price unless stated
otherwise.

There are three pages:

- **Performance Calculator** — what a given amount invested on a given date would be
  worth now, and the worst and best points along the way.
- **Quant Mode** — risk and return figures for one asset: volatility, drawdown,
  distribution, moving averages.
- **Correlations** — how one asset moved relative to up to five others.

## Market conventions

Quartermaster is not crypto-specific. Each asset is tagged with a market, and the market
supplies the conventions used in its calculations:

| Market | Periods per year | Currency | Normal maximum gap |
|---|---|---|---|
| Crypto | 365 | USD | 1 day |
| US equity | 252 | USD | 4 days |
| Indian equity | 252 | INR | 5 days |
| UK equity | 252 | GBP | 5 days |
| Commodity | 252 | USD | 4 days |

Crypto markets trade every day of the year, so annualisation for a crypto asset uses 365
periods rather than the 252 trading days conventional for equities. The maximum gap
figures were measured from Yahoo Finance history between 2020-01-01 and 2025-12-31:
BTC-USD 1, AAPL 4, RELIANCE.NS 5 (Diwali), GC=F 4. UK equity is set to 5 because the LSE
closes both Good Friday and Easter Monday.

Figures are shown in each asset's own trading currency. **No currency conversion is
applied anywhere.**

---

## Limitations

Read this section first. A tool that hides its weaknesses is not worth trusting, and
these affect how much weight to put on any figure below.

- **Data quality depends on Yahoo Finance.** It is a free, aggregated source. It can
  carry gaps, delayed updates and occasional errors, and its figures differ from
  exchange-level data. The Tick Inspector catches structural problems, not every possible
  inaccuracy.
- **Short histories make statistics unreliable.** Skewness, excess kurtosis, volatility
  and rolling correlation all need a reasonable sample. Over short ranges some figures
  will not appear at all, because their windows have not filled.
- **Stablecoins and wrapped assets behave differently.** A stablecoin's near-zero returns
  and extreme kurtosis reflect its peg, not market behaviour. Stablecoins are excluded
  from the Correlations page entirely, because correlation against a fixed value is
  undefined rather than low.
- **Annualisation is an approximation.** Scaling by the square root of the period count
  assumes daily returns are independent of one another. That is the conventional
  assumption, not a measured fact.
- **Gaps distort some figures.** If a date is missing, the following return spans more
  than one day while being treated as one. See the integrity checks.
- **Nothing here is predictive.** Every figure describes what already happened.
- **No costs are modelled.** Transaction fees, slippage, spreads and taxes appear nowhere
  in these calculations.

---

## How the pipeline works

The app runs a fixed sequence and will stop rather than show numbers it does not trust.

```
Select asset + dates → Download → Tick Inspector → Analyzer → Page
                                        │
                                   bad data?
                                        │
                        Hard Stop: report the problem, render nothing
```

1. **The Gatekeeper.** Every download passes through the Tick Inspector before any
   calculation runs.
2. **The Health Check.** If the inspector finds corrupted data, the pipeline halts and
   says which rows or dates are affected. Bad data never reaches a chart.
3. **The Render.** If the data passes, the analytics run and the page is drawn.

Missing calendar dates are treated differently from corrupted values: a small number of
gaps produces a visible warning but the analysis still runs.

On the Correlations page the inspector runs per asset, before any pairing. A single
failing comparison asset is dropped and named; only a failing primary asset stops the
page.

## Data source

- **Provider:** Yahoo Finance, through the `yfinance` library.
- **Frequency:** daily bars (open, high, low, close, volume).
- **Price adjustment:** `auto_adjust=True` is set explicitly, so output does not depend on
  a library default that could change between versions. Prices are adjusted for splits
  and dividends, which makes every return a total return.
- **Date range:** date pickers are bounded by the earliest and latest dates Yahoo holds
  for the selected asset. Yahoo treats a download's end date as exclusive, so the app adds
  one day internally, making the date you pick inclusive.
- **The current session is excluded.** Today's bar has not closed, so it is dropped. This
  is why figures do not shift between page loads during the trading day.
- **Column handling:** columns are lower-cased to `open`, `high`, `low`, `close`,
  `volume`; the index is named `date`.
- **Caching:** downloads are cached for one hour and each asset's available date range for
  24 hours, so repeated interaction does not hammer Yahoo Finance. Failures are never
  cached — a temporary outage cannot be stored and served to the next visitor.

## Integrity checks (the Tick Inspector)

Four checks are fatal and one is tolerated up to a limit.

| Check | Looks for | If it fails |
|---|---|---|
| Duplicate rows | Repeated timestamps in the index | Hard stop |
| Corrupted high/low | Rows where low is above high | Hard stop |
| Negative volume | Rows where volume is below zero | Hard stop |
| High violations | Rows where open or close is above high | Hard stop |
| Missing dates | Gaps beyond the market's normal maximum | Warning up to 5 excess days, then hard stop |

Gaps are measured against the market's own normal maximum rather than against a calendar,
so a weekend is not reported as missing data for an equity and a Diwali closure is not
reported as missing for an Indian stock. Only days beyond that normal gap count as excess.

---

## Returns

**Simple daily return** — the percentage change from one close to the next:

$$r_t = \frac{P_t}{P_{t-1}} - 1$$

**Log return** — the natural logarithm of the same ratio:

$$\ell_t = \ln\left(\frac{P_t}{P_{t-1}}\right)$$

Simple returns compound multiplicatively and are what a position actually earns. Log
returns add over time and are better behaved for statistics, which is why volatility,
skewness and kurtosis use them while value figures use simple returns.

## Moving averages

20-day and 50-day simple moving averages of the closing price. They are descriptive
context, not signals.

## Rolling volatility

The standard deviation of daily log returns over a trailing 30 days, annualised by
multiplying by the square root of the market's periods per year:

$$\sigma_{\text{ann}} = \sigma_{30} \times \sqrt{N}$$

where $N$ is 365 for crypto and 252 for equities and commodities. The first 29 days of any
range produce no value, because the window has not filled.

## Cumulative return

$$R_{\text{cum}}(t) = \prod_{s=1}^{t}(1 + r_s) - 1$$

The total gain or loss since the first close in the selected range — not the asset's
all-time first price. A value of 1.5 means +150%.

## Drawdown and maximum drawdown

A growth index is built by compounding daily simple returns from 1:

$$W_t = \prod_{s=1}^{t}(1 + r_s), \qquad W_0 = 1$$

$$M_t = \max_{s \le t} W_s, \qquad D_t = \frac{W_t - M_t}{M_t}$$

**Drawdown** is how far the asset sits below its highest point so far, as a percentage.
It is always zero or negative. **Maximum drawdown** is the lowest value it reaches over
the period: the worst peak-to-trough loss someone holding throughout would have lived
through. The peak starts at the first close in the range, so an immediate fall is measured
from that starting point.

## Distribution statistics

Both are computed on daily log returns using the pandas estimators `.skew()` and
`.kurt()`.

**Skewness** measures asymmetry — which side holds the bigger surprises. Negative means
the left tail is longer, so the largest moves have tended to be drops. Positive means the
extremes lean toward gains.

**Excess kurtosis** measures tail weight against a normal distribution. Pandas `.kurt()`
returns excess kurtosis (kurtosis minus 3), so a normal distribution scores 0. Large
positive values mean fat tails: extreme days occur far more often than a bell curve
predicts. Crypto assets typically score high.

## Average daily returns

The mean daily log return and the mean daily simple return. These are arithmetic daily
averages. They are **not** annualised and should not be read as an expected future
return — a small average can conceal very large swings, which is why they sit next to
volatility and drawdown rather than alone.

## Returns histogram

Daily log returns grouped into fixed-width bins, so each bar covers the same width however
extreme the underlying data. The x-axis is zoomed to the 1st–99th percentile so the bulk
of the distribution stays readable; the extreme days are still in the data and still in
the chart.

---

## The Performance Calculator

Answers: if a given amount had been invested in an asset at a given month, what would it
be worth now?

- **Entry** is the closing price on the **first trading day** of the month you choose.
- **Exit** is the closing price on the last completed session in the range.
- **Value over time** is the amount multiplied by the cumulative return, so every figure
  on the page is that position's value on a given day.
- **The worst it got** is the lowest that value ever reached, and the date it happened.
  **The best it got** is the highest. Realising the best would have required selling on
  that exact day.
- **Time spent underwater** counts the days the position was worth less than the amount
  put in.
- **Worst day, week and month** are the largest falls over those spans. Weekly and monthly
  figures compound the daily returns within each period rather than summing them.

Prices are adjusted for splits and dividends, so these are total returns. No costs or
taxes are modelled.

---

## Correlations

Answers: how did one asset move relative to another?

### Putting two assets on a shared calendar

Two assets rarely trade on the same days. Bitcoin trades every day; the NSE does not.
Returns are therefore computed from closing prices **on the days both assets traded**.

A move on a day only one asset traded is **compounded into its next shared observation**,
not discarded. A Bitcoin weekend is carried into Monday.

Worked example. Bitcoin closes Friday 100, Saturday 104, Sunday 110, Monday 108. An equity
closes Friday 50 and Monday 52.

- Dropping the weekend *returns* would make Bitcoin's Monday 110 → 108 = −1.8%, paired
  against the equity's +4%. They would appear to move in opposite directions.
- Dropping the weekend *prices* gives 100 → 108 = **+8%** against **+4%**. Both up, over
  the same Friday-to-Monday window.

The weekend lives inside that +8%: `1.04 × 1.0577 × 0.9818 = 1.08`.

### Market close times

Markets close at different times, so a "same day" comparison can cover slightly different
windows.

| Market | Close (UTC, winter) |
|---|---|
| NSE (India) | 10:00 |
| LSE (UK) | 16:30 |
| NYSE / NASDAQ | 21:00 |
| Bitcoin daily bar | 00:00 next day |

Weekly returns are the default whenever two assets trade on different markets, because a
weekly window reduces that mismatch to a small fraction of the period.

### Why the daily and weekly figures differ

Correlation depends on the period you measure it over, and the daily and weekly figures
will usually differ.

Two assets can react to the same news on the same day and still end a week in different
places, if one of them partly unwinds that reaction or has strong moves of its own. Over a
longer window each asset's own behaviour accumulates while a shared one-off reaction does
not — so the two numbers answer different questions rather than one being more accurate.

Use the daily figure to ask whether two assets react to the same events. Use the weekly
figure to ask whether they end up in the same place. If you hold for months, the weekly
figure matches your horizon.

Neither frequency is generally higher than the other. Which one reads higher depends on
the pair.

### The figures

**Correlation** is the Pearson correlation of the two aligned return series.

**Beta** is the slope of the primary asset against the comparison asset:

$$\beta = \frac{\operatorname{cov}(a, b)}{\operatorname{var}(b)}$$

It reads as *how far the primary asset moved, on average, per 1% move in the other*. It is
**not** a market beta, and against an asset that is not a market index it has no standard
interpretation beyond that slope.

**R²** is correlation squared — the same measurement expressed as a share of movement, not
an independent finding.

**Same direction** is the share of periods in which both assets moved the same way.
Periods where either return was exactly zero are excluded, because direction is undefined
there.

**Lead and lag** are three correlations: the comparison asset's previous period against
the primary's current one, the two contemporaneous, and the primary's previous against the
comparison's current. A high value in the first means the comparison asset moved first.
These are computed on **daily** returns whatever the page is showing, because weekly
returns are too coarse to separate a lead from a lag.

### Rolling windows

Rolling figures use a **52-week** window on weekly returns. On daily returns the window is
one year of shared trading days, which depends on the pair: **365** when both assets trade
every day of the week, **252** as soon as an equity is involved.

A shorter window would be noisier. A correlation measured from 26 observations carries
roughly ±0.4 of uncertainty, so a rolling line that short mostly shows sampling noise
rather than a changing relationship.

### What is not offered

Stablecoins are excluded from this page. A stablecoin holds a fixed value by design, so it
has almost no variation to measure, and correlation against it is undefined rather than
low.

---

## Changelog

Corrections and methodology changes are recorded here. If a published figure was wrong,
the fix and its date appear below rather than being quietly amended.

| Date | Version | Change |
|---|---|---|
| 2026-11-11 | 1.1 | Multi-asset conventions replace the crypto-only annualisation rule. Performance Calculator and Correlations documented. Rolling correlation windows set to 52 weeks and one year of shared trading days, from 26 weeks and 90 days. |
| — | 1.0 | First public release. |

Spotted an error in any of the above? Tell me — that is the most useful message you can
send.
