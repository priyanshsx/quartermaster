#---------------------beginning-of-code------------------------#
#--------------------------------------------------------------#

# Imports libraries
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import timedelta
from assets import ASSET_SPECS, get_spec
from charts import style_fig
from engine import (
    get_asset_date_bounds,
    fetch_asset,
    tick_inspector,
    quant_analyzer,
    align_pair,
    pair_analyzer,
    default_freq,
)
#--------------------------------------------------------------#

# Global variables 
# Rolling window lengths. Weekly is a flat 52: resampling gives 52 weeks a year
# whatever the underlying calendar, so a weekly window is a year for every pair.
WINDOW_W = 52


# One year of shared trading days for a pair. The joined calendar can hold no
# more days than the thinner of the two markets trades, so 365 when both assets
# trade every day and 252 as soon as an equity is involved.
def daily_window(spec_a, spec_b):
    return min(spec_a["trading_days"], spec_b["trading_days"])

# Assets that can be compared. A stablecoin holds a fixed value by design, so it
# has almost no variation to measure: correlation against it is undefined rather
# than low. Those carry comparable: False in the registry.
COMPARABLE = [t for t, a in ASSET_SPECS.items() if a.get("comparable", True)]

# Chart series colours, from the site palette in .streamlit/config.toml. Violet
# (#A78BFA) is deliberately left out: against the blue it measures a colour-blind
# separation of 0.3, which is indistinguishable for deuteranopia.
SERIES_COLORS = ["#34D399", "#60A5FA", "#EF4444", "#FBBF24", "#F472B6"]


# Formats a figure for display, showing a dash where the value is undefined
def fmt(value, places=2, pct=False):
    if value is None or value != value:
        return "\u2014"
    if pct:
        value = round(value * 100) + 0.0  # collapses -0.0 so it prints as 0%
        return f"{value:.0f}%"
    value = round(value, places) + 0.0
    return f"{value:.{places}f}"


left, mid, right = st.columns([1, 6, 1])
#--------------------------------------------------------------#

with mid:
    st.markdown("# Correlations")
    st.markdown(
        "How two assets moved together — correlation, beta, and timing."
    )

    c1, c2 = st.columns([1, 2])

    with c1:
        ui_primary = st.selectbox(
            label="Primary asset",
            options=COMPARABLE,
            format_func=lambda t: f"{ASSET_SPECS[t]['display']} ({t})",
            key="correlations_primary",
        )

    primary_spec = get_spec(ui_primary)

    with c2:
        ui_compare = st.multiselect(
            label="Compare against (up to 5)",
            options=[t for t in COMPARABLE if t != ui_primary],
            format_func=lambda t: f"{ASSET_SPECS[t]['display']} ({t})",
            max_selections=5,
        )

    if not ui_compare:
        st.info("Pick at least one asset to compare against.")
        st.stop()

    # Date bounds are the overlap across every selected asset.
    try:
        bounds = [get_asset_date_bounds(t) for t in [ui_primary] + ui_compare]
    except ValueError:
        st.warning("No history available for one of these assets.")
        st.stop()
    except Exception:
        st.warning("Couldn't reach Yahoo Finance. Please try again in a minute.")
        st.stop()

    min_date = max(b[0] for b in bounds)
    max_date = min(b[1] for b in bounds)

    if min_date >= max_date:
        st.error("These assets have no overlapping price history.")
        st.stop()

    f1, f2, f3 = st.columns(3)

    with f1:
        freq_default = "W" if any(
            default_freq(primary_spec, get_spec(t)) == "W" for t in ui_compare
        ) else "D"

        ui_freq = st.segmented_control(
            label="Return frequency",
            options=["W", "D"],
            format_func=lambda f: {"W": "Weekly", "D": "Daily"}[f],
            default=freq_default,
        )

    with f2:
        ui_start = st.date_input(
            "From", value=min_date, min_value=min_date, max_value=max_date
        )

    with f3:
        ui_end = st.date_input(
            "To", value=max_date, min_value=min_date, max_value=max_date
        )

    if freq_default == "W":
        st.caption(
            "These assets trade on markets that close at different times, so a "
            "same-day comparison can describe slightly different windows. Weekly "
            "reduces that. Correlation genuinely differs by horizon \u2014 it is "
            "worth looking at both."
        )

    run = st.button("Run comparison", type="primary")

    if run:
        st.session_state.pop("correlations_result", None)

        frames, failed = {}, []
        for t in [ui_primary] + ui_compare:
            try:
                with st.spinner(f"Fetching {t}..."):
                    raw = fetch_asset(t, ui_start, ui_end + timedelta(days=1))
            except Exception:
                failed.append(t)
                continue

            spec = get_spec(t)
            health = tick_inspector(raw, spec)
            if not health["is_healthy"]:
                failed.append(t)
                continue

            frames[t] = quant_analyzer(raw, t, spec)

        if ui_primary in failed or len(frames) < 2:
            st.error(
                "Couldn't build a clean comparison from these assets. "
                "Try a different selection or a shorter period."
            )
            st.stop()

        # Both frequencies are computed on every run. Prices are already
        # fetched by this point, so the second pass costs nothing in network
        # terms, and it lets the toggle switch view without refetching and the
        # two figures be compared against each other.
        pairs = {}
        for t in ui_compare:
            if t not in frames:
                continue

            win = {"W": WINDOW_W, "D": daily_window(primary_spec, get_spec(t))}
            entry = {"window": win}
            for f in ("W", "D"):
                aligned = align_pair(frames[ui_primary], frames[t], f)
                entry[f] = pair_analyzer(aligned, win[f]) if len(aligned) >= win[f] else None

            if entry["W"] is None and entry["D"] is None:
                failed.append(t)
                continue

            pairs[t] = entry

        st.session_state["correlations_result"] = {
            "primary": ui_primary,
            "order": list(ui_compare),
            "pairs": pairs,
            "failed": failed,
        }

    result = st.session_state.get("correlations_result")

    if result:
        primary = result["primary"]
        primary_name = ASSET_SPECS[primary]["display"]
        pairs = result["pairs"]

        # The live toggle drives the view, so changing frequency re-renders from
        # what is already stored rather than running the comparison again.
        # st.segmented_control returns None when the user deselects the active
        # option, so fall back rather than rendering with view set to None
        view = ui_freq or freq_default
        period = "weeks" if view == "W" else "days"
        freq_word = "weekly" if view == "W" else "daily"

        # colour follows the asset, in the order it was selected, so dropping one
        # comparison does not repaint the others
        color_of = {t: SERIES_COLORS[i % len(SERIES_COLORS)]
                    for i, t in enumerate(result["order"])}

        rows = [(t, p[view]) for t, p in pairs.items()
                if p.get(view) and p[view]["full_corr"] == p[view]["full_corr"]]
        rows.sort(key=lambda kv: abs(kv[1]["full_corr"]), reverse=True)

        if not rows:
            st.warning(
                f"There is not enough shared history to compute {freq_word} figures "
                f"over this period. A rolling window needs a full year of overlapping "
                f"data. Try a longer date range, or the other frequency."
            )
        else:
            top_t, top = rows[0]
            top_name = ASSET_SPECS[top_t]["display"]

            # ---- the statement, in plain language, before any numbers table ----
            # The lead makes a claim about direction agreement, so it ranks on that
            # rather than on correlation. With several comparison assets the two
            # orderings disagree, and quoting one while ranking by the other
            # contradicts the table directly below it.
            by_dir = sorted(
                (r for r in rows
                 if r[1]["same_direction_pct"] == r[1]["same_direction_pct"]),
                key=lambda kv: kv[1]["same_direction_pct"],
                reverse=True,
            )
            dir_t, dir_m = by_dir[0] if by_dir else (top_t, top)

            lead = (
                f"Over **{dir_m['n_obs']:,} {period}**, {primary_name} moved in the same "
                f"direction as **{ASSET_SPECS[dir_t]['display']}** in "
                f"**{fmt(dir_m['same_direction_pct'], pct=True)}** of them"
            )
            if len(by_dir) > 1:
                low_t, low_m = by_dir[-1]
                lead += (
                    f" — more often than any other asset here. "
                    f"**{ASSET_SPECS[low_t]['display']}** came closest to moving "
                    f"independently, at **{fmt(low_m['same_direction_pct'], pct=True)}**."
                )
            else:
                lead += "."

            st.markdown(lead)
            st.markdown(
                f"The strongest relationship, **{top_name}**, lines up with about "
                f"**{fmt(top['r_squared'], pct=True)}** of {primary_name}'s {freq_word} "
                f"movement over this period. The rest came from somewhere else."
            )

            # ---- the table ----
            st.dataframe(
                pd.DataFrame([{
                    "Asset": ASSET_SPECS[t]["display"],
                    "Correlation": fmt(m["full_corr"]),
                    "Beta": fmt(m["full_beta"]),
                    "R²": fmt(m["r_squared"], pct=True),
                    "Same direction": fmt(m["same_direction_pct"], pct=True),
                    period.capitalize(): f"{m['n_obs']:,}",
                } for t, m in rows]),
                hide_index=True,
                width="stretch",
            )

            st.caption(
                f"Beta is the slope of {primary_name} against that asset — how far it "
                f"moved, on average, per 1% move in the other. It is not a market beta. "
                f"R² is correlation squared: the same measurement read as a share of "
                f"movement, not a second finding."
            )

            # ---- the same pair at the other frequency, which usually differs ----
            other = "D" if view == "W" else "W"
            other_word = "daily" if view == "W" else "weekly"
            other_m = pairs[top_t].get(other)
            if other_m and other_m["full_corr"] == other_m["full_corr"]:
                st.caption(
                    f"Measured on {other_word} returns instead, {top_name} reads "
                    f"**{fmt(other_m['full_corr'])}** rather than {fmt(top['full_corr'])}. "
                    f"Correlation depends on the period you measure it over — see "
                    f"*How this is calculated* below."
                )

            # ---- the rolling chart ----
            if view == "W":
                win_phrase = f"{WINDOW_W}-week window, one year"
            else:
                wins = sorted({pairs[t]["window"]["D"] for t, _ in rows})
                if len(wins) == 1:
                    win_phrase = f"{wins[0]}-day window, one year"
                else:
                    win_phrase = (
                        "One-year window \u2014 "
                        + " and ".join(f"{w} days" for w in wins)
                        + ", depending on how many days a pair's two markets both trade"
                    )

            st.markdown(f"#### Each asset's rolling correlation with {primary_name}")
            st.caption(
                f"{win_phrase}. "
                f"{primary_name} is the baseline, so it has no line of its own — every "
                f"line already measures one asset against it. The three strongest are "
                f"drawn; click a name in the legend to add or remove it."
            )

            fig = go.Figure()

            # the band inside which a relationship is weak enough to be mostly noise
            fig.add_hrect(y0=-0.3, y1=0.3, line_width=0,
                          fillcolor="#9498A0", opacity=0.07, layer="below")

            for i, (t, m) in enumerate(rows):
                series = m["rolling_corr"].dropna()
                if series.empty:
                    continue
                fig.add_trace(go.Scatter(
                    x=series.index,
                    y=series,
                    mode="lines",
                    name=ASSET_SPECS[t]["display"],
                    line=dict(color=color_of.get(t, "#9498A0"), width=1.5),
                    visible=True if i < 3 else "legendonly",
                    hovertemplate="%{y:.2f}<extra>%{fullData.name}</extra>",
                ))

            fig.update_yaxes(range=[-1, 1], title_text="Correlation",
                             zeroline=True, zerolinecolor="#282828")
            fig.update_layout(hovermode="x unified")

            st.plotly_chart(style_fig(fig, height=420), width="stretch")
            st.caption(
                "The shaded band marks ±0.3. Inside it, the relationship is weak "
                "enough that it is mostly noise."
            )

            # ---- lead and lag, always on daily returns ----
            lag_rows = [(t, pairs[t]["D"]) for t, _ in rows
                        if pairs[t].get("D")
                        and get_spec(t)["market"] != get_spec(primary)["market"]
                        and pairs[t]["D"]["corr_same"] == pairs[t]["D"]["corr_same"]]

            if lag_rows:
                st.markdown("#### Lead and lag")
                st.caption(
                    "Measured on daily returns, where timing differences are visible. "
                    "Weekly returns are too coarse to separate a lead from a lag. Only "
                    "assets trading on a different market from "
                    f"{primary_name} are shown."
                )
                st.dataframe(
                    pd.DataFrame([{
                        "Asset": ASSET_SPECS[t]["display"],
                        "Asset moved first": fmt(m["corr_b_leads"]),
                        "Same day": fmt(m["corr_same"]),
                        f"{primary_name} moved first": fmt(m["corr_a_leads"]),
                    } for t, m in lag_rows]),
                    hide_index=True,
                    width="stretch",
                )

            # ---- methodology ----
            with st.expander("How this is calculated"):
                st.markdown(
                    "- Returns come from closing prices on the days **both** assets "
                    "traded. A move on a day only one of them traded is compounded "
                    "into its next shared observation, so nothing is discarded — a "
                    "Bitcoin weekend is carried into Monday.\n"
                    "- **Correlation depends on the period you measure it over**, and "
                    "the daily and weekly figures will usually differ. Two assets can "
                    "react to the same news on the same day and still end a week in "
                    "different places, if one partly unwinds that reaction or has "
                    "strong moves of its own. Over a longer window each asset's own "
                    "behaviour accumulates while a shared one-off reaction does not — "
                    "so the two numbers answer different questions rather than one "
                    "being more accurate. Use the daily figure to ask whether two "
                    "assets react to the same events, and the weekly figure to ask "
                    "whether they end up in the same place.\n"
                    "- Markets close at different times — the NSE at 10:00 UTC, the "
                    "NYSE at 21:00, Bitcoin's daily bar at 00:00 the next day — so two "
                    "same-day daily returns can describe different windows. The lead "
                    "and lag table shows whether that is happening for a given pair.\n"
                    f"- Rolling figures use a **{WINDOW_W}-week** window on weekly "
                    "returns. On daily returns the window is one year of shared "
                    "trading days, which depends on the pair: **365** when both "
                    "assets trade every day of the week, **252** as soon as an equity "
                    "is involved. A shorter window would be noisier \u2014 a "
                    "correlation measured from 26 observations carries roughly "
                    "\u00b10.4 of uncertainty, so a rolling line that short mostly "
                    "shows sampling noise rather than a changing relationship.\n"
                    "- Each pair keeps its own set of shared trading days, which is "
                    "why the observation counts differ by row.\n"
                    "- Correlation and beta are computed on returns in each asset's own "
                    "trading currency. No currency conversion is applied.\n"
                    "- A stablecoin holds a fixed value by design, so it has almost no "
                    "variation to measure. Correlation against it is undefined rather "
                    "than low, which is why stablecoins are not offered on this page.\n"
                    "- Prices are adjusted for splits and dividends. Today's session is "
                    "excluded because it has not finished."
                )

        if result["failed"]:
            names = ", ".join(ASSET_SPECS[t]["display"] for t in result["failed"])
            st.warning(
                f"Left out of the comparison: {names}. Either the price history "
                f"failed its integrity checks, or there were not enough shared "
                f"trading days to fill the rolling window."
            )

        st.caption("Historical measurements only. Not investment advice.")
#--------------------------------------------------------------#
#---------------------end-of-code------------------------------#