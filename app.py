"""
Swiggy Customer Experience (CX) Intelligence Dashboard
TAPMI Academic Research Project | Faculty Guide: Prof. Jinu Sara Rajan

Setup:  pip install "streamlit>=1.32" pandas numpy plotly openpyxl
Run:    streamlit run app.py
"""

import inspect
import io
import os
from html import escape

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# =====================================================================
# 1. PAGE SETUP
# =====================================================================
st.set_page_config(
    page_title="Swiggy CX Intelligence | TAPMI",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================================
# 2. CONSTANTS (colours, files, keyword taxonomy)
# =====================================================================
BRAND = "#FF5200"
INK = "#0F172A"
MUTED = "#64748B"
BORDER = "#E2E8F0"

SENTIMENT_COLORS = {"Positive": "#10B981", "Neutral": "#F59E0B", "Negative": "#EF4444"}
SENTIMENTS = list(SENTIMENT_COLORS)

PRIMARY_FILE_PATH = r"F:\Sem 5\Jinu Sara Rajan\Project\swiggy_reviews.csv"
FALLBACK_FILE_PATH = "swiggy_reviews.csv"

TOPIC_KEYWORDS = {
    "Delivery & Speed": ["delivery", "late", "delayed", "time", "partner", "rider", "hour", "hours", "fast"],
    "App Experience & Pricing": ["app", "ui", "coupon", "coupons", "offers", "discount", "price", "costly", "expensive"],
    "Refund & Cancellation": ["refund", "money", "cancel", "charge", "deduct", "fees", "cheated"],
    "Customer Support": ["support", "chat", "bot", "care", "unhelpful", "complaint", "executive", "call"],
    "Food Quality & Accuracy": ["wrong", "missing", "stale", "cold", "item", "items", "spoiled", "rotten", "quantity"],
}
TOPICS = list(TOPIC_KEYWORDS)
TOPIC_COLORS = dict(zip(TOPICS, ["#FF5200", "#4F46E5", "#0284C7", "#10B981", "#F59E0B"]))
ALL_DOMAINS = "All domains"

# Simulator levers: session key -> (label, topic it fixes, default %)
SIM_LEVERS = {
    "lever_delivery": ("Delivery SLA compliance increase", "Delivery & Speed", 35),
    "lever_refund": ("Refund & dispute resolution speed", "Refund & Cancellation", 50),
    "lever_app": ("App pricing transparency & stability", "App Experience & Pricing", 30),
    "lever_support": ("Support first-contact resolution", "Customer Support", 40),
}
SIM_PRESETS = {
    "Conservative": (15, 20, 10, 15),
    "Balanced": (35, 50, 30, 40),
    "Aggressive": (70, 80, 60, 75),
}

FILTER_DEFAULTS = {
    "f_sentiment": SENTIMENTS,
    "f_rating": (1, 5),
    "f_domain": ALL_DOMAINS,
}

PLAYBOOK = [
    {
        "area": "Operations & dispatch", "color": "#FF5200", "bg": "#FFF1EB", "topic": "Delivery & Speed",
        "title": "Dynamic buffer staging & transit windows",
        "insight": "{share:.0f}% of complaints mention delivery, mostly inaccurate arrival estimates during peak dinner surges.",
        "actions": [
            ("Rider proximity dispatch", "Delay the final pickup notification until the restaurant hits 80% food preparation, eliminating rider idling."),
            ("Proactive SLA credits", "Automatically credit 40 Swiggy Money points if delivery exceeds the estimated arrival by 12 minutes."),
        ],
    },
    {
        "area": "Financial trust", "color": "#0284C7", "bg": "#E0F2FE", "topic": "App Experience & Pricing",
        "title": "Transparent cart pricing & fee disclosures",
        "insight": "Surprise surge pricing and coupon failures at final OTP entry drive checkout drop-offs ({share:.0f}% of complaints).",
        "actions": [
            ("Upfront bill itemisation", "Disclose packaging fees and platform handling charges directly on the restaurant menu."),
            ("Payment offer locking", "Cache payment-discount validation for 180 seconds during bank gateway authentication."),
        ],
    },
    {
        "area": "Customer support", "color": "#059669", "bg": "#ECFDF5", "topic": "Customer Support",
        "title": "Rapid AI escalation & photo refunds",
        "insight": "Chatbot deadlocks on missing or spilled items produce the densest cluster of 1-star ratings ({share:.0f}% of complaints).",
        "actions": [
            ("Autonomous image inspection", "Validate customer photo uploads of wrong or damaged items with computer vision for instant credit."),
            ("Smart human transfer", "Bypass the bot immediately when phrases like \"spoiled\", \"unhygienic\" or \"money deducted\" appear."),
        ],
    },
    {
        "area": "Policy redesign", "color": "#D97706", "bg": "#FEF3C7", "topic": "Refund & Cancellation",
        "title": "Cancellation fee restructuring",
        "insight": "Rigid 100% cancellation deductions create resentment and uninstalls ({share:.0f}% of complaints).",
        "actions": [
            ("Grace window", "Offer a 90-second zero-cost cancellation grace period after order confirmation."),
            ("Credit conversion", "Convert unavoidable kitchen-preparation penalties into usable food credits instead of full forfeiture."),
        ],
    },
]

# =====================================================================
# 3. STYLING
# =====================================================================
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, .stApp, [class*="css"] { font-family: "Plus Jakarta Sans", "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
.stApp { background: #FFFFFF; color: #0F172A; }
.block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1440px; }

/* Sidebar */
[data-testid="stSidebar"] { background: #F7F8FB; border-right: 1px solid #E2E8F0; }
.side-title { font-size: 17px; font-weight: 800; color: #0F172A; margin: 0; }
.side-sub { font-size: 12.5px; color: #64748B; margin: 2px 0 14px 0; }
.side-label { font-size: 13px; font-weight: 700; color: #334155; margin: 18px 0 6px 0; }

/* Header */
.hero { display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: space-between;
        padding: 18px 24px; border: 1px solid #E2E8F0; border-left: 6px solid #FF5200; border-radius: 14px;
        background: #FFFFFF; margin-bottom: 10px; }
.hero-left { display: flex; align-items: center; gap: 16px; }
.hero h1 { margin: 0; padding: 0; font-size: 22px; font-weight: 800; color: #0F172A; letter-spacing: -0.3px; line-height: 1.25; }
.hero p { margin: 3px 0 0 0; font-size: 13px; color: #64748B; font-weight: 500; }
.tapmi { background: #0A2540; padding: 8px 16px; border-radius: 8px; text-align: right; }
.tapmi b { display: block; color: #FFFFFF; font-weight: 800; font-size: 15px; letter-spacing: 1.5px; }
.tapmi span { color: #94A3B8; font-size: 10px; font-weight: 500; }
.filter-line { font-size: 13px; color: #64748B; margin: 4px 0 14px 2px; }
.filter-line b { color: #0F172A; }

/* KPI metrics */
[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px 18px; }
[data-testid="stMetricLabel"] p { font-size: 13px; font-weight: 600; color: #64748B; }
[data-testid="stMetricValue"] { font-size: 24px; font-weight: 800; color: #0F172A; }

/* Tabs as pills */
.stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px; }
.stTabs [data-baseweb="tab"] { height: auto; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 999px; padding: 8px 18px; }
.stTabs [data-baseweb="tab"] p { font-size: 14px; font-weight: 600; color: #475569; }
.stTabs [aria-selected="true"] { background: #FF5200; border-color: #FF5200; }
.stTabs [aria-selected="true"] p { color: #FFFFFF; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

/* Buttons (normal + download) */
.stButton > button, .stDownloadButton > button { border-radius: 10px; font-weight: 600; min-height: 40px; }
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] { background: #FF5200; border: 1px solid #FF5200; color: #FFFFFF; }
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover { background: #E04600; border-color: #E04600; color: #FFFFFF; }
.stButton > button[kind="primary"] p, .stDownloadButton > button[kind="primary"] p,
[data-testid="stBaseButton-primary"] p { color: #FFFFFF; }
.stButton > button[kind="secondary"], .stDownloadButton > button[kind="secondary"],
[data-testid="stBaseButton-secondary"] { background: #FFFFFF; border: 1px solid #CBD5E1; color: #0F172A; }
.stButton > button[kind="secondary"]:hover, .stDownloadButton > button[kind="secondary"]:hover,
[data-testid="stBaseButton-secondary"]:hover { border-color: #FF5200; color: #FF5200; }
button:focus-visible { outline: 2px solid #FF5200 !important; outline-offset: 2px; }

/* Card text */
.card-title { font-size: 15px; font-weight: 700; color: #0F172A; margin: 0; }
.card-sub { font-size: 12.5px; color: #64748B; margin: 2px 0 6px 0; }

/* Callouts */
.callout { border-radius: 10px; padding: 12px 16px; margin: 6px 0 4px 0; font-size: 13.5px; line-height: 1.55; }
.callout.indigo { background: #EEF2FF; border-left: 4px solid #4F46E5; color: #312E81; }
.callout.orange { background: #FFF1EB; border-left: 4px solid #FF5200; color: #7C2D12; }

/* Playbook cards */
.play-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px 22px; margin-bottom: 16px; }
.play-head { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: space-between; }
.chip { font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 999px; }
.impact { font-size: 12px; font-weight: 600; color: #64748B; }
.play-card h4 { margin: 10px 0 6px 0; padding: 0; font-size: 16px; font-weight: 700; color: #0F172A; }
.play-card p { font-size: 13.5px; color: #475569; line-height: 1.55; margin: 0 0 8px 0; }
.play-card ul { font-size: 13.5px; color: #334155; padding-left: 18px; margin: 0; }
.play-card li { margin-bottom: 4px; }

/* Review spotlight */
.spot { border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px 18px; background: #F7F8FB; }
.spot .meta { font-size: 12.5px; color: #64748B; margin-bottom: 6px; }
.spot .text { font-size: 15px; color: #0F172A; line-height: 1.55; }
</style>
""",
    unsafe_allow_html=True,
)

PLOTLY_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


# =====================================================================
# 4. SMALL HELPERS
# =====================================================================
def _stretch_kwargs(func):
    """Full-width keyword that works on both old and new Streamlit versions."""
    try:
        param = inspect.signature(func).parameters.get("width")
    except (TypeError, ValueError):
        param = None
    if param is not None and isinstance(param.default, str):
        return {"width": "stretch"}
    return {"use_container_width": True}


FULL = {name: _stretch_kwargs(getattr(st, name)) for name in ["plotly_chart", "dataframe", "button", "download_button"]}


def html(markup, target=None):
    """Render HTML safely: strips indentation so Markdown never turns it into a code block."""
    clean = "\n".join(line.strip() for line in markup.strip().splitlines() if line.strip())
    (target or st).markdown(clean, unsafe_allow_html=True)


def card_title(title, subtitle=""):
    sub = f"<div class='card-sub'>{subtitle}</div>" if subtitle else ""
    html(f"<div class='card-title'>{title}</div>{sub}")


def style_fig(fig, height=330):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, Segoe UI, sans-serif", color=INK, size=12),
        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12, bordercolor=BORDER),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER, linecolor="#CBD5E1")
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER, linecolor="#CBD5E1")
    return fig


def show_chart(fig, height=330):
    st.plotly_chart(style_fig(fig, height), config=PLOTLY_CONFIG, **FULL["plotly_chart"])


def short(topic):
    return topic.replace(" & ", "<br>& ")


# =====================================================================
# 5. DATA ENGINE
# =====================================================================
def classify_sentiment(score):
    if score >= 4:
        return "Positive"
    if score == 3:
        return "Neutral"
    return "Negative"


def sample_reviews():
    rows = [
        ("Rider was late by 1 hour and food arrived cold and stale.", 1),
        ("Prompt delivery, piping hot biryani and great packaging.", 5),
        ("App deducted payment twice and support bot refused to refund.", 1),
        ("Used the discount coupon, smooth checkout and polite rider.", 5),
        ("Wrong items received, missing my beverage and dessert.", 2),
        ("Support executive disconnected chat without resolving my query.", 1),
        ("Decent service, standard food delivery time.", 3),
        ("Heavy cancellation charges applied for a delay from restaurant side.", 1),
    ] * 125
    return pd.DataFrame({
        "reviewId": range(1, len(rows) + 1),
        "content": [r[0] for r in rows],
        "score": [r[1] for r in rows],
    })


def read_table(source, name):
    if str(name).lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(source)
    return pd.read_csv(source)


def prepare(raw):
    df = raw.copy()
    lookup = {str(c).lower().strip(): c for c in df.columns}

    def pick(candidates):
        return next((lookup[c] for c in candidates if c in lookup), None)

    content_col = pick(["content", "review", "review_text", "text", "comment"])
    score_col = pick(["score", "rating", "stars", "star_rating"])
    if content_col is None or score_col is None:
        raise ValueError(
            "The file needs a review text column (e.g. 'content' or 'review') "
            "and a rating column (e.g. 'score' or 'rating')."
        )
    df = df.rename(columns={content_col: "content", score_col: "score"})

    id_col = pick(["reviewid", "review_id", "id"])
    if id_col is not None:
        df = df.rename(columns={id_col: "reviewId"}).drop_duplicates(subset=["reviewId"])
    else:
        df.insert(0, "reviewId", range(1, len(df) + 1))

    date_col = pick(["at", "date", "review_date", "timestamp"])
    if date_col is not None:
        df["review_date"] = pd.to_datetime(df[date_col], errors="coerce")

    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    df = df.dropna(subset=["content", "score"])
    df["score"] = df["score"].round().clip(1, 5).astype(int)

    df["clean_content"] = df["content"].astype(str).str.lower().str.strip()
    df["sentiment"] = df["score"].apply(classify_sentiment)

    # Whole-word matching, so "app" no longer matches "happy" and "ui" no longer matches "quite".
    for topic, keywords in TOPIC_KEYWORDS.items():
        pattern = r"\b(?:" + "|".join(keywords) + r")\b"
        df[topic] = df["clean_content"].str.contains(pattern, regex=True)

    return df.reset_index(drop=True)


@st.cache_data(show_spinner="Loading reviews...")
def load_dataset(file_bytes=None, file_name=None):
    if file_bytes is not None:
        return prepare(read_table(io.BytesIO(file_bytes), file_name)), f"Uploaded file: {file_name}"
    if os.path.exists(PRIMARY_FILE_PATH):
        return prepare(read_table(PRIMARY_FILE_PATH, PRIMARY_FILE_PATH)), "Project file (F: drive)"
    if os.path.exists(FALLBACK_FILE_PATH):
        return prepare(read_table(FALLBACK_FILE_PATH, FALLBACK_FILE_PATH)), "swiggy_reviews.csv (app folder)"
    return prepare(sample_reviews()), "Built-in sample data (demo mode)"


# =====================================================================
# 6. SESSION STATE + CALLBACKS
# =====================================================================
for key, value in FILTER_DEFAULTS.items():
    st.session_state.setdefault(key, list(value) if isinstance(value, list) else value)
for key, (_, _, default) in SIM_LEVERS.items():
    st.session_state.setdefault(key, default)


def reset_filters():
    for k, v in FILTER_DEFAULTS.items():
        st.session_state[k] = list(v) if isinstance(v, list) else v


def apply_preset(name):
    for k, v in zip(SIM_LEVERS, SIM_PRESETS[name]):
        st.session_state[k] = v


# =====================================================================
# 7. SIDEBAR
# =====================================================================
with st.sidebar:
    html("""
        <div class="side-title">Control panel</div>
        <div class="side-sub">Every chart and table updates as you change these.</div>
    """)

    with st.expander("Data source", expanded=False):
        uploaded = st.file_uploader(
            "Upload reviews (CSV or Excel)",
            type=["csv", "xlsx", "xls"],
            help="Needs a review text column (content/review) and a rating column (score/rating).",
        )
        try:
            if uploaded is not None:
                df, source = load_dataset(uploaded.getvalue(), uploaded.name)
            else:
                df, source = load_dataset()
        except Exception as exc:  # show a clear message instead of a crash
            st.error(f"Could not read the file. {exc}")
            df, source = load_dataset()
        st.caption(f"Source: {source}  \nRecords: {len(df):,}")

    html("<div class='side-label'>Filters</div>")
    st.multiselect("Sentiment", options=SENTIMENTS, key="f_sentiment")
    st.slider("Rating range (stars)", 1, 5, key="f_rating")
    st.selectbox("Operational domain", options=[ALL_DOMAINS] + TOPICS, key="f_domain")
    st.button("Reset filters", on_click=reset_filters, **FULL["button"])

    html("<div class='side-label'>About</div>")
    st.caption("TAPMI academic research project on Swiggy customer reviews. Faculty guide: Prof. Jinu Sara Rajan.")

# =====================================================================
# 8. FILTERING + CORE METRICS
# =====================================================================
sel_sent = st.session_state.f_sentiment
lo, hi = st.session_state.f_rating
domain = st.session_state.f_domain

fdf = df[df["sentiment"].isin(sel_sent) & df["score"].between(lo, hi)]
if domain != ALL_DOMAINS:
    fdf = fdf[fdf[domain]]

n_all, n_view = len(df), len(fdf)
base_avg = df["score"].mean()
base_pos = (df["sentiment"] == "Positive").mean() * 100
base_neg = (df["sentiment"] == "Negative").mean() * 100

view_avg = fdf["score"].mean() if n_view else 0.0
view_pos = (fdf["sentiment"] == "Positive").mean() * 100 if n_view else 0.0
view_neg = (fdf["sentiment"] == "Negative").mean() * 100 if n_view else 0.0

fneg = fdf[fdf["sentiment"] == "Negative"]
topic_share = (fneg[TOPICS].mean() * 100).round(1) if len(fneg) else pd.Series(0.0, index=TOPICS)
top_pain = topic_share.idxmax() if topic_share.max() > 0 else "None"

neg_all = df[df["sentiment"] == "Negative"]
platform_share = (neg_all[TOPICS].mean() * 100) if len(neg_all) else pd.Series(0.0, index=TOPICS)

# =====================================================================
# 9. HEADER + KPI ROW
# =====================================================================
html(f"""
<div class="hero">
  <div class="hero-left">
    <svg width="46" height="46" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Swiggy">
      <rect width="100" height="100" rx="22" fill="{BRAND}"/>
      <path d="M53.2 24C41.5 24 32 33.5 32 45.2C32 55.6 42.4 68.3 50.8 76.5C52.1 77.8 54.3 77.8 55.6 76.5C64 68.3 74.4 55.6 74.4 45.2C74.4 33.5 64.9 24 53.2 24ZM53.2 41.5C49.8 41.5 47 38.7 47 35.3C47 31.9 49.8 29.1 53.2 29.1C56.6 29.1 59.4 31.9 59.4 35.3C59.4 38.7 56.6 41.5 53.2 41.5Z" fill="white"/>
    </svg>
    <div>
      <h1>Swiggy Customer Experience Intelligence</h1>
      <p>What customers love, what frustrates them, and what fixing it would be worth.</p>
    </div>
  </div>
  <div class="tapmi"><b>TAPMI</b><span>T. A. PAI MANAGEMENT INSTITUTE</span></div>
</div>
""")

domain_txt = domain if domain != ALL_DOMAINS else "all domains"
sent_txt = ", ".join(sel_sent) if sel_sent else "none"
html(
    f"<div class='filter-line'>Showing <b>{n_view:,}</b> of {n_all:,} reviews &nbsp;|&nbsp; "
    f"Sentiment: <b>{sent_txt}</b> &nbsp;|&nbsp; Rating: <b>{lo}-{hi} stars</b> &nbsp;|&nbsp; Domain: <b>{domain_txt}</b></div>"
)

filtered = n_view != n_all
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Reviews in view", f"{n_view:,}", f"{n_view / n_all * 100:.0f}% of dataset", delta_color="off")
k2.metric("Average rating", f"{view_avg:.2f} / 5", f"{view_avg - base_avg:+.2f} vs all" if filtered and n_view else None)
k3.metric("Positive share", f"{view_pos:.1f}%", f"{view_pos - base_pos:+.1f} pts vs all" if filtered and n_view else None)
k4.metric("Negative share", f"{view_neg:.1f}%", f"{view_neg - base_neg:+.1f} pts vs all" if filtered and n_view else None, delta_color="inverse")
k5.metric(
    "Top pain point",
    top_pain,
    f"{topic_share.max():.0f}% of complaints" if top_pain != "None" else None,
    delta_color="off",
    help="The domain mentioned most often in negative reviews within the current view.",
)

st.write("")

# =====================================================================
# 10. TABS
# =====================================================================
tab_overview, tab_sim, tab_playbook, tab_explorer = st.tabs(
    ["Analytics overview", "Impact simulator", "Strategy playbook", "Review explorer"]
)

EMPTY_MSG = "No reviews match the current filters. Widen the filters or press **Reset filters** in the sidebar."

# ---------------------------------------------------------------------
# TAB 1: ANALYTICS OVERVIEW
# ---------------------------------------------------------------------
with tab_overview:
    if fdf.empty:
        st.warning(EMPTY_MSG)
    else:
        c1, c2 = st.columns(2, gap="medium")

        with c1:
            with st.container(border=True):
                card_title("Sentiment mix", "Share of reviews by sentiment. Hover a slice for counts.")
                counts = fdf["sentiment"].value_counts().reindex(SENTIMENTS, fill_value=0)
                fig = go.Figure(go.Pie(
                    labels=counts.index, values=counts.values, hole=0.62, sort=False, direction="clockwise",
                    marker=dict(colors=[SENTIMENT_COLORS[s] for s in counts.index], line=dict(color="#FFFFFF", width=3)),
                    textinfo="percent", textfont=dict(size=13, color="#FFFFFF"),
                    hovertemplate="<b>%{label}</b><br>%{value:,} reviews<br>%{percent}<extra></extra>",
                ))
                fig.add_annotation(text=f"<b>{n_view:,}</b><br>reviews", showarrow=False, font=dict(size=18, color=INK))
                show_chart(fig)

        with c2:
            with st.container(border=True):
                card_title("What customers complain about", "Share of negative reviews mentioning each domain (one review can mention several).")
                if fneg.empty:
                    st.info("The current filters contain no negative reviews, so there is nothing to break down.")
                else:
                    ts = topic_share.sort_values()
                    fig = go.Figure(go.Bar(
                        x=ts.values, y=ts.index, orientation="h",
                        marker_color=[TOPIC_COLORS[t] for t in ts.index],
                        text=[f"{v:.1f}%" for v in ts.values], textposition="outside",
                        hovertemplate="<b>%{y}</b><br>%{x:.1f}% of negative reviews<extra></extra>",
                    ))
                    fig.update_xaxes(range=[0, max(ts.max() * 1.25, 10)], ticksuffix="%")
                    fig.update_yaxes(showgrid=False)
                    show_chart(fig)

        c3, c4 = st.columns(2, gap="medium")

        with c3:
            with st.container(border=True):
                card_title("Rating distribution", "Number of reviews at each star level.")
                rc = fdf["score"].value_counts().reindex(range(1, 6), fill_value=0)
                bar_colors = ["#EF4444", "#F87171", "#F59E0B", "#34D399", "#10B981"]
                fig = go.Figure(go.Bar(
                    x=[f"{s} star" for s in rc.index], y=rc.values, marker_color=bar_colors,
                    text=[f"{v:,}" for v in rc.values], textposition="outside",
                    hovertemplate="<b>%{x}</b><br>%{y:,} reviews<extra></extra>",
                ))
                fig.update_yaxes(range=[0, max(rc.max() * 1.18, 1)])
                fig.update_xaxes(showgrid=False)
                show_chart(fig, height=300)

        with c4:
            with st.container(border=True):
                card_title("Domain mentions by sentiment", "% of reviews in each sentiment that mention a domain.")
                present = [s for s in SENTIMENTS if s in set(fdf["sentiment"])]
                hm = (fdf.groupby("sentiment")[TOPICS].mean() * 100).reindex(present)
                fig = go.Figure(go.Heatmap(
                    z=hm.values, x=[short(t) for t in TOPICS], y=hm.index,
                    colorscale=[[0, "#FFF7F2"], [1, BRAND]], zmin=0, zmax=max(100 if hm.empty else hm.values.max(), 1),
                    text=np.round(hm.values, 0), texttemplate="%{text:.0f}%", textfont=dict(size=12),
                    hovertemplate="<b>%{y}</b> reviews<br>%{x}: %{z:.1f}%<extra></extra>", showscale=False, xgap=3, ygap=3,
                ))
                fig.update_xaxes(showgrid=False)
                fig.update_yaxes(showgrid=False, autorange="reversed")
                show_chart(fig, height=300)

        # Trend chart only when the data has review dates
        if "review_date" in fdf.columns and fdf["review_date"].notna().any():
            monthly = (
                fdf.dropna(subset=["review_date"])
                .groupby(pd.Grouper(key="review_date", freq="MS"))
                .agg(reviews=("score", "size"), avg_rating=("score", "mean"))
                .query("reviews > 0")
            )
            if len(monthly) >= 2:
                with st.container(border=True):
                    card_title("Monthly trend", "Review volume (bars) and average rating (line).")
                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                    fig.add_bar(x=monthly.index, y=monthly["reviews"], name="Reviews", marker_color="#CBD5E1")
                    fig.add_scatter(x=monthly.index, y=monthly["avg_rating"], name="Avg rating", mode="lines+markers",
                                    line=dict(color=BRAND, width=3), secondary_y=True)
                    fig.update_yaxes(title_text="Reviews", secondary_y=False)
                    fig.update_yaxes(title_text="Avg rating", range=[1, 5], secondary_y=True, showgrid=False)
                    show_chart(fig, height=320)

        if top_pain != "None":
            html(
                f"<div class='callout orange'><b>Key insight:</b> {top_pain} appears in "
                f"{topic_share.max():.0f}% of negative reviews in this view. {view_neg:.0f}% of reviews are negative "
                f"and the average rating is {view_avg:.2f} stars.</div>"
            )

# ---------------------------------------------------------------------
# TAB 2: IMPACT SIMULATOR (platform-wide, independent of sidebar filters)
# ---------------------------------------------------------------------
with tab_sim:
    html("""
        <div class="card-title" style="font-size:18px;">What would fixing these problems be worth?</div>
        <div class="card-sub">Set how much each problem area improves and see the projected rating, sentiment and customers retained.
        Uses the full dataset, so sidebar filters don't change it.</div>
    """)

    ctrl, res = st.columns([1, 1.9], gap="large")

    with ctrl:
        with st.container(border=True):
            card_title("Quick scenarios")
            current = tuple(st.session_state[k] for k in SIM_LEVERS)
            p_cols = st.columns(3)
            for col, name in zip(p_cols, SIM_PRESETS):
                col.button(
                    name, key=f"preset_{name}", on_click=apply_preset, args=(name,),
                    type="primary" if current == SIM_PRESETS[name] else "secondary", **FULL["button"],
                )

            card_title("Improvement levers", "Share of each problem's complaints that gets resolved.")
            for key, (label, _, _) in SIM_LEVERS.items():
                st.slider(label, 0, 100, step=5, key=key, format="%d%%")

    # Simulation model (same logic as the original project)
    n_neg = len(neg_all)
    resolved = {  # lever key -> complaints resolved
        key: neg_all[topic].sum() * st.session_state[key] / 100
        for key, (_, topic, _) in SIM_LEVERS.items()
    }
    rescued = int(min(sum(resolved.values()) * 0.72, n_neg))  # 0.72 adjusts for reviews tagged with several topics
    proj_neg = max(0, n_neg - rescued)
    pos_count = int((df["sentiment"] == "Positive").sum())
    proj_pos = pos_count + int(rescued * 0.8)
    proj_score = min(5.0, (df["score"].sum() + rescued * 2.8) / n_all)
    proj_pos_pct = proj_pos / n_all * 100

    with res:
        r1, r2, r3 = st.columns(3)
        r1.metric("Projected app rating", f"{proj_score:.2f} / 5", f"{proj_score - base_avg:+.2f}")
        r2.metric("Projected positive share", f"{proj_pos_pct:.1f}%", f"{proj_pos_pct - base_pos:+.1f} pts")
        r3.metric("Customers retained", f"{rescued:,}", f"-{rescued / max(1, n_neg) * 100:.1f}% complaints", delta_color="inverse")

        g1, g2 = st.columns([1.3, 1], gap="medium")
        with g1:
            with st.container(border=True):
                card_title("Before vs after", "Review counts today and after the fixes.")
                cats = ["Negative reviews", "Positive reviews"]
                fig = go.Figure()
                fig.add_bar(name="Current", x=cats, y=[n_neg, pos_count], marker_color="#94A3B8",
                            text=[f"{n_neg:,}", f"{pos_count:,}"], textposition="outside")
                fig.add_bar(name="After fixes", x=cats, y=[proj_neg, proj_pos], marker_color=BRAND,
                            text=[f"{proj_neg:,}", f"{proj_pos:,}"], textposition="outside")
                fig.update_layout(barmode="group", bargap=0.35)
                fig.update_yaxes(range=[0, max(n_neg, proj_pos, pos_count, 1) * 1.2])
                fig.update_xaxes(showgrid=False)
                show_chart(fig, height=300)
        with g2:
            with st.container(border=True):
                card_title("Where the gain comes from", "Complaints resolved by each lever.")
                contrib = pd.Series({k: v * 0.72 for k, v in resolved.items()}).sort_values()
                fig = go.Figure(go.Bar(
                    x=contrib.values, y=[short(SIM_LEVERS[k][1]) for k in contrib.index], orientation="h",
                    marker_color=[TOPIC_COLORS[SIM_LEVERS[k][1]] for k in contrib.index],
                    text=[f"{v:,.0f}" for v in contrib.values], textposition="outside",
                    hovertemplate="%{x:,.0f} complaints resolved<extra></extra>",
                ))
                fig.update_xaxes(range=[0, max(contrib.max() * 1.3, 1)])
                fig.update_yaxes(showgrid=False, tickfont=dict(size=11))
                show_chart(fig, height=300)

        lv = {k: st.session_state[k] for k in SIM_LEVERS}
        html(
            f"<div class='callout indigo'><b>Summary for leadership:</b> improving delivery SLA compliance by "
            f"<b>{lv['lever_delivery']}%</b> and dispute resolution by <b>{lv['lever_refund']}%</b>, alongside the pricing "
            f"and support levers, would retain about <b>{rescued:,} customers</b> and lift the rating from "
            f"<b>{base_avg:.2f}</b> to <b>{proj_score:.2f}</b> stars.</div>"
        )

# ---------------------------------------------------------------------
# TAB 3: STRATEGY PLAYBOOK
# ---------------------------------------------------------------------
with tab_playbook:
    top_l, top_r = st.columns([2, 1])
    with top_l:
        html("""
            <div class="card-title" style="font-size:18px;">Strategic interventions</div>
            <div class="card-sub">Four initiatives, each linked to the complaint domain it addresses. Percentages are live from the full dataset.</div>
        """)
    with top_r:
        order = st.radio("Order by", ["Biggest impact first", "Original order"], horizontal=True, key="pb_order")

    items = list(PLAYBOOK)
    if order == "Biggest impact first":
        items.sort(key=lambda it: platform_share[it["topic"]], reverse=True)

    cols = st.columns(2, gap="medium")
    for i, it in enumerate(items):
        share = platform_share[it["topic"]]
        actions = "".join(f"<li><b>{a}:</b> {d}</li>" for a, d in it["actions"])
        html(f"""
            <div class="play-card" style="border-left: 4px solid {it['color']};">
              <div class="play-head">
                <span class="chip" style="background:{it['bg']}; color:{it['color']};">{it['area']}</span>
                <span class="impact">Addresses {share:.0f}% of complaints</span>
              </div>
              <h4>{it['title']}</h4>
              <p>{it['insight'].format(share=share)}</p>
              <ul>{actions}</ul>
            </div>
        """, target=cols[i % 2])

# ---------------------------------------------------------------------
# TAB 4: REVIEW EXPLORER
# ---------------------------------------------------------------------
with tab_explorer:
    if fdf.empty:
        st.warning(EMPTY_MSG)
    else:
        s1, s2, s3 = st.columns([2.2, 1.2, 1], gap="medium")
        query = s1.text_input("Search reviews", placeholder="e.g. late, cold, discount, refund", key="ex_query")
        sort_by = s2.selectbox("Sort by", ["Original order", "Lowest rating first", "Highest rating first"], key="ex_sort")
        with s3:
            st.write("")
            show_tags = st.toggle("Show domain tags", value=True, key="ex_tags")

        view = fdf
        if query.strip():
            view = view[view["clean_content"].str.contains(query.strip().lower(), regex=False)]
        if sort_by == "Lowest rating first":
            view = view.sort_values("score", kind="stable")
        elif sort_by == "Highest rating first":
            view = view.sort_values("score", ascending=False, kind="stable")

        st.caption(f"{len(view):,} reviews match")

        display_cols = ["reviewId", "score", "sentiment", "content"]
        if "review_date" in view.columns:
            display_cols.insert(1, "review_date")
        if show_tags:
            display_cols += TOPICS

        col_cfg = {
            "reviewId": st.column_config.Column("ID"),
            "review_date": st.column_config.DatetimeColumn("Date", format="DD MMM YYYY"),
            "score": st.column_config.NumberColumn("Rating", format="%d ★"),
            "sentiment": st.column_config.TextColumn("Sentiment"),
            "content": st.column_config.TextColumn("Review", width="large"),
        }
        col_cfg.update({t: st.column_config.CheckboxColumn(t.split(" & ")[0]) for t in TOPICS})

        st.dataframe(view[display_cols], column_config=col_cfg, hide_index=True, height=420, **FULL["dataframe"])

        export_cols = [c for c in view.columns if c != "clean_content"]
        d1, d2, d3 = st.columns(3, gap="medium")
        d1.download_button(
            "Download current view (CSV)", view[export_cols].to_csv(index=False).encode("utf-8"),
            file_name="swiggy_tapmi_filtered_analysis.csv", mime="text/csv", type="primary", **FULL["download_button"],
        )
        d2.download_button(
            "Download full dataset (CSV)", df[export_cols].to_csv(index=False).encode("utf-8"),
            file_name="swiggy_tapmi_full_dataset.csv", mime="text/csv", **FULL["download_button"],
        )
        if d3.button("Show a random review", disabled=view.empty, **FULL["button"]):
            st.session_state.spot_idx = int(np.random.default_rng().choice(view.index))

        spot = st.session_state.get("spot_idx")
        if spot is not None and spot in view.index:
            row = view.loc[spot]
            tags = ", ".join(t for t in TOPICS if row[t]) or "no domain tag"
            color = SENTIMENT_COLORS[row["sentiment"]]
            html(f"""
                <div class="spot" style="border-left: 4px solid {color};">
                  <div class="meta"><b style="color:{color};">{row['sentiment']}</b> | {row['score']} star | {tags}</div>
                  <div class="text">“{escape(str(row['content']))}”</div>
                </div>
            """)
