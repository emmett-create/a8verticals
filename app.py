"""
Agency 8 — Influencer Analytics (Streamlit Web App)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Agency 8 — Influencer Analytics", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid #333; }
.stTabs [data-baseweb="tab"] { padding: 8px 20px; border-radius: 6px 6px 0 0; font-weight: 500; color: #aaa; }
.stTabs [aria-selected="true"] { background-color: #1a1a2e; color: #fff; border-bottom: 2px solid #e84393; }
[data-testid="metric-container"] { background-color: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 16px; }
[data-testid="stExpander"] { border: 1px solid #1f2937; border-radius: 8px; margin-bottom: 8px; }
[data-testid="stButton"] button { border-radius: 8px; font-weight: 600; letter-spacing: 0.3px; }
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
h2, h3 { color: #f0f0f0; }
</style>
""", unsafe_allow_html=True)

# ── Branding ──────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='margin-bottom:0;'>Agency 8 "
    "<span style='color:#9b59b6;font-weight:800;'>·</span></h1>"
    "<p style='color:#888;font-size:1.1rem;margin-top:0;'>Influencer Analytics</p>",
    unsafe_allow_html=True,
)

# ── Status classifications (matches Agency 8 master list dropdowns) ───────────
# Not yet outreached
STATUS_NO_OUTREACH = {"no outreach yet", ""}

# Outreached but not yet replied/active
STATUS_OUTREACHED_ONLY = {
    "initial outreach", "follow up #1", "emailed", "follow up on email",
    "sent form", "followed up to fill", "follow up to fill #2",
}

# Replied / actively progressing through the gifting pipeline
STATUS_ACTIVE = {
    "order confirmed", "sent guides", "shipped", "delivered",
    "follow up on delivered", "follow up to post", "follow up to post #2",
    "follow up after posted",
}

# Actually posted
STATUS_POSTED = {"posted"}

# Dead / declined
STATUS_DEAD = {"not interested", "wants paid", "abroad", "existing"}

# Combined sets for funnel stages
STATUS_ALL_OUTREACHED = STATUS_OUTREACHED_ONLY | STATUS_ACTIVE | STATUS_POSTED | STATUS_DEAD
STATUS_ALL_ACTIVE_PLUS = STATUS_ACTIVE | STATUS_POSTED

# ── Constants ─────────────────────────────────────────────────────────────────
SHOPIFY_COLOR = "#9b59b6"
PALETTE = ["#4a90d9", "#9b59b6", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4", "#ec4899", "#84cc16"]
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#f0f0f0"),
    margin=dict(l=20, r=20, t=40, b=20),
)

TIER_ORDER = ["Nano", "Micro", "Mid-tier", "Macro", "Mega"]
TIER_COLORS = {
    "Nano": "#4a90d9",
    "Micro": "#22c55e",
    "Mid-tier": "#f59e0b",
    "Macro": "#9b59b6",
    "Mega": "#ef4444",
}


def assign_tier(followers):
    """Assign a follower tier label based on follower count."""
    if pd.isna(followers):
        return "Unknown"
    f = float(followers)
    if f < 10_000:
        return "Nano"
    if f < 50_000:
        return "Micro"
    if f < 250_000:
        return "Mid-tier"
    if f < 1_000_000:
        return "Macro"
    return "Mega"


# ── Column auto-detection ─────────────────────────────────────────────────────
COLUMN_HINTS = {
    "name":          ["name"],
    "vertical":      ["vertical"],
    "platform":      ["primary platform", "platform"],
    "followers":     ["followers on primary", "followers"],
    "engagement":    ["engagement rate", "engagement"],
    "posts_90":      ["posts last 90", "posts 90", "posts_90", "post count"],
    "emv":           ["est. emv", "emv", "estimated emv"],
    "gender":        ["gender"],
    "status":        ["status"],
    "inbound":       ["inbound"],
    "campaign":      ["campaign"],
    "outreach_date": ["outreach date", "outreach_date", "date outreached"],
    "reply_date":    ["response date", "reply date", "reply_date", "date replied", "responded"],
    "ig_handle":     ["clean ig handle", "ig handle", "instagram handle"],
    "tt_handle":     ["clean tt handle", "tiktok handle", "tt handle"],
}

COLUMN_LABELS = {
    "name":          "Name",
    "vertical":      "Vertical",
    "platform":      "Primary Platform",
    "followers":     "Followers on Primary Platform",
    "engagement":    "Engagement Rate",
    "posts_90":      "Posts Last 90 Days",
    "emv":           "Est. EMV",
    "gender":        "Gender",
    "status":        "Status",
    "inbound":       "Inbound?",
    "campaign":      "Campaign",
    "outreach_date": "Outreach Date",
    "reply_date":    "Response Date",
    "ig_handle":     "Clean IG Handle",
    "tt_handle":     "Clean TT Handle",
}


def auto_detect_columns(df_columns):
    """Return a dict mapping field_key -> detected column name (or empty string)."""
    cols_lower = {c.lower(): c for c in df_columns}
    detected = {}
    for field, hints in COLUMN_HINTS.items():
        found = ""
        for hint in hints:
            for col_lower, col_orig in cols_lower.items():
                if hint in col_lower:
                    found = col_orig
                    break
            if found:
                break
        detected[field] = found
    return detected


def safe_numeric(series):
    """Strip $ % commas then coerce to float."""
    return pd.to_numeric(
        series.astype(str).str.replace(r"[$,%]", "", regex=True).str.strip(),
        errors="coerce",
    )


def fmt_number(n, decimals=0):
    """Format large numbers with K/M suffixes."""
    if pd.isna(n):
        return "—"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{n:,.{decimals}f}"


def fmt_currency(n):
    if pd.isna(n):
        return "—"
    if n >= 1_000_000:
        return f"${n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"${n/1_000:.1f}K"
    return f"${n:,.0f}"


# ── Chart helpers ─────────────────────────────────────────────────────────────
def apply_dark_layout(fig, title=""):
    fig.update_layout(**CHART_LAYOUT, title=title)
    fig.update_xaxes(gridcolor="#1f2937", zerolinecolor="#1f2937")
    fig.update_yaxes(gridcolor="#1f2937", zerolinecolor="#1f2937")
    return fig


# ── File uploader ─────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader("Upload master list CSV", type=["csv"])

if uploaded_file is None:
    st.info("Upload a master list CSV to get started.")
    st.stop()

# ── Read CSV ──────────────────────────────────────────────────────────────────
try:
    raw_df = pd.read_csv(uploaded_file, dtype=str)
except Exception as e:
    st.error(f"Could not read CSV: {e}")
    st.stop()

if raw_df.empty:
    st.error("The uploaded CSV appears to be empty.")
    st.stop()

# Strip whitespace from column names
raw_df.columns = raw_df.columns.str.strip()

# ── Column mapping expander ───────────────────────────────────────────────────
detected = auto_detect_columns(raw_df.columns.tolist())
all_cols = [""] + raw_df.columns.tolist()

with st.expander("Column Mapping (auto-detected — adjust if needed)", expanded=False):
    mapping = {}
    cols_ui = st.columns(3)
    field_keys = list(COLUMN_HINTS.keys())
    for i, field in enumerate(field_keys):
        with cols_ui[i % 3]:
            default_idx = all_cols.index(detected[field]) if detected[field] in all_cols else 0
            mapping[field] = st.selectbox(
                COLUMN_LABELS[field],
                options=all_cols,
                index=default_idx,
                key=f"map_{field}",
            )

if st.button("Analyze", type="primary"):
    st.session_state["analyzed"] = True

if not st.session_state.get("analyzed"):
    st.info("Click **Analyze** to generate the report.")
    st.stop()

# ── Build working dataframe ───────────────────────────────────────────────────
df = raw_df.copy()

def get_col(field):
    """Return mapped column name or None."""
    return mapping.get(field) or None


def col_series(field):
    """Return the series for a mapped field, or an empty series."""
    c = get_col(field)
    if c and c in df.columns:
        return df[c]
    return pd.Series([pd.NA] * len(df), index=df.index)


# Convert numeric columns
for num_field in ["followers", "engagement", "posts_90", "emv"]:
    c = get_col(num_field)
    if c and c in df.columns:
        df[c] = safe_numeric(df[c])

# Assign follower tiers
followers_col = get_col("followers")
if followers_col:
    df["_tier"] = df[followers_col].apply(assign_tier)
else:
    df["_tier"] = "Unknown"

# Parse dates
for date_field in ["outreach_date", "reply_date"]:
    c = get_col(date_field)
    if c and c in df.columns:
        df[c] = pd.to_datetime(df[c], errors="coerce")

# Compute days_to_reply
outreach_col = get_col("outreach_date")
reply_col = get_col("reply_date")
if outreach_col and reply_col and outreach_col in df.columns and reply_col in df.columns:
    df["_days_to_reply"] = (df[reply_col] - df[outreach_col]).dt.days
else:
    df["_days_to_reply"] = pd.NA

vertical_col = get_col("vertical")
platform_col = get_col("platform")
followers_col = get_col("followers")
engagement_col = get_col("engagement")
posts_col = get_col("posts_90")
emv_col = get_col("emv")
gender_col = get_col("gender")
status_col = get_col("status")
inbound_col = get_col("inbound")
campaign_col = get_col("campaign")
name_col = get_col("name")
ig_col = get_col("ig_handle")
tt_col = get_col("tt_handle")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Overview",
    "Vertical Deep Dive",
    "Follower Tier Analysis",
    "Outreach Effectiveness",
    "Campaign Analysis",
    "Creator Roster",
])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### Overview")

    total = len(df)
    n_verticals = df[vertical_col].nunique() if vertical_col else 0
    avg_followers = df[followers_col].mean() if followers_col else None
    avg_eng = df[engagement_col].mean() if engagement_col else None
    total_emv = df[emv_col].sum() if emv_col else None

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Influencers", f"{total:,}")
    c2.metric("Total Verticals", f"{n_verticals}")
    c3.metric("Avg Followers", fmt_number(avg_followers))
    c4.metric("Avg Engagement Rate", f"{avg_eng:.2f}%" if avg_eng is not None and not np.isnan(avg_eng) else "—")
    c5.metric("Total Est. EMV", fmt_currency(total_emv))

    st.markdown("---")

    col_l, col_r = st.columns(2)

    # Left: influencer count per vertical
    with col_l:
        if vertical_col:
            vc = df[vertical_col].dropna().value_counts().reset_index()
            vc.columns = ["Vertical", "Count"]
            vc = vc.sort_values("Count")
            fig = go.Figure(go.Bar(
                x=vc["Count"], y=vc["Vertical"],
                orientation="h",
                marker_color=SHOPIFY_COLOR,
                text=vc["Count"],
                textposition="outside",
            ))
            apply_dark_layout(fig, "Influencers by Vertical")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No Vertical column mapped.")

    # Right: platform split
    with col_r:
        if platform_col:
            pc = df[platform_col].dropna().value_counts()
            fig = go.Figure(go.Pie(
                labels=pc.index,
                values=pc.values,
                hole=0.45,
                marker=dict(colors=PALETTE[:len(pc)]),
                textinfo="label+percent",
            ))
            apply_dark_layout(fig, "Platform Split")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No Platform column mapped.")

    # Avg engagement per vertical
    if vertical_col and engagement_col:
        eng_v = (
            df[[vertical_col, engagement_col]]
            .dropna()
            .groupby(vertical_col)[engagement_col]
            .mean()
            .reset_index()
            .sort_values(engagement_col)
        )
        eng_v.columns = ["Vertical", "Avg Engagement Rate"]
        fig = go.Figure(go.Bar(
            x=eng_v["Avg Engagement Rate"],
            y=eng_v["Vertical"],
            orientation="h",
            marker_color="#4a90d9",
            text=eng_v["Avg Engagement Rate"].map(lambda x: f"{x:.2f}%"),
            textposition="outside",
        ))
        apply_dark_layout(fig, "Avg Engagement Rate by Vertical")
        st.plotly_chart(fig, use_container_width=True)
    else:
        if not vertical_col or not engagement_col:
            st.info("Map Vertical and Engagement Rate columns to see engagement by vertical.")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — VERTICAL DEEP DIVE
# ═════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Vertical Deep Dive")

    if not vertical_col:
        st.warning("No Vertical column mapped. Please check column mapping.")
    else:
        verticals = sorted(df[vertical_col].dropna().unique().tolist())
        if not verticals:
            st.info("No vertical data found.")
        else:
            selected_v = st.selectbox("Select a Vertical", verticals)
            vdf = df[df[vertical_col] == selected_v].copy()

            count_v = len(vdf)
            avg_fol_v = vdf[followers_col].mean() if followers_col else None
            avg_eng_v = vdf[engagement_col].mean() if engagement_col else None
            avg_emv_v = vdf[emv_col].mean() if emv_col else None
            total_posts_v = vdf[posts_col].sum() if posts_col else None

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Influencers", f"{count_v:,}")
            c2.metric("Avg Followers", fmt_number(avg_fol_v))
            c3.metric("Avg Engagement", f"{avg_eng_v:.2f}%" if avg_eng_v is not None and not np.isnan(avg_eng_v) else "—")
            c4.metric("Avg EMV", fmt_currency(avg_emv_v))
            c5.metric("Total Posts (90d)", f"{int(total_posts_v):,}" if total_posts_v is not None and not np.isnan(total_posts_v) else "—")

            st.markdown("---")
            row1_l, row1_r = st.columns(2)

            # Tier breakdown
            with row1_l:
                tier_counts = vdf["_tier"].value_counts().reindex(TIER_ORDER, fill_value=0).reset_index()
                tier_counts.columns = ["Tier", "Count"]
                fig = go.Figure(go.Bar(
                    x=tier_counts["Tier"],
                    y=tier_counts["Count"],
                    marker_color=[TIER_COLORS.get(t, SHOPIFY_COLOR) for t in tier_counts["Tier"]],
                    text=tier_counts["Count"],
                    textposition="outside",
                ))
                apply_dark_layout(fig, "Follower Tier Breakdown")
                st.plotly_chart(fig, use_container_width=True)

            # Platform split
            with row1_r:
                if platform_col:
                    pc_v = vdf[platform_col].dropna().value_counts()
                    if not pc_v.empty:
                        fig = go.Figure(go.Pie(
                            labels=pc_v.index,
                            values=pc_v.values,
                            hole=0.45,
                            marker=dict(colors=PALETTE[:len(pc_v)]),
                            textinfo="label+percent",
                        ))
                        apply_dark_layout(fig, "Platform Split")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No platform data for this vertical.")
                else:
                    st.info("No Platform column mapped.")

            # Gender split
            if gender_col:
                gc_v = vdf[gender_col].dropna().value_counts()
                if not gc_v.empty:
                    fig = go.Figure(go.Pie(
                        labels=gc_v.index,
                        values=gc_v.values,
                        hole=0.45,
                        marker=dict(colors=PALETTE[:len(gc_v)]),
                        textinfo="label+percent",
                    ))
                    apply_dark_layout(fig, "Gender Split")
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No Gender column mapped.")

            # Top influencers by followers
            st.markdown("#### Top 10 Influencers by Followers")
            show_cols = [c for c in [name_col, platform_col, followers_col, status_col] if c]
            top10 = vdf[show_cols].copy() if show_cols else vdf.copy()
            if followers_col and followers_col in top10.columns:
                top10 = top10.sort_values(followers_col, ascending=False)
            top10 = top10.head(10)
            display_top10 = top10.copy()
            if followers_col and followers_col in display_top10.columns:
                display_top10[followers_col] = display_top10[followers_col].apply(fmt_number)
            st.dataframe(display_top10, hide_index=True, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — FOLLOWER TIER ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### Follower Tier Analysis")

    # Tier filter
    available_tiers = [t for t in TIER_ORDER if t in df["_tier"].values]
    selected_tiers = st.multiselect(
        "Filter by Tier", options=available_tiers, default=available_tiers, key="tier_filter"
    )
    tier_df = df[df["_tier"].isin(selected_tiers)] if selected_tiers else df.copy()

    has_outreach_col = bool(outreach_col and outreach_col in df.columns)
    has_reply_col = bool(reply_col and reply_col in df.columns)
    has_status_col = bool(status_col and status_col in df.columns)

    # Helper: compute rates for a sub-dataframe
    def compute_tier_rates(tdf):
        count_t = len(tdf)
        avg_fol_t = tdf[followers_col].mean() if followers_col and count_t > 0 else None
        top_vert = (
            tdf[vertical_col].value_counts().index[0]
            if vertical_col and count_t > 0 and not tdf[vertical_col].dropna().empty
            else "—"
        )
        # Outreached = has an outreach date
        outreached = tdf[outreach_col].notna().sum() if has_outreach_col else None
        # Responded = has a response date
        responded = tdf[reply_col].notna().sum() if has_reply_col else None
        # Posted = POSTED status
        if has_status_col:
            s = tdf[status_col].astype(str).str.strip().str.lower()
            posted = s.isin(STATUS_POSTED).sum()
        else:
            posted = None

        outreached_n = int(outreached) if outreached is not None else 0
        responded_n = int(responded) if responded is not None else 0
        posted_n = int(posted) if posted is not None else 0
        resp_rate = (responded_n / outreached_n * 100) if outreached_n > 0 else None
        post_rate = (posted_n / responded_n * 100) if responded_n > 0 else None

        return {
            "Count": count_t,
            "Avg Followers": fmt_number(avg_fol_t),
            "Outreached": outreached_n if has_outreach_col else "—",
            "Responded": responded_n if has_reply_col else "—",
            "Posted": posted_n if has_status_col else "—",
            "Response Rate": f"{resp_rate:.1f}%" if resp_rate is not None else "—",
            "Post Rate (of responded)": f"{post_rate:.1f}%" if post_rate is not None else "—",
            "Top Vertical": top_vert,
            "_resp_rate": resp_rate,
            "_post_rate": post_rate,
        }

    # Build summary table
    tier_data = []
    for tier in TIER_ORDER:
        if tier not in selected_tiers:
            continue
        tdf = tier_df[tier_df["_tier"] == tier]
        row = {"Tier": tier, **compute_tier_rates(tdf)}
        tier_data.append(row)

    tier_summary_df = pd.DataFrame(tier_data) if tier_data else pd.DataFrame()

    # Metric cards
    if not tier_summary_df.empty:
        card_cols = st.columns(len(tier_summary_df))
        for i, (_, row) in enumerate(tier_summary_df.iterrows()):
            with card_cols[i]:
                st.metric(
                    row["Tier"],
                    f"{row['Count']:,}",
                    help=f"Response Rate: {row['Response Rate']} | Post Rate: {row['Post Rate (of responded)']}"
                )

    st.markdown("---")

    col_a, col_b = st.columns(2)

    # Response rate by tier (bar)
    with col_a:
        if not tier_summary_df.empty:
            rate_chart = tier_summary_df[["Tier", "_resp_rate", "_post_rate"]].dropna(subset=["_resp_rate"])
            if not rate_chart.empty:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    name="Response Rate",
                    x=rate_chart["Tier"],
                    y=rate_chart["_resp_rate"],
                    marker_color="#4a90d9",
                    text=rate_chart["_resp_rate"].map(lambda x: f"{x:.1f}%"),
                    textposition="outside",
                ))
                if "_post_rate" in rate_chart.columns:
                    rate_chart2 = tier_summary_df[["Tier", "_post_rate"]].dropna(subset=["_post_rate"])
                    fig.add_trace(go.Bar(
                        name="Post Rate (of responded)",
                        x=rate_chart2["Tier"],
                        y=rate_chart2["_post_rate"],
                        marker_color="#22c55e",
                        text=rate_chart2["_post_rate"].map(lambda x: f"{x:.1f}%"),
                        textposition="outside",
                    ))
                fig.update_layout(barmode="group", **CHART_LAYOUT, title="Response & Post Rate by Tier")
                fig.update_xaxes(gridcolor="#1f2937")
                fig.update_yaxes(gridcolor="#1f2937", ticksuffix="%")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No outreach date data available.")
        else:
            st.info("No tiers selected.")

    # Vertical distribution across selected tiers (stacked bar)
    with col_b:
        if vertical_col and not tier_df.empty:
            pivot = (
                tier_df.groupby([vertical_col, "_tier"])
                .size()
                .unstack(fill_value=0)
            )
            for t in selected_tiers:
                if t not in pivot.columns:
                    pivot[t] = 0
            pivot = pivot[[t for t in TIER_ORDER if t in pivot.columns]]
            fig = go.Figure()
            for tier in pivot.columns:
                fig.add_trace(go.Bar(
                    name=tier,
                    x=pivot.index,
                    y=pivot[tier],
                    marker_color=TIER_COLORS.get(tier, SHOPIFY_COLOR),
                ))
            fig.update_layout(barmode="stack", **CHART_LAYOUT, title="Vertical × Tier Distribution")
            fig.update_xaxes(gridcolor="#1f2937", tickangle=-30)
            fig.update_yaxes(gridcolor="#1f2937")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No Vertical column mapped.")

    # Summary table
    if not tier_summary_df.empty:
        st.markdown("#### Tier Summary")
        display_summary = tier_summary_df.drop(columns=["_resp_rate", "_post_rate"], errors="ignore")
        st.dataframe(display_summary, hide_index=True, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — OUTREACH EFFECTIVENESS
# ═════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### Outreach Effectiveness")

    has_status = bool(status_col and status_col in df.columns)
    has_outreach = bool(outreach_col and outreach_col in df.columns)
    has_reply = bool(reply_col and reply_col in df.columns)
    has_inbound = bool(inbound_col and inbound_col in df.columns)
    has_vertical = bool(vertical_col and vertical_col in df.columns)

    if not has_status and not has_outreach:
        st.info("Map Status and/or Outreach Date columns to see outreach metrics.")
    else:
        # ── Funnel by vertical ────────────────────────────────────────────────
        if has_status and has_vertical:
            st.markdown("#### Pipeline Funnel by Vertical")

            # Normalize status for comparison
            status_series = df[status_col].astype(str).str.strip().str.lower()

            def stage_count(vdf_local, stage):
                s = vdf_local[status_col].astype(str).str.strip().str.lower()
                if stage == "total":
                    return len(vdf_local)
                if stage == "outreached":
                    return s.isin(STATUS_ALL_OUTREACHED).sum()
                if stage == "active":
                    return s.isin(STATUS_ALL_ACTIVE_PLUS).sum()
                if stage == "posted":
                    return s.isin(STATUS_POSTED).sum()
                return 0

            funnel_rows = []
            for v in sorted(df[vertical_col].dropna().unique()):
                vdf_local = df[df[vertical_col] == v]
                total_f = stage_count(vdf_local, "total")
                outreached = stage_count(vdf_local, "outreached")
                active = stage_count(vdf_local, "active")
                posted = stage_count(vdf_local, "posted")
                funnel_rows.append({
                    "Vertical": v,
                    "Total": total_f,
                    "Outreached": outreached,
                    "Active/Gifted": active,
                    "Posted": posted,
                    "Outreach Rate": f"{(outreached/total_f*100):.0f}%" if total_f > 0 else "—",
                    "Post Rate": f"{(posted/outreached*100):.0f}%" if outreached > 0 else "—",
                })

            funnel_df = pd.DataFrame(funnel_rows)
            st.dataframe(funnel_df, hide_index=True, use_container_width=True)

            # Funnel chart (grouped bars)
            fig = go.Figure()
            stages = ["Total", "Outreached", "Active/Gifted", "Posted"]
            stage_colors = ["#4a90d9", "#9b59b6", "#22c55e", "#f59e0b"]
            for s, color in zip(stages, stage_colors):
                fig.add_trace(go.Bar(
                    name=s,
                    x=funnel_df["Vertical"],
                    y=funnel_df[s],
                    marker_color=color,
                ))
            fig.update_layout(barmode="group", **CHART_LAYOUT, title="Pipeline Stages by Vertical")
            fig.update_xaxes(gridcolor="#1f2937", tickangle=-30)
            fig.update_yaxes(gridcolor="#1f2937")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # ── Reply rate by follower tier ───────────────────────────────────────
        if has_status:
            st.markdown("#### Posted Rate by Follower Tier")
            status_norm = df[status_col].astype(str).str.strip().str.lower()
            df["_replied"] = status_norm.isin(STATUS_POSTED).astype(int)
            df["_outreached"] = status_norm.isin(STATUS_ALL_OUTREACHED).astype(int)

            tier_reply = (
                df[df["_outreached"] == 1]
                .groupby("_tier")["_replied"]
                .agg(["sum", "count"])
                .reindex(TIER_ORDER)
                .reset_index()
            )
            tier_reply.columns = ["Tier", "Posted", "Outreached"]
            tier_reply["Post Rate %"] = (tier_reply["Posted"] / tier_reply["Outreached"] * 100).round(1)
            tier_reply = tier_reply.dropna(subset=["Post Rate %"])

            if not tier_reply.empty:
                fig = go.Figure(go.Bar(
                    x=tier_reply["Tier"],
                    y=tier_reply["Post Rate %"],
                    marker_color=[TIER_COLORS.get(t, SHOPIFY_COLOR) for t in tier_reply["Tier"]],
                    text=tier_reply["Post Rate %"].map(lambda x: f"{x:.1f}%"),
                    textposition="outside",
                ))
                apply_dark_layout(fig, "Post Rate by Follower Tier")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Not enough data to calculate reply rates by tier.")

        st.markdown("---")

        # ── Time to reply ─────────────────────────────────────────────────────
        if has_outreach and has_reply and "_days_to_reply" in df.columns:
            st.markdown("#### Time to Reply")
            valid_reply_df = df[df["_days_to_reply"].notna() & (df["_days_to_reply"] >= 0)]

            col_dtr_l, col_dtr_r = st.columns(2)

            with col_dtr_l:
                if has_vertical and not valid_reply_df.empty:
                    dtr_vert = (
                        valid_reply_df.groupby(vertical_col)["_days_to_reply"]
                        .mean()
                        .reset_index()
                        .sort_values("_days_to_reply")
                    )
                    dtr_vert.columns = ["Vertical", "Avg Days to Reply"]
                    fig = go.Figure(go.Bar(
                        x=dtr_vert["Avg Days to Reply"],
                        y=dtr_vert["Vertical"],
                        orientation="h",
                        marker_color=SHOPIFY_COLOR,
                        text=dtr_vert["Avg Days to Reply"].map(lambda x: f"{x:.1f}d"),
                        textposition="outside",
                    ))
                    apply_dark_layout(fig, "Avg Days to Reply by Vertical")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No reply date data available for verticals.")

            with col_dtr_r:
                if not valid_reply_df.empty:
                    dtr_tier = (
                        valid_reply_df.groupby("_tier")["_days_to_reply"]
                        .mean()
                        .reindex(TIER_ORDER)
                        .reset_index()
                        .dropna()
                    )
                    dtr_tier.columns = ["Tier", "Avg Days to Reply"]
                    fig = go.Figure(go.Bar(
                        x=dtr_tier["Tier"],
                        y=dtr_tier["Avg Days to Reply"],
                        marker_color=[TIER_COLORS.get(t, SHOPIFY_COLOR) for t in dtr_tier["Tier"]],
                        text=dtr_tier["Avg Days to Reply"].map(lambda x: f"{x:.1f}d"),
                        textposition="outside",
                    ))
                    apply_dark_layout(fig, "Avg Days to Reply by Tier")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No reply date data available for tiers.")

        st.markdown("---")

        # ── Inbound vs Outreach ───────────────────────────────────────────────
        if has_inbound and has_vertical:
            st.markdown("#### Inbound vs. Outreach by Vertical")
            inbound_v = (
                df[[vertical_col, inbound_col]]
                .dropna(subset=[vertical_col])
                .copy()
            )
            inbound_v[inbound_col] = inbound_v[inbound_col].astype(str).str.strip().str.lower()
            inbound_v["_is_inbound"] = inbound_v[inbound_col].isin(["yes", "y", "true", "1", "x"])
            inbound_agg = (
                inbound_v.groupby(vertical_col)["_is_inbound"]
                .agg(["sum", "count"])
                .reset_index()
            )
            inbound_agg.columns = ["Vertical", "Inbound", "Total"]
            inbound_agg["Outreach"] = inbound_agg["Total"] - inbound_agg["Inbound"]
            inbound_agg["Inbound %"] = (inbound_agg["Inbound"] / inbound_agg["Total"] * 100).round(1)

            fig = go.Figure()
            fig.add_trace(go.Bar(name="Inbound", x=inbound_agg["Vertical"], y=inbound_agg["Inbound"], marker_color="#22c55e"))
            fig.add_trace(go.Bar(name="Outreach", x=inbound_agg["Vertical"], y=inbound_agg["Outreach"], marker_color="#4a90d9"))
            fig.update_layout(barmode="stack", **CHART_LAYOUT, title="Inbound vs. Outreach by Vertical")
            fig.update_xaxes(gridcolor="#1f2937", tickangle=-30)
            fig.update_yaxes(gridcolor="#1f2937")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # ── Status breakdown table ────────────────────────────────────────────
        if has_status and has_vertical:
            st.markdown("#### Status Breakdown by Vertical")
            status_pivot = (
                df[[vertical_col, status_col]]
                .dropna(subset=[vertical_col, status_col])
                .groupby([vertical_col, status_col])
                .size()
                .unstack(fill_value=0)
            )
            if not status_pivot.empty:
                st.dataframe(status_pivot, use_container_width=True)
            else:
                st.info("No status data to display.")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 5 — CAMPAIGN ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("### Campaign Analysis")

    if not campaign_col or campaign_col not in df.columns:
        st.info("No Campaign column mapped. Please check column mapping.")
    else:
        campaign_series = df[campaign_col].dropna()
        if campaign_series.str.strip().replace("", pd.NA).dropna().empty:
            st.info("Campaign column is empty.")
        else:
            # Filter out blank/null campaigns
            cdf = df[df[campaign_col].notna() & (df[campaign_col].str.strip() != "")].copy()

            # Count per campaign
            camp_counts = cdf[campaign_col].value_counts().reset_index()
            camp_counts.columns = ["Campaign", "Count"]

            col_ca, col_cb = st.columns(2)

            with col_ca:
                fig = go.Figure(go.Bar(
                    x=camp_counts["Count"],
                    y=camp_counts["Campaign"],
                    orientation="h",
                    marker_color=SHOPIFY_COLOR,
                    text=camp_counts["Count"],
                    textposition="outside",
                ))
                apply_dark_layout(fig, "Influencers per Campaign")
                st.plotly_chart(fig, use_container_width=True)

            # Vertical breakdown per campaign (stacked bar)
            with col_cb:
                if vertical_col and vertical_col in cdf.columns:
                    camp_vert = (
                        cdf[[campaign_col, vertical_col]]
                        .dropna()
                        .groupby([campaign_col, vertical_col])
                        .size()
                        .unstack(fill_value=0)
                    )
                    fig = go.Figure()
                    for idx, vert in enumerate(camp_vert.columns):
                        fig.add_trace(go.Bar(
                            name=vert,
                            x=camp_vert.index,
                            y=camp_vert[vert],
                            marker_color=PALETTE[idx % len(PALETTE)],
                        ))
                    fig.update_layout(barmode="stack", **CHART_LAYOUT, title="Vertical Breakdown per Campaign")
                    fig.update_xaxes(gridcolor="#1f2937", tickangle=-30)
                    fig.update_yaxes(gridcolor="#1f2937")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No Vertical column mapped.")

            st.markdown("---")

            # Avg followers and engagement per campaign
            st.markdown("#### Campaign Performance Metrics")
            camp_stats = cdf.groupby(campaign_col).agg(
                Count=(campaign_col, "count"),
                **({followers_col: (followers_col, "mean")} if followers_col else {}),
                **({engagement_col: (engagement_col, "mean")} if engagement_col else {}),
                **({posts_col: (posts_col, lambda x: (x.fillna(0) > 0).mean() * 100)} if posts_col else {}),
            ).reset_index()

            # Rename for display
            rename_map = {campaign_col: "Campaign", "Count": "Count"}
            if followers_col:
                rename_map[followers_col] = "Avg Followers"
            if engagement_col:
                rename_map[engagement_col] = "Avg Engagement Rate"
            if posts_col:
                rename_map[posts_col] = "Post Rate %"
            camp_stats = camp_stats.rename(columns=rename_map)

            # Format
            if "Avg Followers" in camp_stats.columns:
                camp_stats["Avg Followers"] = camp_stats["Avg Followers"].apply(fmt_number)
            if "Avg Engagement Rate" in camp_stats.columns:
                camp_stats["Avg Engagement Rate"] = camp_stats["Avg Engagement Rate"].apply(
                    lambda x: f"{x:.2f}%" if pd.notna(x) else "—"
                )
            if "Post Rate %" in camp_stats.columns:
                camp_stats["Post Rate %"] = camp_stats["Post Rate %"].apply(
                    lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
                )

            st.dataframe(camp_stats, hide_index=True, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 6 — CREATOR ROSTER
# ═════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown("### Creator Roster")
    st.markdown(
        "<p style='color:#888;margin-top:-8px;'>Use filters to find creators worth pulling for a new campaign. "
        "Reliability Score rewards fast responses and posting history.</p>",
        unsafe_allow_html=True,
    )

    # ── Build per-creator record ───────────────────────────────────────────────
    roster = df.copy()

    # Responded = has a date in reply_col
    if reply_col and reply_col in roster.columns:
        roster["_responded"] = roster[reply_col].notna().astype(int)
    else:
        roster["_responded"] = 0

    # Outreached = has a date in outreach_col
    if outreach_col and outreach_col in roster.columns:
        roster["_outreached"] = roster[outreach_col].notna().astype(int)
    else:
        roster["_outreached"] = 0

    # Posted = POSTED status
    if status_col and status_col in roster.columns:
        s_norm = roster[status_col].astype(str).str.strip().str.lower()
        roster["_posted"] = s_norm.isin(STATUS_POSTED).astype(int)
    else:
        roster["_posted"] = 0

    # Days to respond
    if "_days_to_reply" in roster.columns:
        roster["_dtr"] = pd.to_numeric(roster["_days_to_reply"], errors="coerce")
    else:
        roster["_dtr"] = pd.NA

    # ── Reliability Score (0–100) ──────────────────────────────────────────────
    # +40 if responded, +40 if posted, +20 bonus if response time ≤ 7 days
    roster["_score"] = (
        roster["_responded"] * 40
        + roster["_posted"] * 40
        + roster["_dtr"].apply(lambda d: 20 if pd.notna(d) and d <= 7 else (10 if pd.notna(d) and d <= 14 else 0))
    )

    # ── Filters ───────────────────────────────────────────────────────────────
    f1, f2, f3, f4 = st.columns(4)

    with f1:
        vert_options = ["All"] + sorted(roster[vertical_col].dropna().unique().tolist()) if vertical_col else ["All"]
        sel_vert = st.selectbox("Vertical", vert_options, key="roster_vert")

    with f2:
        tier_options = ["All"] + [t for t in TIER_ORDER if t in roster["_tier"].values]
        sel_tier = st.selectbox("Follower Tier", tier_options, key="roster_tier")

    with f3:
        plat_options = ["All"] + sorted(roster[platform_col].dropna().unique().tolist()) if platform_col else ["All"]
        sel_plat = st.selectbox("Platform", plat_options, key="roster_plat")

    with f4:
        reliability_filter = st.selectbox(
            "Reliability",
            ["All", "High (80–100)", "Medium (40–79)", "Low (0–39)"],
            key="roster_rel",
        )

    # Second row of filters
    f5, f6, f7 = st.columns(3)
    with f5:
        posted_only = st.checkbox("Posted before", key="roster_posted")
    with f6:
        responded_only = st.checkbox("Responded before", key="roster_responded")
    with f7:
        min_followers = st.number_input("Min followers", min_value=0, value=0, step=1000, key="roster_minfol")

    # Apply filters
    fdf = roster.copy()
    if sel_vert != "All" and vertical_col:
        fdf = fdf[fdf[vertical_col] == sel_vert]
    if sel_tier != "All":
        fdf = fdf[fdf["_tier"] == sel_tier]
    if sel_plat != "All" and platform_col:
        fdf = fdf[fdf[platform_col] == sel_plat]
    if reliability_filter == "High (80–100)":
        fdf = fdf[fdf["_score"] >= 80]
    elif reliability_filter == "Medium (40–79)":
        fdf = fdf[(fdf["_score"] >= 40) & (fdf["_score"] < 80)]
    elif reliability_filter == "Low (0–39)":
        fdf = fdf[fdf["_score"] < 40]
    if posted_only:
        fdf = fdf[fdf["_posted"] == 1]
    if responded_only:
        fdf = fdf[fdf["_responded"] == 1]
    if min_followers > 0 and followers_col:
        fdf = fdf[fdf[followers_col].fillna(0) >= min_followers]

    st.markdown(f"**{len(fdf):,} creators** match your filters")

    # ── Summary metrics ───────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    total_f = len(fdf)
    outreached_f = int(fdf["_outreached"].sum())
    responded_f = int(fdf["_responded"].sum())
    posted_f = int(fdf["_posted"].sum())
    resp_rate_f = (responded_f / outreached_f * 100) if outreached_f > 0 else 0
    post_rate_f = (posted_f / responded_f * 100) if responded_f > 0 else 0
    avg_dtr_f = fdf["_dtr"][fdf["_dtr"].notna() & (fdf["_dtr"] >= 0)].mean()

    m1.metric("Response Rate", f"{resp_rate_f:.1f}%", help=f"{responded_f} responded / {outreached_f} outreached")
    m2.metric("Post Rate", f"{post_rate_f:.1f}%", help=f"{posted_f} posted / {responded_f} responded")
    m3.metric("Avg Response Time", f"{avg_dtr_f:.1f}d" if pd.notna(avg_dtr_f) else "—")
    m4.metric("Avg Reliability Score", f"{fdf['_score'].mean():.0f}/100" if total_f > 0 else "—")

    st.markdown("---")

    # ── Build display table ────────────────────────────────────────────────────
    display_cols_map = {}
    if name_col:        display_cols_map["Name"] = name_col
    if ig_col:          display_cols_map["IG Handle"] = ig_col
    if tt_col:          display_cols_map["TT Handle"] = tt_col
    if platform_col:    display_cols_map["Platform"] = platform_col
    if vertical_col:    display_cols_map["Vertical"] = vertical_col
    if followers_col:   display_cols_map["Followers"] = followers_col
    if campaign_col:    display_cols_map["Campaign"] = campaign_col
    if status_col:      display_cols_map["Status"] = status_col

    table_df = fdf[[c for c in display_cols_map.values() if c in fdf.columns]].copy()
    table_df.columns = [k for k, v in display_cols_map.items() if v in fdf.columns]

    # Add computed columns
    table_df["Tier"] = fdf["_tier"].values
    table_df["Responded"] = fdf["_responded"].map({1: "Yes", 0: "No"}).values
    table_df["Posted"] = fdf["_posted"].map({1: "Yes", 0: "No"}).values
    table_df["Days to Respond"] = fdf["_dtr"].apply(
        lambda x: f"{int(x)}d" if pd.notna(x) and x >= 0 else "—"
    ).values
    table_df["Reliability Score"] = fdf["_score"].apply(lambda x: f"{int(x)}/100").values

    # Format followers
    if "Followers" in table_df.columns:
        table_df["Followers"] = fdf[followers_col].apply(fmt_number).values

    # Sort by reliability score descending
    table_df = table_df.sort_values("Reliability Score", ascending=False)

    st.dataframe(table_df, hide_index=True, use_container_width=True)

    # ── Export ────────────────────────────────────────────────────────────────
    csv_export = table_df.to_csv(index=False)
    st.download_button(
        label="Export filtered list as CSV",
        data=csv_export,
        file_name="creator_roster_filtered.csv",
        mime="text/csv",
    )
