import streamlit as st
import pandas as pd
import numpy as np
import time
import plotly.express as px
import warnings
import os
import hashlib
from datetime import datetime

warnings.filterwarnings("ignore")

# ==================== COMPATIBILITY HELPER ====================
def safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

# ==================== APP CONFIG ====================
DEPLOYMENT_MODE = os.environ.get("DEPLOYMENT_MODE", "development")
APP_VERSION = "2.1.4"
APP_NAME = "Sentiment Analysis Dashboard"

MAX_LOGIN_ATTEMPTS = 3
SESSION_TIMEOUT_MINUTES = 60

def load_config():
    return {
        "COMMON_PASSWORD": os.environ.get("APP_PASSWORD", "sentiment2024"),
        "ALLOWED_USERS": [u.strip().lower() for u in os.environ.get("ALLOWED_USERS", "admin,analyst,user").split(",")],
        "ADMIN_USERS": [u.strip().lower() for u in os.environ.get("ADMIN_USERS", "admin").split(",")],
        "MAX_FILE_SIZE_MB": int(os.environ.get("MAX_FILE_SIZE_MB", 10)),
        "ALLOWED_FILE_TYPES": ["csv", "xlsx", "xls"],
    }

config = load_config()

# ==================== THEME COLORS (SIMPLE) ====================
def get_theme_colors(theme: str):
    if theme == "dark":
        return {
            "primary": "#4285F4",
            "secondary": "#34A853",
            "accent": "#EA4335",
            "warning": "#FBBC05",
            "neutral": "#9AA0A6",
            "background": "#0E1117",
            "card": "#1E2126",
            "text": "#FAFAFA",
            "text_light": "#B0B3B8",
            "success": "#34A853",
            "danger": "#EA4335",
            "border": "#2D3748",
            "hover": "#2A2D35",
        }
    return {
        "primary": "#4285F4",
        "secondary": "#34A853",
        "accent": "#EA4335",
        "warning": "#FBBC05",
        "neutral": "#9AA0A6",
        "background": "#F8F9FA",
        "card": "#FFFFFF",
        "text": "#202124",
        "text_light": "#5F6368",
        "success": "#34A853",
        "danger": "#EA4335",
        "border": "#DADCE0",
        "hover": "#F1F3F4",
    }

SENTIMENT_COLORS = {
    "Positive": "#34A853",
    "Neutral": "#9AA0A6",
    "Negative": "#EA4335",
}

# ==================== SECURITY HELPERS ====================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def update_activity():
    st.session_state.last_activity = datetime.now()

def check_session_timeout() -> bool:
    if "last_activity" in st.session_state and st.session_state.last_activity:
        diff = datetime.now() - st.session_state.last_activity
        if diff.total_seconds() > SESSION_TIMEOUT_MINUTES * 60:
            logout()
            return True
    return False

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title=f"{APP_NAME} v{APP_VERSION}",
    page_icon="icon.png",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": f"""
### {APP_NAME} v{APP_VERSION}

Deployment Mode: {DEPLOYMENT_MODE}
Security: Password protected
Features: Upload, analysis, export
""",
    },
)

# ==================== SESSION STATE INIT ====================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None
if "user_role" not in st.session_state:
    st.session_state.user_role = "user"
if "login_attempts" not in st.session_state:
    st.session_state.login_attempts = {}
if "last_activity" not in st.session_state:
    st.session_state.last_activity = datetime.now()
if "session_id" not in st.session_state:
    st.session_state.session_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]

if "current_theme" not in st.session_state:
    st.session_state.current_theme = "light"

default_states = {
    "df": None,
    "file_name": None,
    "text_column": None,
    "data_loaded": False,
    "analysis_complete": False,
    "results_df": None,
    "analysis_history": [],
    "export_history": [],
    "analysis_engine": "TextBlob",
    "language_mode": "Auto-detect",
    "sentiment_threshold": 0.3,
}
for k, v in default_states.items():
    if k not in st.session_state:
        st.session_state[k] = v

COLORS = get_theme_colors(st.session_state.current_theme)

# ==================== STYLES (LOGIN MATCHES YOUR EXAMPLE) ====================
st.markdown(
    f"""
<style>
:root {{
    --primary: {COLORS["primary"]};
    --secondary: {COLORS["secondary"]};
    --accent: {COLORS["accent"]};
    --warning: {COLORS["warning"]};
    --neutral: {COLORS["neutral"]};
    --bg: {COLORS["background"]};
    --card: {COLORS["card"]};
    --text: {COLORS["text"]};
    --text2: {COLORS["text_light"]};
    --success: {COLORS["success"]};
    --danger: {COLORS["danger"]};
    --border: {COLORS["border"]};
    --hover: {COLORS["hover"]};

    --pos: {SENTIMENT_COLORS["Positive"]};
    --neu: {SENTIMENT_COLORS["Neutral"]};
    --neg: {SENTIMENT_COLORS["Negative"]};
}}

.stApp {{
    background: var(--bg);
    color: var(--text);
    font-family: "Google Sans", "Roboto", system-ui, -apple-system, "Segoe UI", sans-serif;
}}

#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
.stDeployButton {{ display: none; }}

/* Login screen */
.login-container {{
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:100vh;
    padding: 2rem;
    background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
}}
.login-card {{
    background: var(--card);
    border-radius: 12px;
    padding: 3rem;
    width: 100%;
    max-width: 420px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.15);
    border: 1px solid var(--border);
    color: var(--text);
}}
.security-badge {{
    display:inline-flex;
    align-items:center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    background: rgba(52,168,83,0.15);
    color: var(--success);
    border: 1px solid rgba(52,168,83,0.3);
}}
.google-logo {{
    width: 80px;
    height: 80px;
    margin: 0 auto 1.5rem;
    background: linear-gradient(135deg, var(--primary), var(--secondary), var(--warning), var(--accent));
    border-radius: 50%;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size: 2.2rem;
    color: #fff;
    font-weight: 700;
    box-shadow: 0 4px 12px rgba(66,133,244,0.3);
}}
.login-title {{
    font-size: 28px;
    font-weight: 400;
    text-align:center;
    margin: 0 0 0.5rem 0;
}}
.login-subtitle {{
    text-align:center;
    margin: 0 0 2.5rem 0;
    font-size: 15px;
    line-height: 1.5;
    color: var(--text2);
}}

/* App header */
.header-container {{
    background: var(--card);
    border-bottom: 1px solid var(--border);
    padding: 1.2rem 2.2rem;
    margin: -2rem -1rem 1.5rem -1rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}}
.user-chip {{
    display:flex;
    align-items:center;
    gap: 10px;
    background: var(--bg);
    padding: 10px 16px;
    border-radius: 24px;
    border: 1px solid var(--border);
    font-size: 14px;
    font-weight: 500;
}}
.user-avatar {{
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--primary), var(--secondary));
    color: #fff;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size: 14px;
    font-weight: 700;
}}

.g-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 22px;
    margin-bottom: 18px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}}
.g-card-header {{
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
    gap: 12px;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 16px;
}}
.g-card-title {{
    font-size: 20px;
    font-weight: 600;
    margin: 0 0 6px 0;
}}
.g-card-subtitle {{
    font-size: 14px;
    margin: 0;
    line-height: 1.5;
    color: var(--text2);
}}

.metric-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 18px;
    text-align:center;
    min-height: 120px;
    display:flex;
    flex-direction:column;
    justify-content:center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}}
.metric-label {{
    font-size: 12px;
    color: var(--text2);
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 600;
}}
.metric-value {{
    font-size: 30px;
    font-weight: 500;
    margin: 8px 0 4px 0;
}}
.metric-status {{
    font-size: 11px;
    color: var(--text2);
    font-weight: 600;
}}

.stButton > button {{
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 600;
}}

.security-warning {{
    background: rgba(251,188,5,0.15);
    border: 1px solid rgba(251,188,5,0.3);
    border-radius: 8px;
    padding: 14px;
    margin: 14px 0;
    color: var(--warning);
    font-size: 13px;
    line-height: 1.5;
}}
</style>
""",
    unsafe_allow_html=True,
)

# ==================== AUTH ====================
def check_password(username: str, password: str):
    username = (username or "").strip().lower()

    if username in st.session_state.login_attempts:
        attempts, last_attempt = st.session_state.login_attempts[username]
        seconds = (datetime.now() - last_attempt).total_seconds()
        if attempts >= MAX_LOGIN_ATTEMPTS and seconds < 300:
            return False, "Too many failed attempts. Try again later."

    if username and password == config["COMMON_PASSWORD"]:
        if username in st.session_state.login_attempts:
            del st.session_state.login_attempts[username]

        if username in config["ADMIN_USERS"]:
            role = "admin"
        elif username in config["ALLOWED_USERS"]:
            role = "user"
        else:
            role = "guest"

        return True, role

    if username not in st.session_state.login_attempts:
        st.session_state.login_attempts[username] = [1, datetime.now()]
    else:
        st.session_state.login_attempts[username][0] += 1
        st.session_state.login_attempts[username][1] = datetime.now()

    return False, "Invalid credentials"

def logout():
    st.session_state.analysis_history.append(
        {"timestamp": datetime.now().isoformat(), "username": st.session_state.username, "action": "logout"}
    )

    for key in ["df", "file_name", "text_column", "results_df", "data_loaded", "analysis_complete"]:
        st.session_state[key] = default_states.get(key)

    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.user_role = "user"
    st.session_state.session_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
    safe_rerun()

def show_login_page():
    st.markdown('<div class="login-container"><div class="login-card">', unsafe_allow_html=True)

    st.markdown(
        """
        <div style="text-align:center; margin-bottom: 1rem;">
            <span class="security-badge">Secure Login</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="google-logo">SA</div>', unsafe_allow_html=True)
    st.markdown(f'<h1 class="login-title">Sign in to {APP_NAME}</h1>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <p class="login-subtitle">
            Enter your credentials to access the dashboard.<br>
            <span style="font-size: 12px; opacity: 0.85;">
                Deployment: <strong>{DEPLOYMENT_MODE.upper()}</strong> | Version: {APP_VERSION}
            </span>
        </p>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submit = st.form_submit_button("Sign In", type="primary", use_container_width=True)

    if submit:
        if not (username or "").strip():
            st.error("Enter a username.")
        else:
            ok, role_or_msg = check_password(username, password)
            if ok:
                st.session_state.authenticated = True
                st.session_state.username = username.strip().lower()
                st.session_state.user_role = role_or_msg
                update_activity()

                st.session_state.analysis_history.append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "username": st.session_state.username,
                        "action": "login",
                        "role": st.session_state.user_role,
                    }
                )
                st.success(f"Welcome, {st.session_state.username}.")
                time.sleep(0.6)
                safe_rerun()
            else:
                st.error(role_or_msg)

    st.markdown(
        f"""
        <div style="margin-top: 26px; padding-top: 16px; border-top: 1px solid var(--border); text-align:center;">
            <div style="color: var(--text2); font-size: 12px;">
                <div><strong>{APP_NAME} v{APP_VERSION}</strong></div>
                <div style="font-size: 11px; opacity: 0.85; margin-top: 6px;">
                    Unauthorized access is prohibited
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div></div>", unsafe_allow_html=True)

# ==================== SECURITY MIDDLEWARE ====================
if st.session_state.authenticated and check_session_timeout():
    st.warning("Session timed out. Sign in again.")
    st.stop()

if st.session_state.authenticated:
    update_activity()

if not st.session_state.authenticated:
    show_login_page()
    st.stop()

# ==================== HEADER ====================
st.markdown(
    f"""
<div class="header-container">
  <div style="display:flex; justify-content:space-between; align-items:center; gap: 16px;">
    <div>
      <div style="font-size: 22px; font-weight: 700; color: var(--primary);">{APP_NAME}</div>
      <div style="font-size: 13px; color: var(--text2);">v{APP_VERSION} • {DEPLOYMENT_MODE.title()} Mode</div>
    </div>
    <div class="user-chip">
      <div class="user-avatar">{st.session_state.username[0].upper()}</div>
      <div>
        <div style="font-weight: 700;">{st.session_state.username}</div>
        <div style="font-size: 11px; color: var(--text2); font-weight: 700;">
          {st.session_state.user_role.upper()} • Session: {st.session_state.session_id}
        </div>
      </div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

top_a, top_b, top_c = st.columns([3, 2, 3])
with top_b:
    if st.button("Secure Logout", use_container_width=True):
        logout()

# ==================== SIDEBAR (SIMPLE) ====================
with st.sidebar:
    st.markdown("### Settings")

    st.session_state.analysis_engine = st.selectbox(
        "Analysis engine",
        ["TextBlob", "Simple"],
        index=0 if st.session_state.analysis_engine == "TextBlob" else 1,
    )

    st.session_state.language_mode = st.selectbox(
        "Language handling",
        ["Auto-detect", "English Only", "Multi-language"],
        index=["Auto-detect", "English Only", "Multi-language"].index(st.session_state.language_mode),
    )

    st.session_state.sentiment_threshold = st.slider(
        "Sentiment threshold",
        0.0,
        1.0,
        float(st.session_state.sentiment_threshold),
        0.05,
    )

    st.markdown("---")
    if st.button("Clear loaded data", use_container_width=True):
        st.session_state.df = None
        st.session_state.file_name = None
        st.session_state.text_column = None
        st.session_state.data_loaded = False
        st.session_state.analysis_complete = False
        st.session_state.results_df = None
        safe_rerun()

# ==================== SIMPLE SENTIMENT ====================
def simple_sentiment_score(text: str) -> float:
    if not isinstance(text, str) or not text.strip():
        return 0.0
    t = text.lower()
    pos = ["good", "great", "love", "excellent", "amazing", "happy", "nice", "best", "awesome"]
    neg = ["bad", "hate", "terrible", "worst", "awful", "sad", "poor", "angry", "horrible"]
    score = 0
    for w in pos:
        score += t.count(w)
    for w in neg:
        score -= t.count(w)
    if score == 0:
        return 0.0
    return max(-1.0, min(1.0, score / 5.0))

def run_sentiment(df: pd.DataFrame, text_col: str, threshold: float, engine: str) -> pd.DataFrame:
    out = df.copy()
    series = out[text_col].astype(str)

    if engine == "TextBlob":
        try:
            from textblob import TextBlob  # optional dependency
            out["sentiment_score"] = series.apply(lambda x: float(TextBlob(x).sentiment.polarity))
        except Exception:
            out["sentiment_score"] = series.apply(simple_sentiment_score)
            st.warning("TextBlob not available. Using Simple engine.")
    else:
        out["sentiment_score"] = series.apply(simple_sentiment_score)

    out["sentiment_category"] = np.where(
        out["sentiment_score"] > threshold,
        "Positive",
        np.where(out["sentiment_score"] < -threshold, "Negative", "Neutral"),
    )
    out["analysis_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out["analysis_engine"] = engine
    out["analyzed_by"] = st.session_state.username
    return out

# ==================== TWO TABS ONLY ====================
tab_upload, tab_results = st.tabs(["Data Upload", "Results and Export"])

with tab_upload:
    st.markdown(
        """
        <div class="g-card">
            <div class="g-card-header">
                <div>
                    <div class="g-card-title">Secure Data Upload</div>
                    <p class="g-card-subtitle">Upload a CSV or Excel file, select the text column, then run analysis.</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=config["ALLOWED_FILE_TYPES"],
        label_visibility="visible",
        help=f"Max size: {config['MAX_FILE_SIZE_MB']}MB",
    )

    if uploaded_file is not None:
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        if file_size_mb > config["MAX_FILE_SIZE_MB"]:
            st.error(f"File too large: {file_size_mb:.1f}MB. Max is {config['MAX_FILE_SIZE_MB']}MB.")
        else:
            try:
                if uploaded_file.name.lower().endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)

                st.session_state.df = df
                st.session_state.file_name = uploaded_file.name
                st.session_state.data_loaded = True
                st.session_state.analysis_complete = False
                st.session_state.results_df = None

                st.session_state.analysis_history.append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "username": st.session_state.username,
                        "action": "upload",
                        "filename": uploaded_file.name,
                        "size_mb": round(file_size_mb, 2),
                        "rows": int(len(df)),
                        "columns": int(len(df.columns)),
                    }
                )

                st.markdown(
                    f"""
                    <div class="g-card">
                        <div class="g-card-header">
                            <div>
                                <div class="g-card-title" style="color: var(--success);">File loaded</div>
                                <p class="g-card-subtitle">{uploaded_file.name}</p>
                            </div>
                            <span class="security-badge">Secured</span>
                        </div>
                        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap: 14px;">
                            <div class="metric-card">
                                <div class="metric-label">Rows</div>
                                <div class="metric-value">{len(df):,}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Columns</div>
                                <div class="metric-value">{len(df.columns):,}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">File size</div>
                                <div class="metric-value">{file_size_mb:.1f} MB</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown(
                    """
                    <div class="g-card">
                        <div class="g-card-header">
                            <div>
                                <div class="g-card-title">Preview</div>
                                <p class="g-card-subtitle">First 10 rows</p>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.dataframe(df.head(10), use_container_width=True, hide_index=True)

                st.markdown(
                    """
                    <div class="g-card">
                        <div class="g-card-header">
                            <div>
                                <div class="g-card-title">Configure analysis</div>
                                <p class="g-card-subtitle">Pick the column that contains the text you want to score.</p>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.session_state.text_column = st.selectbox(
                    "Text column",
                    options=df.columns.tolist(),
                    index=0,
                )

                sample_mode = st.checkbox("Analyze a sample (faster)", value=False)
                sample_n = 500
                if sample_mode:
                    sample_n = st.slider("Sample size", 100, min(5000, len(df)), min(500, len(df)))

                run_col1, run_col2, run_col3 = st.columns([1, 2, 1])
                with run_col2:
                    if st.button("Run analysis", type="primary", use_container_width=True):
                        if st.session_state.text_column is None:
                            st.error("Select a text column.")
                        else:
                            df_to_use = df.head(sample_n).copy() if sample_mode else df.copy()

                            progress = st.progress(0)
                            status = st.empty()

                            steps = [
                                ("Preparing data", 20),
                                ("Scoring sentiment", 60),
                                ("Finalizing output", 100),
                            ]
                            for label, pct in steps:
                                time.sleep(0.25)
                                progress.progress(pct)
                                status.markdown(f"<div style='color: var(--text); font-weight: 700;'>{label}</div>", unsafe_allow_html=True)

                            results = run_sentiment(
                                df=df_to_use,
                                text_col=st.session_state.text_column,
                                threshold=float(st.session_state.sentiment_threshold),
                                engine=st.session_state.analysis_engine,
                            )

                            st.session_state.results_df = results
                            st.session_state.analysis_complete = True

                            st.session_state.analysis_history.append(
                                {
                                    "timestamp": datetime.now().isoformat(),
                                    "username": st.session_state.username,
                                    "action": "analysis_completed",
                                    "engine": st.session_state.analysis_engine,
                                    "rows_analyzed": int(len(results)),
                                    "text_column": st.session_state.text_column,
                                }
                            )

                            st.success("Analysis complete. Open the Results and Export tab.")

            except Exception as e:
                st.error(f"Error loading file: {e}")
                st.session_state.analysis_history.append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "username": st.session_state.username,
                        "action": "error",
                        "detail": str(e),
                        "filename": getattr(uploaded_file, "name", "unknown"),
                    }
                )

with tab_results:
    if not st.session_state.analysis_complete or st.session_state.results_df is None:
        st.markdown(
            """
            <div class="g-card">
                <div class="g-card-header">
                    <div>
                        <div class="g-card-title">No results yet</div>
                        <p class="g-card-subtitle">Upload data and run analysis first.</p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        res = st.session_state.results_df

        counts = res["sentiment_category"].value_counts().reindex(["Positive", "Neutral", "Negative"]).fillna(0).astype(int)
        total = int(len(res))
        pos_pct = int(round((counts.get("Positive", 0) / total) * 100)) if total else 0
        neu_pct = int(round((counts.get("Neutral", 0) / total) * 100)) if total else 0
        neg_pct = int(round((counts.get("Negative", 0) / total) * 100)) if total else 0

        st.markdown(
            """
            <div class="g-card">
                <div class="g-card-header">
                    <div>
                        <div class="g-card-title">Results</div>
                        <p class="g-card-subtitle">Distribution and export options.</p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Records analyzed</div>
                    <div class="metric-value">{total:,}</div>
                    <div class="metric-status">Ready</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Positive</div>
                    <div class="metric-value" style="color: var(--success);">{pos_pct}%</div>
                    <div class="metric-status">{counts.get("Positive", 0):,} rows</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Neutral</div>
                    <div class="metric-value" style="color: var(--neutral);">{neu_pct}%</div>
                    <div class="metric-status">{counts.get("Neutral", 0):,} rows</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Negative</div>
                    <div class="metric-value" style="color: var(--danger);">{neg_pct}%</div>
                    <div class="metric-status">{counts.get("Negative", 0):,} rows</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        chart_df = pd.DataFrame({"Sentiment": counts.index.tolist(), "Count": counts.values.tolist()})
        fig = px.pie(
            chart_df,
            names="Sentiment",
            values="Count",
            color="Sentiment",
            color_discrete_map=SENTIMENT_COLORS,
            hole=0.4,
        )
        fig.update_layout(
            font=dict(family="Google Sans, Roboto, sans-serif", size=14, color=COLORS["text"]),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=420,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            """
            <div class="g-card">
                <div class="g-card-header">
                    <div>
                        <div class="g-card-title">Preview of scored data</div>
                        <p class="g-card-subtitle">Includes sentiment_score and sentiment_category.</p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(res.head(25), use_container_width=True, hide_index=True)

        st.markdown(
            """
            <div class="g-card">
                <div class="g-card-header">
                    <div>
                        <div class="g-card-title">Export</div>
                        <p class="g-card-subtitle">Download summary or full scored dataset.</p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Summary export
        summary = pd.DataFrame(
            {
                "Report Type": ["Sentiment Analysis Summary"],
                "Generated By": [st.session_state.username],
                "Generation Date": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                "Records Analyzed": [total],
                "Positive (%)": [pos_pct],
                "Neutral (%)": [neu_pct],
                "Negative (%)": [neg_pct],
                "Engine": [st.session_state.analysis_engine],
                "Threshold": [st.session_state.sentiment_threshold],
                "Session ID": [st.session_state.session_id],
                "Deployment Mode": [DEPLOYMENT_MODE],
            }
        )

        e1, e2 = st.columns(2)
        with e1:
            st.download_button(
                "Download summary (CSV)",
                data=summary.to_csv(index=False),
                file_name=f"sentiment_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with e2:
            st.download_button(
                "Download full results (CSV)",
                data=res.to_csv(index=False),
                file_name=f"sentiment_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.session_state.export_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "username": st.session_state.username,
                "action": "export_offered",
                "rows": total,
            }
        )

        with st.expander("Audit log"):
            audit_df = pd.DataFrame(st.session_state.analysis_history)
            if audit_df.empty:
                st.info("No activity yet.")
            else:
                st.dataframe(audit_df, use_container_width=True, hide_index=True)

# ==================== FOOTER ====================
st.markdown("---")
st.markdown(
    f"""
<div style="text-align:center; color: var(--text2); font-size: 12px; padding: 12px 0;">
  <div style="font-weight: 700;">{APP_NAME} v{APP_VERSION} • {DEPLOYMENT_MODE.upper()} MODE</div>
  <div style="font-size: 11px; margin-top: 6px;">
    User: {st.session_state.username} • Role: {st.session_state.user_role.upper()} • Session: {st.session_state.session_id}
  </div>
</div>
""",
    unsafe_allow_html=True,
)
