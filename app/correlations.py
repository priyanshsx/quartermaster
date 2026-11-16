#---------------------beginning-of-code------------------------#
#--------------------------------------------------------------#

# Imports libraries
import math
import time

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

        # failed maps a ticker to why it dropped out, so the message can say
        # something true rather than guessing at the cause
        frames, failed = {}, {}
        for t in [ui_primary] + ui_compare:
            raw = None
            for attempt in (1, 2):
                try:
                    with st.spinner(f"Fetching {t}..."):
                        raw = fetch_asset(t, ui_start, ui_end + timedelta(days=1))
                except ValueError as exc:
                    # the engine raises this when the range really holds no data
                    failed[t] = ("no_data", str(exc))
                    break
                except Exception:
                    # nearly always a Yahoo rate limit, which clears in a moment.
                    # Exceptions are never cached, so a second call does retry.
                    if attempt == 1:
                        time.sleep(1.5)
                        continue
                    failed[t] = ("unreachable", "")
                else:
                    break

            if raw is None:
                continue

            spec = get_spec(t)
            health = tick_inspector(raw, spec)
            if not health["is_healthy"]:
                failed[t] = ("integrity", "")
                continue

            frames[t] = quant_analyzer(raw, t, spec)

        if ui_primary in failed or len(frames) < 2:
            unreachable = [k for k, (why, _) in failed.items() if why == "unreachable"]
            if unreachable:
                names = ", ".join(ASSET_SPECS[k]["display"] for k in unreachable)
                st.error(
                    f"Couldn't reach Yahoo Finance for {names}. This is almost always "
                    f"a temporary rate limit rather than a problem with the assets \u2014 "
                    f"wait a few seconds and run it again."
                )
            else:
                detail = next((msg for _, msg in failed.values() if msg), "")
                st.error(
                    "Couldn't build a clean comparison from these assets. "
                    + (detail + " " if detail else "")
                    + "Try a different selection or a shorter period."
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
                failed[t] = ("window", "")
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
                f"{primary_name} and **{ASSET_SPECS[dir_t]['display']}** moved the same "
                f"way in **{fmt(dir_m['same_direction_pct'], pct=True)}** of "
                f"{dir_m['n_obs']:,} {period}"
            )
            if len(by_dir) > 1:
                low_t, low_m = by_dir[-1]
                lead += (
                    f", more often than any other asset here. "
                    f"**{ASSET_SPECS[low_t]['display']}** was the least aligned, at "
                    f"**{fmt(low_m['same_direction_pct'], pct=True)}**."
                )
            else:
                lead += "."

            # 50% is what two unrelated assets produce, so the figure above needs
            # that anchor or it means nothing to a reader
            lead += " Two assets with no relationship would land near 50%."

            # Says in words whether the coefficient is a lot or a little. The bands
            # are a convention rather than a law, and are stated in the methodology.
            def strength(r):
                size = abs(r)
                kind = "inverse " if r <= -0.2 else ""
                if size >= 0.7:
                    return f"a strong {kind}relationship"
                if size >= 0.4:
                    return f"a moderate {kind}relationship"
                if size >= 0.2:
                    return f"a weak {kind}relationship"
                return "close to no relationship at all"

            tail = " — and that is the closest pairing here." if len(rows) > 1 else "."
            st.markdown(
                f"At a correlation of **{fmt(top['full_corr'])}**, {primary_name} and "
                f"**{top_name}** show {strength(top['full_corr'])}{tail}"
            )
            st.markdown(lead)

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
                column_config={
                    "Correlation": st.column_config.TextColumn(help=(
                        "1.0 means the two moved the same way every period, 0 means "
                        "they moved independently, −1.0 means exactly opposite.")),
                    "Beta": st.column_config.TextColumn(help=(
                        f"How far {primary_name} moved, on average, for each 1% move "
                        f"in that asset. A slope between two assets, not a market "
                        f"beta.")),
                    "R²": st.column_config.TextColumn(help=(
                        "Correlation squared, read as a share of movement. The same "
                        "measurement in different units, not a second finding.")),
                    "Same direction": st.column_config.TextColumn(help=(
                        "The share of periods in which both assets moved the same "
                        "way. Two unrelated assets land near 50%.")),
                },
            )

            # ---- the same pair at the other frequency, which usually differs ----
            other = "D" if view == "W" else "W"
            other_word = "daily" if view == "W" else "weekly"
            other_m = pairs[top_t].get(other)
            if other_m and other_m["full_corr"] == other_m["full_corr"]:
                st.caption(
                    f"On {other_word} returns it reads **{fmt(other_m['full_corr'])}** "
                    f"rather than {fmt(top['full_corr'])}. Correlation depends on the "
                    f"period you measure over — *How this is calculated* explains why."
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

            if len(rows) == 1:
                chart_title = (f"{ASSET_SPECS[rows[0][0]]['display']}'s rolling "
                               f"correlation with {primary_name}")
            else:
                chart_title = f"Each asset's rolling correlation with {primary_name}"

            head, info = st.columns([14, 1], vertical_alignment="center")
            with head:
                st.markdown(f"#### {chart_title}")
            with info:
                with st.popover("ⓘ"):
                    st.markdown(
                        "A correlation of **1.0** means the two moved the same way in "
                        "every period, **0** means they moved independently, and "
                        "**−1.0** means they moved in exactly opposite directions."
                    )
                    if len(rows) > 1:
                        st.markdown(
                            f"Every line is one asset measured against {primary_name}, "
                            f"so {primary_name} has no line of its own — its "
                            f"correlation with itself would be a flat 1.0. The three "
                            f"strongest are drawn; click a name in the legend to add "
                            f"or remove it."
                        )
            st.caption(f"{win_phrase}.")

            fig = go.Figure()

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

            fig.update_yaxes(title_text="Correlation", range=[-1, 1],
                             tickvals=[-1, -0.5, 0, 0.5, 1], zeroline=False)

            # An emphasised zero line, and the scale said in words. There is
            # deliberately no shaded band: shading the middle reads as "this is the
            # normal zone", which made a correlation of zero look like agreement
            # rather than the absence of one.
            fig.add_hline(y=0, line_width=1, line_color="#4A4A4A")

            # The labels sit outside the plot area, so they can never run through
            # a line the way an inside annotation does.
            for y, label in ((1, "move together"),
                             (0, "no correlation at 0"),
                             (-1, "move opposite")):
                fig.add_annotation(
                    xref="paper", x=1.0, xanchor="left", xshift=10,
                    yref="y", y=y, yanchor="middle",
                    text=label, showarrow=False,
                    font=dict(size=11, color="#8A8F99"),
                )

            fig.update_layout(hovermode="x unified")
            fig = style_fig(fig, height=460)
            fig.update_layout(margin=dict(t=40, b=30, l=50, r=128))

            st.plotly_chart(fig, width="stretch")

            # ---- lead and lag, always on daily returns ----
            lag_rows = [(t, pairs[t]["D"]) for t, _ in rows
                        if pairs[t].get("D")
                        and get_spec(t)["market"] != get_spec(primary)["market"]
                        and pairs[t]["D"]["corr_same"] == pairs[t]["D"]["corr_same"]]

            if lag_rows:
                st.markdown("#### Timing")
                st.caption(
                    "Measured on daily returns, where timing differences show. Only "
                    f"assets trading on a different market from {primary_name} appear "
                    f"here."
                )

                # Three bare correlations do not tell a reader which one matters, so
                # every row carries a verdict. A term counts only if it clears the 95%
                # threshold for that many observations; below it, the figure is noise.
                def timing_verdict(m):
                    n = m["n_obs"]
                    threshold = 1.96 / math.sqrt(n - 3) if n > 4 else 1.0
                    terms = (
                        (m["corr_same"], "same"),
                        (m["corr_a_leads"], "primary"),
                        (m["corr_b_leads"], "asset"),
                    )
                    real = sorted(
                        ((v, k) for v, k in terms if v == v and v > threshold),
                        reverse=True,
                    )
                    if not real:
                        return "No clear timing pattern"

                    strongest, leader = real[0]
                    keys = [leader] + [k for v, k in real[1:] if v >= 0.7 * strongest]

                    if "primary" in keys:
                        if "same" in keys:
                            return f"Partly same day, partly a day after {primary_name}"
                        return f"Follows {primary_name} by a day"
                    if "asset" in keys:
                        if "same" in keys:
                            return f"Partly same day, partly a day before {primary_name}"
                        return f"Moves a day before {primary_name}"
                    return "Moves within the same day"

                st.dataframe(
                    pd.DataFrame([{
                        "Asset": ASSET_SPECS[t]["display"],
                        "What this means": timing_verdict(m),
                        "Asset moved first": fmt(m["corr_b_leads"]),
                        "Same day": fmt(m["corr_same"]),
                        f"{primary_name} moved first": fmt(m["corr_a_leads"]),
                    } for t, m in lag_rows]),
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "Asset moved first": st.column_config.TextColumn(help=(
                            f"How closely that asset's move on one day lines up with "
                            f"{primary_name}'s move the next day.")),
                        "Same day": st.column_config.TextColumn(help=(
                            "How closely the two moved on the same day.")),
                        f"{primary_name} moved first": st.column_config.TextColumn(help=(
                            f"How closely {primary_name}'s move on one day lines up "
                            f"with that asset's move the next day.")),
                    },
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
            dropped = result["failed"]
            unreachable = [k for k, (why, _) in dropped.items() if why == "unreachable"]
            other = [k for k, (why, _) in dropped.items() if why != "unreachable"]
            if unreachable:
                st.warning(
                    "Couldn't reach Yahoo Finance for "
                    + ", ".join(ASSET_SPECS[k]["display"] for k in unreachable)
                    + ". That is usually a temporary rate limit \u2014 run the "
                    "comparison again to include them."
                )
            if other:
                st.warning(
                    "Left out of the comparison: "
                    + ", ".join(ASSET_SPECS[k]["display"] for k in other)
                    + ". Either the price history failed its integrity checks, or "
                    "there were not enough shared trading days to fill the rolling "
                    "window."
                )

        st.caption("Historical measurements only. Not investment advice.")
#--------------------------------------------------------------#
#---------------------end-of-code------------------------------#