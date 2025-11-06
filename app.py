# app.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh
from token_utils import load_credentials_from_gsheet
from data_fetcher import fetch_sector_stock_changes
from sector_logic import identify_exceptions
import gspread
from google.oauth2.service_account import Credentials
from kiteconnect import KiteConnect, exceptions as kite_ex
from typing import Tuple, Optional

# ------------------------------------------------------------------------------------
# Page configuration & styling
# ------------------------------------------------------------------------------------
st.set_page_config(
    page_title="📊 Sector-Wise Exception Tracker",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📈",
)

st.markdown(
    """
    <style>
        body {background-color: #0e1117; color: white;}
        .stDataFrame {background-color: #0e1117; color: white; font-size: 18px;}
        div.row-widget.stRadio > div{flex-direction:row;}
        .ok-badge {background: #143d1f; color: #a7f3d0; padding: 2px 8px; border-radius: 6px; font-size: 0.85rem;}
        .warn-badge {background: #3a2e14; color: #fde68a; padding: 2px 8px; border-radius: 6px; font-size: 0.85rem;}
        .err-badge {background: #431515; color: #fecaca; padding: 2px 8px; border-radius: 6px; font-size: 0.85rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------------------------
# Time helpers
# ------------------------------------------------------------------------------------
IST = timezone(timedelta(hours=5, minutes=30))
def now_ist() -> datetime:
    return datetime.now(IST)

def fmt_ist(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S IST")

def parse_iso_aware(ts: str) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat(ts)
        if d.tzinfo is None:
            d = d.replace(tzinfo=IST)
        return d.astimezone(IST)
    except Exception:
        return None

# ------------------------------------------------------------------------------------
# Auto-refresh every 60s (configurable in sidebar)
# ------------------------------------------------------------------------------------
refresh_secs = st.sidebar.slider("Auto-refresh (seconds)", 15, 300, 60)
st_autorefresh(interval=refresh_secs * 1000, key="auto_refresh")

# ------------------------------------------------------------------------------------
# Title & server time
# ------------------------------------------------------------------------------------
st.title("📊 Sector-Wise Exception Tracker")
st.caption(f"🕒 Server time: {fmt_ist(now_ist())}")

# ------------------------------------------------------------------------------------
# CACHED HELPERS
# ------------------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def get_gspread_client() -> gspread.client.Client:
    """
    Build a read/write gspread client from Streamlit secrets.
    Expects st.secrets['gcreds'] (service account JSON dict).
    """
    # Prefer native google.oauth2 (less brittle than gspread.service_account_from_dict in Streamlit)
    sa = st.secrets.get("gcreds", None)
    if not sa:
        raise RuntimeError("gcreds not found in st.secrets")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_info(sa, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=3600, show_spinner=False)
def get_watchlist_sheet(gc: gspread.client.Client):
    try:
        sh = gc.open("SectorWatchlist")
        return sh.sheet1
    except Exception as e:
        # Propagate: the caller will handle and degrade gracefully
        raise RuntimeError(f"Failed opening 'SectorWatchlist': {e}")

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_existing_watchlist(sheet) -> list:
    try:
        vals = sheet.col_values(1)
        if not vals:
            return []
        header = vals[0].strip().lower() if vals else "script"
        data = vals[1:] if len(vals) > 1 else []
        return [v.strip() for v in data if v.strip()]
    except Exception as e:
        raise RuntimeError(f"Reading watchlist failed: {e}")

@st.cache_data(ttl=3600, show_spinner=False)
def read_meta_last_updated(gc: gspread.client.Client) -> Optional[str]:
    """
    Optional: reads SectorExceptionLog -> Meta sheet -> first row col 'last_updated_ist'
    If not present, returns None (UI will fall back to 'data as of server time').
    """
    try:
        sh = gc.open("SectorExceptionLog")
        ws = sh.worksheet("Meta")
        recs = ws.get_all_records()
        if recs and "last_updated_ist" in recs[0]:
            return str(recs[0]["last_updated_ist"]).strip()
        return None
    except Exception:
        return None

@st.cache_data(ttl=3600, show_spinner=False)
def build_kite(api_key: str, access_token: str) -> KiteConnect:
    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)
    return kite

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_instruments_safe(kite: KiteConnect) -> pd.DataFrame:
    """
    Instruments list changes rarely. Cache for an hour.
    """
    data = kite.instruments("NSE")
    return pd.DataFrame(data)

@st.cache_data(ttl=60, show_spinner=False)
def fetch_data_cached(api_key: str, access_token: str):
    """
    60s TTL to keep data fresh but avoid hammering sources.
    Assumes fetch_sector_stock_changes returns an iterable/dict list.
    """
    return fetch_sector_stock_changes(api_key, access_token)

# ------------------------------------------------------------------------------------
# 1) Load credentials (no caching; fail loud if missing)
# ------------------------------------------------------------------------------------
credentials = load_credentials_from_gsheet()
if not credentials:
    st.error("❌ Failed to load Zerodha credentials from Google Sheet (A1=API Key, B1=Secret, C1=Access Token).")
    st.stop()
api_key, api_secret, access_token = credentials

# ------------------------------------------------------------------------------------
# 2) Validate token / warm up Kite (fail loud, but don't poison cache)
# ------------------------------------------------------------------------------------
try:
    kite = build_kite(api_key, access_token)
    # Lightweight validity check: attempt a tiny instruments fetch (raises on invalid token)
    _ = kite.instruments("NSE")[:1]
except kite_ex.TokenException as e:
    st.error(f"❌ Invalid/expired access token. {e}. Please refresh your Zerodha token (C1) and reload.")
    st.stop()
except Exception as e:
    st.error(f"❌ Zerodha connectivity error: {e}")
    st.stop()

# ------------------------------------------------------------------------------------
# 3) Read optional data "freshness" meta
# ------------------------------------------------------------------------------------
meta_badge = ""
last_updated_text = None
try:
    gc = get_gspread_client()
    last_updated_text = read_meta_last_updated(gc)
except Exception as e:
    # Meta is optional; don't kill the app
    last_updated_text = None

if last_updated_text:
    ts = parse_iso_aware(last_updated_text)
    if ts:
        age_sec = int((now_ist() - ts).total_seconds())
        if age_sec <= 120:
            badge = f"<span class='ok-badge'>Live (Δ {age_sec}s)</span>"
        elif age_sec <= 600:
            badge = f"<span class='warn-badge'>Warm (Δ {age_sec}s)</span>"
        else:
            badge = f"<span class='err-badge'>Stale (Δ {age_sec}s)</span>"
        st.markdown(f"**Data as of:** {fmt_ist(ts)} &nbsp; {badge}", unsafe_allow_html=True)
    else:
        st.markdown(f"**Data as of:** {last_updated_text} &nbsp; <span class='warn-badge'>Unparsed timestamp</span>", unsafe_allow_html=True)
else:
    st.markdown(f"**Data as of:** (no meta timestamp found) &nbsp; <span class='warn-badge'>Unknown</span>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------------
# 4) Instruments & Watchlist (robust; won't crash if Sheet missing)
# ------------------------------------------------------------------------------------
all_symbols = []
watchlist_sheet = None
existing_watchlist = []

# Instruments (cached)
try:
    instruments_df = fetch_instruments_safe(kite)
    # Use segment filter if present
    if "segment" in instruments_df.columns:
        instruments_df = instruments_df[instruments_df["segment"] == "NSE"]
    if "tradingsymbol" in instruments_df.columns:
        all_symbols = sorted(set(instruments_df["tradingsymbol"].astype(str)))
    else:
        all_symbols = []
except Exception as e:
    st.warning(f"⚠️ Could not fetch instruments list: {e}. Symbol picker disabled.")
    all_symbols = []

# Watchlist (cached)
try:
    watchlist_sheet = get_watchlist_sheet(gc)
    existing_watchlist = fetch_existing_watchlist(watchlist_sheet)
except Exception as e:
    st.warning(f"⚠️ Watchlist not available: {e}")
    existing_watchlist = []

# Multiselect with safe default
safe_existing_watchlist = [s for s in existing_watchlist if s in all_symbols] if all_symbols else existing_watchlist
selected_scripts = st.multiselect(
    "🔎 Search and Add Scripts to Watchlist:",
    options=all_symbols if all_symbols else safe_existing_watchlist,
    default=safe_existing_watchlist,
)

col_a, col_b, col_c = st.columns([1,1,2])
with col_a:
    if st.button("💾 Save Watchlist", use_container_width=True, type="primary", disabled=watchlist_sheet is None):
        if watchlist_sheet is None:
            st.error("❌ Watchlist sheet unavailable. Cannot save.")
        else:
            try:
                # Clear and write fresh
                data = [['Script']] + [[s] for s in selected_scripts]
                watchlist_sheet.clear()
                watchlist_sheet.update(data)
                st.success("✅ Watchlist saved.")
                # Invalidate caches that depend on this
                fetch_existing_watchlist.clear()
            except Exception as e:
                st.error(f"❌ Failed to save watchlist: {e}")

with col_b:
    if st.button("🔄 Refresh now", use_container_width=True):
        # Clear only our data caches; do not clear credentials
        fetch_data_cached.clear()
        fetch_instruments_safe.clear()
        st.rerun()

if selected_scripts:
    st.success(f"📋 Current Watchlist: {', '.join(selected_scripts)}")
else:
    st.info("ℹ️ Add scripts to your watchlist to focus the analysis. The app will still fetch market data.")

# ------------------------------------------------------------------------------------
# 5) Threshold
# ------------------------------------------------------------------------------------
threshold = st.slider("📈 Exception Threshold (%)", min_value=0.5, max_value=5.0, step=0.5, value=2.0)

# ------------------------------------------------------------------------------------
# 6) Fetch market data (cached 60s). Fail loud but don't cache failures.
# ------------------------------------------------------------------------------------
try:
    raw_result = fetch_data_cached(api_key, access_token)
except kite_ex.TokenException as e:
    fetch_data_cached.clear()
    st.error(f"❌ Live fetch failed (token): {e}. Please refresh access token.")
    st.stop()
except Exception as e:
    fetch_data_cached.clear()
    st.error(f"❌ Live fetch failed: {e}")
    st.stop()

# ------------------------------------------------------------------------------------
# 7) Transform & display
# ------------------------------------------------------------------------------------
sector_df = pd.DataFrame(raw_result) if raw_result is not None else pd.DataFrame()

if not sector_df.empty:
    # Expected keys from fetch_sector_stock_changes: ['symbol','sector','%change', ...]
    rename_map = {"symbol": "Stock", "sector": "Sector", "%change": "Stock % Change"}
    present_keys = {k for k in rename_map if k in sector_df.columns}
    sector_df = sector_df.rename(columns={k: rename_map[k] for k in present_keys})

    # Filter to selected watchlist if provided
    if selected_scripts:
        sector_df = sector_df[sector_df["Stock"].isin(selected_scripts)] if "Stock" in sector_df.columns else sector_df

    # Sector averages
    if "Sector" in sector_df.columns and "Stock % Change" in sector_df.columns:
        sector_avg_map = sector_df.groupby("Sector")["Stock % Change"].mean().to_dict()
        sector_df["Sector % Change"] = sector_df["Sector"].map(sector_avg_map)
    else:
        st.warning("⚠️ Missing columns required for sector averages. Check your data_fetcher output.")
    
    # Identify exceptions
    try:
        result_df = identify_exceptions(sector_df, threshold=threshold)
    except Exception as e:
        st.error(f"❌ Exception identification failed: {e}")
        st.stop()

    st.subheader("📋 Sector Divergence Summary")

    def highlight_exceptions(row):
        return [
            'background-color: #ffcccc' if row.get('Exception', False) else ''
            for _ in row.index
        ]

    def color_numbers(val):
        if isinstance(val, (float, int)):
            if val > 0:
                return 'color: green;'
            if val < 0:
                return 'color: red;'
        return ''

    # Format & style
    show_cols = []
    for col in ["Stock", "Sector", "Stock % Change", "Sector % Change", "Delta %", "Exception"]:
        if col in result_df.columns:
            show_cols.append(col)
    display_df = result_df[show_cols].copy() if show_cols else result_df

    styled_df = (
        display_df.style
        .format({"Stock % Change": "{:.2f}", "Sector % Change": "{:.2f}", "Delta %": "{:.2f}"})
        .apply(highlight_exceptions, axis=1)
        .applymap(color_numbers)
        .set_table_styles(
            [
                {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#12151c')]},
                {'selector': 'tbody tr:nth-child(odd)', 'props': [('background-color', '#0e1117')]}
            ],
            overwrite=False
        )
    )

    st.dataframe(styled_df, use_container_width=True)
else:
    st.info("✅ Live fetch returned no rows at the moment (or filter removed all). Try broadening your watchlist or lowering the threshold.")
