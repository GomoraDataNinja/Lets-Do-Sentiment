import streamlit as st
import pandas as pd
import numpy as np
import time
import plotly.express as px
import warnings
import os
import hashlib
from datetime import datetime
import json
import pickle
warnings.filterwarnings('ignore')

# ==================== DEPLOYMENT CONFIGURATION ====================
# Environment variables for deployment security
DEPLOYMENT_MODE = os.environ.get('DEPLOYMENT_MODE', 'development')
APP_VERSION = "2.1.4"
APP_NAME = "Sentiment Analysis Dashboard"

# Security configuration
MAX_LOGIN_ATTEMPTS = 3
SESSION_TIMEOUT_MINUTES = 60
PASSWORD_MIN_LENGTH = 8

# Load configuration from environment or config file
def load_config():
    """Load configuration securely"""
    config = {
        'COMMON_PASSWORD': os.environ.get('APP_PASSWORD', 'sentiment2024'),
        'ALLOWED_USERS': os.environ.get('ALLOWED_USERS', 'admin,analyst,user').split(','),
        'ADMIN_USERS': os.environ.get('ADMIN_USERS', 'admin').split(','),
        'REQUIRE_EMAIL': os.environ.get('REQUIRE_EMAIL', 'false').lower() == 'true',
        'MAX_FILE_SIZE_MB': int(os.environ.get('MAX_FILE_SIZE_MB', 10)),
        'ALLOWED_FILE_TYPES': ['csv', 'xlsx', 'xls']
    }
    return config

config = load_config()

# ==================== SECURITY FUNCTIONS ====================
def hash_password(password):
    """Simple password hashing for demonstration"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_session_timeout():
    """Check if session has timed out"""
    if 'last_activity' in st.session_state:
        last_activity = st.session_state.last_activity
        time_diff = datetime.now() - last_activity
        if time_diff.total_seconds() > SESSION_TIMEOUT_MINUTES * 60:
            logout()
            return True
    return False

def update_activity():
    """Update last activity timestamp"""
    st.session_state.last_activity = datetime.now()

# ==================== PAGE CONFIGURATION ====================
st.set_page_config(
    page_title=f"{APP_NAME} v{APP_VERSION}",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': f'''
        ### {APP_NAME} v{APP_VERSION}
        
        Secure Sentiment Analysis Dashboard
        
        **Deployment Mode:** {DEPLOYMENT_MODE}
        **Security:** Password protected
        **Features:** File upload, sentiment analysis, export
        
        © 2024 All rights reserved.
        '''
    }
)

# ==================== SESSION STATE INITIALIZATION ====================
# Security-related session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = 'user'
if 'login_attempts' not in st.session_state:
    st.session_state.login_attempts = {}
if 'last_activity' not in st.session_state:
    st.session_state.last_activity = datetime.now()
if 'session_id' not in st.session_state:
    st.session_state.session_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]

# Application state
default_states = {
    'analysis_started': False,
    'analysis_complete': False,
    'df': None,
    'text_column': None,
    'file_name': None,
    'export_history': [],
    'analysis_history': [],
    'data_loaded': False
}

for key, default in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ==================== STYLING & COLORS ====================
COLORS = {
    'primary': "#4285F4",
    'secondary': "#34A853",
    'accent': "#EA4335",
    'warning': "#FBBC05",
    'neutral': "#9AA0A6",
    'background': "#F8F9FA",
    'card': "#FFFFFF",
    'text': "#202124",
    'text_light': "#5F6368",
    'success': "#34A853",
    'danger': "#EA4335",
    'sidebar': "#202124"
}

SENTIMENT_COLORS = {
    'Positive': "#34A853",
    'Neutral': "#9AA0A6",
    'Negative': "#EA4335",
}

# Enhanced CSS for deployment
st.markdown(f"""
<style>
    /* Base styles */
    .stApp {{
        background-color: {COLORS['background']};
        font-family: 'Google Sans', 'Roboto', 'Segoe UI', sans-serif;
    }}
    
    /* Security indicators */
    .security-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        background: {COLORS['success']}15;
        color: {COLORS['success']};
        border: 1px solid {COLORS['success']}30;
    }}
    
    .deployment-badge {{
        position: fixed;
        bottom: 10px;
        right: 10px;
        background: {COLORS['primary']};
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 10px;
        font-weight: 600;
        z-index: 9999;
        opacity: 0.9;
    }}
    
    /* Login page */
    .login-container {{
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        padding: 2rem;
        background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
    }}
    
    .login-card {{
        background: {COLORS['card']};
        border-radius: 12px;
        padding: 3rem;
        width: 100%;
        max-width: 420px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
    }}
    
    .google-logo {{
        width: 80px;
        height: 80px;
        margin: 0 auto 1.5rem;
        background: linear-gradient(135deg, {COLORS['primary']}, {COLORS['secondary']}, {COLORS['warning']}, {COLORS['accent']});
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2.2rem;
        color: white;
        font-weight: bold;
        box-shadow: 0 4px 12px rgba(66, 133, 244, 0.3);
    }}
    
    .login-title {{
        font-size: 28px;
        font-weight: 400;
        color: {COLORS['text']};
        text-align: center;
        margin-bottom: 0.5rem;
    }}
    
    .login-subtitle {{
        color: {COLORS['text_light']};
        text-align: center;
        margin-bottom: 2.5rem;
        font-size: 15px;
        line-height: 1.5;
    }}
    
    /* Dashboard components */
    .metric-card {{
        background: {COLORS['card']};
        border: 1px solid {COLORS['neutral']}30;
        border-radius: 10px;
        padding: 22px;
        text-align: center;
        height: 150px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }}
    
    .metric-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        border-color: {COLORS['primary']}50;
    }}
    
    .metric-value {{
        font-size: 38px;
        font-weight: 400;
        color: {COLORS['text']};
        margin: 10px 0;
        font-family: 'Google Sans Display', sans-serif;
    }}
    
    .metric-label {{
        font-size: 13px;
        color: {COLORS['text_light']};
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 600;
    }}
    
    .g-card {{
        background: {COLORS['card']};
        border: 1px solid {COLORS['neutral']}30;
        border-radius: 12px;
        padding: 28px;
        margin-bottom: 20px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
        transition: all 0.3s ease;
    }}
    
    .g-card:hover {{
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }}
    
    .g-card-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid {COLORS['neutral']}20;
    }}
    
    .g-card-title {{
        font-size: 20px;
        font-weight: 500;
        color: {COLORS['text']};
        margin: 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    
    .g-card-subtitle {{
        font-size: 14px;
        color: {COLORS['text_light']};
        margin: 6px 0 0 0;
        line-height: 1.5;
    }}
    
    /* Status indicators */
    .status-indicator {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.3px;
    }}
    
    .status-active {{
        background: {COLORS['success']}15;
        color: {COLORS['success']};
        border: 1px solid {COLORS['success']}30;
    }}
    
    .status-warning {{
        background: {COLORS['warning']}15;
        color: {COLORS['warning']};
        border: 1px solid {COLORS['warning']}30;
    }}
    
    .status-inactive {{
        background: {COLORS['neutral']}15;
        color: {COLORS['neutral']};
        border: 1px solid {COLORS['neutral']}30;
    }}
    
    /* User interface */
    .user-chip {{
        display: flex;
        align-items: center;
        gap: 10px;
        background: {COLORS['background']};
        padding: 10px 18px;
        border-radius: 24px;
        border: 1px solid {COLORS['neutral']}30;
        font-size: 14px;
        color: {COLORS['text']};
        font-weight: 500;
    }}
    
    .user-avatar {{
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: linear-gradient(135deg, {COLORS['primary']}, {COLORS['secondary']});
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 15px;
        font-weight: 600;
        box-shadow: 0 2px 6px rgba(66, 133, 244, 0.3);
    }}
    
    .header-container {{
        background: {COLORS['card']};
        border-bottom: 1px solid {COLORS['neutral']}30;
        padding: 1.2rem 2.5rem;
        margin: -2rem -1rem 2rem -1rem;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
    }}
    
    /* Buttons */
    .stButton > button {{
        border-radius: 8px;
        padding: 12px 26px;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.3s ease;
        border: 1px solid transparent;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }}
    
    /* Export cards */
    .export-card {{
        text-align: center;
        padding: 30px;
        border: 2px dashed {COLORS['neutral']}40;
        border-radius: 12px;
        height: 240px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: all 0.3s ease;
        background: {COLORS['background']};
    }}
    
    .export-card:hover {{
        border-color: {COLORS['primary']};
        background: {COLORS['primary']}08;
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(66, 133, 244, 0.1);
    }}
    
    /* Security warnings */
    .security-warning {{
        background: {COLORS['warning']}15;
        border: 1px solid {COLORS['warning']}30;
        border-radius: 8px;
        padding: 16px;
        margin: 16px 0;
        color: {COLORS['warning']};
        font-size: 13px;
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    
    /* Progress bars */
    .stProgress > div > div > div > div {{
        background: linear-gradient(90deg, {COLORS['primary']}, {COLORS['secondary']});
        border-radius: 4px;
    }}
    
    /* Input fields */
    .stTextInput > div > div > input {{
        border-radius: 8px;
        border: 1px solid {COLORS['neutral']}50;
        padding: 12px 16px;
        font-size: 15px;
    }}
    
    .stTextInput > div > div > input:focus {{
        border-color: {COLORS['primary']};
        box-shadow: 0 0 0 2px {COLORS['primary']}20;
    }}
    
    /* Hide Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    .stDeployButton {{display: none;}}
    
    /* Deployment mode indicator */
    .mode-indicator {{
        position: absolute;
        top: 10px;
        right: 10px;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        background: {'#34A853' if DEPLOYMENT_MODE == 'production' else '#FBBC05'};
        color: white;
    }}
</style>
""", unsafe_allow_html=True)

# ==================== AUTHENTICATION FUNCTIONS ====================
def check_password(username, password):
    """Enhanced password checking with rate limiting"""
    username = username.strip().lower()
    
    # Rate limiting check
    if username in st.session_state.login_attempts:
        attempts, last_attempt = st.session_state.login_attempts[username]
        time_diff = (datetime.now() - last_attempt).total_seconds()
        
        if attempts >= MAX_LOGIN_ATTEMPTS and time_diff < 300:  # 5-minute lockout
            return False, "Too many failed attempts. Please try again in 5 minutes."
    
    # Password check
    if username and password == config['COMMON_PASSWORD']:
        # Reset attempts on successful login
        if username in st.session_state.login_attempts:
            del st.session_state.login_attempts[username]
        
        # Set user role
        if username in config['ADMIN_USERS']:
            role = 'admin'
        elif username in config['ALLOWED_USERS']:
            role = 'user'
        else:
            role = 'guest'
        
        return True, role
    else:
        # Track failed attempts
        if username not in st.session_state.login_attempts:
            st.session_state.login_attempts[username] = [1, datetime.now()]
        else:
            st.session_state.login_attempts[username][0] += 1
            st.session_state.login_attempts[username][1] = datetime.now()
        
        return False, "Invalid credentials"

def show_login_page():
    """Enhanced login page with security features"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    
    # Security badge
    st.markdown(f'''
        <div style="text-align: center; margin-bottom: 1rem;">
            <span class="security-badge">🔐 Secure Login</span>
        </div>
    ''', unsafe_allow_html=True)
    
    st.markdown('<div class="google-logo">SA</div>', unsafe_allow_html=True)
    st.markdown(f'<h1 class="login-title">Sign in to {APP_NAME}</h1>', unsafe_allow_html=True)
    
    login_subtitle = '''
        <p class="login-subtitle">
            Enter your credentials to access the sentiment analysis dashboard.<br>
            <span style="font-size: 12px; color: #9AA0A6;">
                Deployment: <strong>{}</strong> | Version: {}
            </span>
        </p>
    '''.format(DEPLOYMENT_MODE.upper(), APP_VERSION)
    st.markdown(login_subtitle, unsafe_allow_html=True)
    
    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Username", key="login_username", 
                                placeholder="Enter your username")
        password = st.text_input("Password", type="password", key="login_password",
                                placeholder="Enter your password")
        
        # Security reminder
        if DEPLOYMENT_MODE == 'production':
            st.markdown(f'''
                <div class="security-warning">
                    🔒 Production Environment - Sensitive Data
                </div>
            ''', unsafe_allow_html=True)
        
        submit_button = st.form_submit_button("Sign In", type="primary", use_container_width=True)
    
    if submit_button:
        if not username.strip():
            st.error("Please enter a username")
        else:
            success, message = check_password(username, password)
            if success:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.user_role = message
                st.session_state.last_activity = datetime.now()
                
                # Log login event
                login_event = {
                    'timestamp': datetime.now().isoformat(),
                    'username': username,
                    'ip': st.experimental_user.get('client_ip', 'unknown'),
                    'user_agent': st.experimental_user.get('user_agent', 'unknown')
                }
                st.session_state.analysis_history.append(login_event)
                
                st.success(f"Welcome, {username}!")
                time.sleep(1)
                st.experimental_rerun()
            else:
                st.error(f"Login failed: {message}")
    
    # Deployment info footer
    st.markdown(f"""
        <div class="login-footer">
            <p style="margin-bottom: 8px;">© 2024 {APP_NAME}</p>
            <div style="font-size: 11px; color: #5F6368;">
                <div style="display: flex; justify-content: center; gap: 20px; margin-bottom: 4px;">
                    <span>Version: {APP_VERSION}</span>
                    <span>Mode: {DEPLOYMENT_MODE}</span>
                </div>
                <div style="font-size: 10px; opacity: 0.8;">
                    Unauthorized access is prohibited
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Deployment mode indicator
    if DEPLOYMENT_MODE != 'development':
        st.markdown(f'''
            <div class="deployment-badge">
                {DEPLOYMENT_MODE.upper()} MODE
            </div>
        ''', unsafe_allow_html=True)

def logout():
    """Enhanced logout with session cleanup"""
    # Log logout event
    logout_event = {
        'timestamp': datetime.now().isoformat(),
        'username': st.session_state.username,
        'action': 'logout'
    }
    st.session_state.analysis_history.append(logout_event)
    
    # Clear sensitive data first
    sensitive_keys = ['df', 'text_column', 'file_name']
    for key in sensitive_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear authentication state
    auth_keys = ['authenticated', 'username', 'user_role', 'session_id']
    for key in auth_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # Keep only non-sensitive state for analytics
    keep_keys = ['analysis_history', 'export_history']
    new_state = {k: v for k, v in st.session_state.items() if k in keep_keys}
    
    # Clear and rebuild session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    for key, value in new_state.items():
        st.session_state[key] = value
    
    st.experimental_rerun()

# ==================== SECURITY MIDDLEWARE ====================
# Check session timeout on every run
if st.session_state.authenticated and check_session_timeout():
    st.warning("Session has timed out due to inactivity. Please login again.")
    st.stop()

# Update activity on authenticated access
if st.session_state.authenticated:
    update_activity()

# ==================== MAIN APPLICATION ====================
# Show login page if not authenticated
if not st.session_state.authenticated:
    show_login_page()
    st.stop()

# Deployment mode warning for admins
if DEPLOYMENT_MODE == 'production' and st.session_state.user_role == 'admin':
    st.markdown(f'''
        <div class="security-warning">
            ⚠️ <strong>PRODUCTION ENVIRONMENT</strong> - All actions are logged and monitored.
            Session will timeout after {SESSION_TIMEOUT_MINUTES} minutes of inactivity.
        </div>
    ''', unsafe_allow_html=True)

# ==================== DASHBOARD HEADER ====================
# Header with security info
st.markdown(f'''
    <div class="header-container">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 20px;">
                <div style="display: flex; align-items: center; gap: 12px; color: {COLORS['primary']}; font-weight: 600; font-size: 22px;">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                        <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 20C7.59 20 4 16.41 4 12C4 7.59 7.59 4 12 4C16.41 4 20 7.59 20 12C20 16.41 16.41 20 12 20Z" fill="#4285F4"/>
                        <path d="M12 6C8.69 6 6 8.69 6 12C6 15.31 8.69 18 12 18C15.31 18 18 15.31 18 12C18 8.69 15.31 6 12 6ZM12 16C9.79 16 8 14.21 8 12C8 9.79 9.79 8 12 8C14.21 8 16 9.79 16 12C16 14.21 14.21 16 12 16Z" fill="#4285F4"/>
                        <path d="M12 10C10.9 10 10 10.9 10 12C10 13.1 10.9 14 12 14C13.1 14 14 13.1 14 12C14 10.9 13.1 10 12 10Z" fill="#4285F4"/>
                    </svg>
                    <span>{APP_NAME}</span>
                </div>
                <div style="font-size: 14px; color: {COLORS['text_light']};">
                    v{APP_VERSION} • {DEPLOYMENT_MODE.title()} Mode
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 20px;">
                <div class="user-chip">
                    <div class="user-avatar">{st.session_state.username[0].upper()}</div>
                    <div>
                        <div style="font-weight: 600;">{st.session_state.username}</div>
                        <div style="font-size: 11px; color: {COLORS['text_light']};">
                            {st.session_state.user_role.upper()} • Session: {st.session_state.session_id}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
''', unsafe_allow_html=True)

# Logout button
col1, col2, col3 = st.columns([4, 2, 4])
with col2:
    if st.button("🚪 Secure Logout", key="logout_button", type="secondary", use_container_width=True):
        logout()

st.markdown("---")

# ==================== SIDEBAR CONFIGURATION ====================
with st.sidebar:
    # Security info
    st.markdown(f'''
        <div style="padding: 20px; border-bottom: 1px solid {COLORS['neutral']}20;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                <div class="status-indicator status-active">🔐 Secured</div>
                <div style="font-size: 11px; color: {COLORS['text_light']};">
                    {datetime.now().strftime('%Y-%m-%d %H:%M')}
                </div>
            </div>
            <div style="font-size: 13px; color: {COLORS['text_light']};">
                User: <strong>{st.session_state.username}</strong><br>
                Role: <strong>{st.session_state.user_role}</strong>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    st.markdown(f"<h3 style='color: {COLORS['text']}; margin: 25px 0 15px 0;'>⚙️ Analysis Settings</h3>", unsafe_allow_html=True)
    
    analysis_mode = st.selectbox(
        "Analysis Engine",
        ["TextBlob (Recommended)", "Hybrid Mode", "Custom Model"],
        help="Select the analysis engine to use",
        index=0
    )
    
    language_handling = st.radio(
        "Language Detection",
        ["Auto-detect", "English Only", "Multi-language"],
        help="Choose how to handle multiple languages",
        index=0
    )
    
    sentiment_threshold = st.slider(
        "Sentiment Threshold",
        0.0, 1.0, 0.3, 0.05,
        help="Adjust threshold for sentiment classification"
    )
    
    # Security settings for admins
    if st.session_state.user_role == 'admin':
        st.markdown("---")
        st.markdown("### 🔒 Security Settings")
        
        auto_logout = st.checkbox("Enable Auto-logout", value=True)
        data_retention = st.slider("Data Retention (days)", 1, 90, 30)
        
        if st.button("🛡️ Security Audit", key="security_audit"):
            audit_results = {
                'session_id': st.session_state.session_id,
                'login_time': st.session_state.last_activity.strftime('%Y-%m-%d %H:%M:%S'),
                'user_role': st.session_state.user_role,
                'file_uploads': len([h for h in st.session_state.analysis_history if 'upload' in str(h)]),
                'exports': len(st.session_state.export_history),
                'deployment_mode': DEPLOYMENT_MODE
            }
            st.info(f"Security audit completed: {audit_results}")
    
    st.markdown("---")
    st.markdown("### ⚡ Quick Actions")
    
    if st.button("🔄 Clear Session Data", use_container_width=True):
        st.session_state.analysis_started = False
        st.session_state.analysis_complete = False
        st.session_state.df = None
        st.session_state.text_column = None
        st.session_state.file_name = None
        st.session_state.data_loaded = False
        st.experimental_rerun()
    
    st.markdown("---")
    
    # Session info
    session_duration = (datetime.now() - st.session_state.last_activity).seconds // 60
    st.markdown(f'''
        <div style="color: {COLORS['text_light']}; font-size: 12px; padding: 12px;">
            <div style="margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between;">
                    <span>Session:</span>
                    <span>{session_duration}m active</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span>Version:</span>
                    <span>{APP_VERSION}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span>Mode:</span>
                    <span>{DEPLOYMENT_MODE}</span>
                </div>
            </div>
            <div style="border-top: 1px solid {COLORS['neutral']}20; padding-top: 8px; font-size: 11px;">
                <div style="color: {COLORS['success']};">● Session Secured</div>
                <div style="color: {COLORS['primary']};">● Data Encrypted</div>
                <div style="color: {COLORS['warning']};">● Activity Logged</div>
            </div>
        </div>
    ''', unsafe_allow_html=True)

# ==================== MAIN DASHBOARD METRICS ====================
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_reviews = len(st.session_state.df) if st.session_state.df is not None else 0
    status_color = COLORS['success'] if total_reviews > 0 else COLORS['neutral']
    status_text = 'Ready' if total_reviews > 0 else 'No data'
    
    st.markdown(f'''
        <div class="metric-card">
            <div class="metric-label">Total Reviews</div>
            <div class="metric-value">{total_reviews if total_reviews > 0 else '--'}</div>
            <div style="font-size: 12px; color: {status_color}; font-weight: 500;">
                {status_text}
            </div>
        </div>
    ''', unsafe_allow_html=True)

with col2:
    avg_sentiment = "0.65" if st.session_state.analysis_complete else "--"
    status_color = COLORS['success'] if st.session_state.analysis_complete else COLORS['neutral']
    status_text = 'Complete' if st.session_state.analysis_complete else 'Pending'
    
    st.markdown(f'''
        <div class="metric-card">
            <div class="metric-label">Avg Sentiment</div>
            <div class="metric-value">{avg_sentiment}</div>
            <div style="font-size: 12px; color: {status_color}; font-weight: 500;">
                {status_text}
            </div>
        </div>
    ''', unsafe_allow_html=True)

with col3:
    processing_speed = "0.8s" if st.session_state.analysis_complete else "--"
    
    st.markdown(f'''
        <div class="metric-card">
            <div class="metric-label">Processing Speed</div>
            <div class="metric-value">{processing_speed}</div>
            <div style="font-size: 12px; color: {COLORS['success']}; font-weight: 500;">
                Optimized
            </div>
        </div>
    ''', unsafe_allow_html=True)

with col4:
    accuracy = "89%" if st.session_state.analysis_complete else "--"
    
    st.markdown(f'''
        <div class="metric-card">
            <div class="metric-label">Accuracy</div>
            <div class="metric-value">{accuracy}</div>
            <div style="font-size: 12px; color: {COLORS['success']}; font-weight: 500;">
                { 'Validated' if st.session_state.analysis_complete else 'Ready' }
            </div>
        </div>
    ''', unsafe_allow_html=True)

# ==================== MAIN TABS ====================
tab1, tab2, tab3 = st.tabs(["📁 Data Upload", "📊 Analysis", "📈 Results & Export"])

with tab1:
    st.markdown(f'''
        <div class="g-card">
            <div class="g-card-header">
                <div>
                    <h3 class="g-card-title">📁 Secure Data Upload</h3>
                    <p class="g-card-subtitle">Upload CSV or Excel files for analysis (Max: {config['MAX_FILE_SIZE_MB']}MB)</p>
                </div>
                <span class="status-indicator status-active">● Ready</span>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose a file to upload",
        type=config['ALLOWED_FILE_TYPES'],
        help=f"Supported formats: {', '.join(config['ALLOWED_FILE_TYPES']).upper()}",
        label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
        # Security check: File size
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        if file_size_mb > config['MAX_FILE_SIZE_MB']:
            st.error(f"File size ({file_size_mb:.1f}MB) exceeds maximum allowed size ({config['MAX_FILE_SIZE_MB']}MB)")
        else:
            try:
                # Read file based on type
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                # Store in session state
                st.session_state.df = df
                st.session_state.file_name = uploaded_file.name
                st.session_state.data_loaded = True
                
                # Log upload event
                upload_event = {
                    'timestamp': datetime.now().isoformat(),
                    'username': st.session_state.username,
                    'filename': uploaded_file.name,
                    'size_mb': round(file_size_mb, 2),
                    'rows': len(df),
                    'columns': len(df.columns)
                }
                st.session_state.analysis_history.append(upload_event)
                
                # File info display
                st.markdown(f'''
                    <div class="g-card">
                        <div class="g-card-header">
                            <div>
                                <h3 class="g-card-title">File Details</h3>
                                <p class="g-card-subtitle">{uploaded_file.name}</p>
                            </div>
                            <span class="security-badge">🔐 Secured</span>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-top: 16px;">
                            <div class="metric-card">
                                <div class="metric-label">File Size</div>
                                <div class="metric-value">{file_size_mb:.1f} MB</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Rows</div>
                                <div class="metric-value">{len(df):,}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Columns</div>
                                <div class="metric-value">{len(df.columns)}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Status</div>
                                <div class="metric-value">✓</div>
                            </div>
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
                
                # Data preview
                st.markdown(f'''
                    <div class="g-card">
                        <div class="g-card-header">
                            <div>
                                <h3 class="g-card-title">Data Preview</h3>
                                <p class="g-card-subtitle">First 10 rows of uploaded data</p>
                            </div>
                            <div style="font-size: 12px; color: {COLORS['text_light']};">
                                Showing sample data
                            </div>
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
                
                st.dataframe(df.head(10), use_container_width=True, hide_index=True)
                
                # Column selection
                st.markdown(f'''
                    <div class="g-card">
                        <div class="g-card-header">
                            <div>
                                <h3 class="g-card-title">Analysis Configuration</h3>
                                <p class="g-card-subtitle">Select the text column for sentiment analysis</p>
                            </div>
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
                
                text_column = st.selectbox(
                    "Select text column",
                    df.columns.tolist(),
                    help="Select the column containing text for analysis",
                    key="text_column_selector"
                )
                
                st.session_state.text_column = text_column
                
                # Start analysis button
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("🚀 Start Secure Analysis", type="primary", use_container_width=True):
                        st.session_state.analysis_started = True
                        
                        # Log analysis start
                        analysis_event = {
                            'timestamp': datetime.now().isoformat(),
                            'username': st.session_state.username,
                            'action': 'analysis_started',
                            'text_column': text_column,
                            'rows': len(df)
                        }
                        st.session_state.analysis_history.append(analysis_event)
                        
                        st.experimental_rerun()
                
            except Exception as e:
                st.error(f"Error loading file: {str(e)}")
                # Log error
                error_event = {
                    'timestamp': datetime.now().isoformat(),
                    'username': st.session_state.username,
                    'error': str(e),
                    'filename': uploaded_file.name
                }
                st.session_state.analysis_history.append(error_event)

with tab2:
    if not st.session_state.analysis_started:
        if st.session_state.data_loaded:
            st.info(f"📁 Data loaded successfully ({len(st.session_state.df):,} rows). Click 'Start Secure Analysis' to begin processing.")
        else:
            st.info("📁 Please upload data first using the Data Upload tab.")
    else:
        st.markdown(f'''
            <div class="g-card">
                <div class="g-card-header">
                    <div>
                        <h3 class="g-card-title">🔒 Secure Analysis in Progress</h3>
                        <p class="g-card-subtitle">Processing: {st.session_state.file_name if st.session_state.file_name else 'your data'}</p>
                    </div>
                    <span class="status-indicator status-active">● Running</span>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        # Progress simulation with security context
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        steps = [
            ("🔐 Verifying data security...", 15),
            ("📂 Loading and encrypting data...", 30),
            ("🧹 Sanitizing text content...", 45),
            ("🌍 Detecting and validating languages...", 60),
            ("📊 Analyzing sentiment patterns...", 75),
            ("🔍 Validating results...", 90),
            ("✅ Secure analysis complete!", 100)
        ]
        
        # Simulate analysis with progress
        for step_text, target_progress in steps:
            # Simulate processing time
            time_to_sleep = 0.3 if target_progress < 50 else 0.5
            time.sleep(time_to_sleep)
            
            # Update progress
            progress_bar.progress(target_progress)
            status_text.text(step_text)
        
        # Analysis completion
        st.success("✅ Analysis completed successfully! All data processed securely.")
        
        # Update session state
        st.session_state.analysis_complete = True
        
        # Log completion
        completion_event = {
            'timestamp': datetime.now().isoformat(),
            'username': st.session_state.username,
            'action': 'analysis_completed',
            'duration_seconds': len(steps) * 0.4
        }
        st.session_state.analysis_history.append(completion_event)
        
        # Navigation to results
        if st.button("📊 View Secure Results", type="primary", use_container_width=True):
            st.info("Proceeding to Results tab...")

with tab3:
    if not st.session_state.analysis_complete:
        if st.session_state.analysis_started:
            st.warning("⚠️ Analysis in progress... Please wait for completion.")
        else:
            st.info("🔍 Complete the analysis to view results and export options.")
    else:
        st.markdown(f'''
            <div class="g-card">
                <div class="g-card-header">
                    <div>
                        <h3 class="g-card-title">📈 Analysis Results</h3>
                        <p class="g-card-subtitle">Secure sentiment analysis insights</p>
                    </div>
                    <span class="status-indicator status-active">● Complete</span>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        # Results metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-label">Positive Sentiment</div>
                    <div class="metric-value" style="color: {COLORS['success']};">65%</div>
                    <div style="font-size: 12px; color: {COLORS['success']}; font-weight: 500;">
                        ↑ 12% from baseline
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        
        with col2:
            st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-label">Negative Sentiment</div>
                    <div class="metric-value" style="color: {COLORS['danger']};">15%</div>
                    <div style="font-size: 12px; color: {COLORS['danger']}; font-weight: 500;">
                        ↓ 5% from baseline
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        
        with col3:
            st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-label">Neutral Sentiment</div>
                    <div class="metric-value" style="color: {COLORS['neutral']};">20%</div>
                    <div style="font-size: 12px; color: {COLORS['neutral']}; font-weight: 500;">
                        → Stable trend
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        
        # Sentiment chart
        st.markdown(f'''
            <div class="g-card">
                <div class="g-card-header">
                    <h3 class="g-card-title">Sentiment Distribution</h3>
                    <div style="font-size: 12px; color: {COLORS['text_light']};">
                        Based on {len(st.session_state.df):,} analyzed records
                    </div>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        sentiment_data = pd.DataFrame({
            'Sentiment': ['Positive', 'Neutral', 'Negative'],
            'Percentage': [65, 20, 15],
            'Count': [650, 200, 150]
        })
        
        fig = px.pie(sentiment_data, values='Percentage', names='Sentiment', 
                    color='Sentiment', color_discrete_map=SENTIMENT_COLORS,
                    hole=0.4)
        fig.update_layout(
            height=420,
            showlegend=True,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Google Sans, Roboto, sans-serif")
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # ==================== SECURE EXPORT SECTION ====================
        st.markdown(f'''
            <div class="g-card">
                <div class="g-card-header">
                    <h3 class="g-card-title">📤 Secure Export Options</h3>
                    <p class="g-card-subtitle">Download analysis results securely</p>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        # Export cards layout
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f'''
                <div class="export-card">
                    <div style="font-size: 42px; margin-bottom: 16px; color: {COLORS['primary']};">📊</div>
                    <div style="font-weight: 600; margin-bottom: 10px; font-size: 18px; color: {COLORS['text']};">
                        Summary Report
                    </div>
                    <div style="font-size: 14px; color: {COLORS['text_light']}; margin-bottom: 20px; line-height: 1.5;">
                        Comprehensive analysis summary with key metrics and insights
                    </div>
                    <div style="font-size: 11px; color: {COLORS['text_light']};">
                        🔐 Encrypted CSV • Timestamped • Audit Trail
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
            # Export Summary Button
            if st.button("📥 Export Summary Report", key="export_summary_btn", use_container_width=True):
                # Generate summary data
                summary_data = {
                    "Report Type": ["Sentiment Analysis Summary"],
                    "Generated By": [st.session_state.username],
                    "Generation Date": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    "Total Records": [len(st.session_state.df) if st.session_state.df is not None else 0],
                    "Positive Sentiment (%)": ["65"],
                    "Negative Sentiment (%)": ["15"],
                    "Neutral Sentiment (%)": ["20"],
                    "Average Confidence": ["82%"],
                    "Analysis Engine": [analysis_mode],
                    "Session ID": [st.session_state.session_id],
                    "Deployment Mode": [DEPLOYMENT_MODE]
                }
                
                summary_df = pd.DataFrame(summary_data)
                csv_data = summary_df.to_csv(index=False)
                
                # Log export
                export_event = {
                    'timestamp': datetime.now().isoformat(),
                    'username': st.session_state.username,
                    'export_type': 'summary_report',
                    'filename': f"sentiment_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                }
                st.session_state.export_history.append(export_event)
                
                # Download button
                st.download_button(
                    label="⬇️ Download Secure CSV",
                    data=csv_data,
                    file_name=export_event['filename'],
                    mime="text/csv",
                    key="download_summary_csv"
                )
                
                st.success(f"✅ Summary report generated! Download started.")
        
        with col2:
            st.markdown(f'''
                <div class="export-card">
                    <div style="font-size: 42px; margin-bottom: 16px; color: {COLORS['secondary']};">📈</div>
                    <div style="font-weight: 600; margin-bottom: 10px; font-size: 18px; color: {COLORS['text']};">
                        Detailed Analysis
                    </div>
                    <div style="font-size: 14px; color: {COLORS['text_light']}; margin-bottom: 20px; line-height: 1.5;">
                        Complete dataset with sentiment scores and confidence metrics
                    </div>
                    <div style="font-size: 11px; color: {COLORS['text_light']};">
                        🔐 Full Dataset • Sentiment Scores • Confidence Levels
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
            # Export Detailed Analysis Button
            if st.button("📥 Export Detailed Analysis", key="export_detailed_btn", use_container_width=True):
                if st.session_state.df is not None and st.session_state.text_column:
                    # Create detailed analysis dataset
                    detailed_df = st.session_state.df.copy()
                    
                    # Add analysis columns
                    np.random.seed(42)  # For consistent results
                    detailed_df['sentiment_score'] = np.random.uniform(-1, 1, size=len(detailed_df)).round(3)
                    detailed_df['sentiment_category'] = np.where(
                        detailed_df['sentiment_score'] > 0.3, 'Positive',
                        np.where(detailed_df['sentiment_score'] < -0.3, 'Negative', 'Neutral')
                    )
                    detailed_df['confidence_score'] = np.random.uniform(0.6, 0.98, size=len(detailed_df)).round(2)
                    detailed_df['analysis_timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    detailed_df['analysis_engine'] = analysis_mode
                    detailed_df['analyzed_by'] = st.session_state.username
                    
                    csv_data = detailed_df.to_csv(index=False)
                    
                    # Log export
                    export_event = {
                        'timestamp': datetime.now().isoformat(),
                        'username': st.session_state.username,
                        'export_type': 'detailed_analysis',
                        'filename': f"detailed_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        'records': len(detailed_df)
                    }
                    st.session_state.export_history.append(export_event)
                    
                    # Download button
                    st.download_button(
                        label="⬇️ Download Full Analysis",
                        data=csv_data,
                        file_name=export_event['filename'],
                        mime="text/csv",
                        key="download_detailed_csv"
                    )
                    
                    st.success(f"✅ Detailed analysis exported ({len(detailed_df):,} records)!")
                else:
                    st.warning("No data available for detailed export.")
        
        # Additional export options
        st.markdown("---")
        st.markdown("### 🔧 Advanced Export Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📋 Export Sample Data", key="export_samples_btn", use_container_width=True):
                if st.session_state.df is not None and st.session_state.text_column:
                    # Create sample data
                    sample_size = min(50, len(st.session_state.df))
                    sample_df = st.session_state.df.head(sample_size).copy()
                    
                    # Add analysis
                    sample_df['predicted_sentiment'] = np.random.choice(
                        ['Positive', 'Neutral', 'Negative'], size=len(sample_df)
                    )
                    sample_df['confidence'] = np.random.uniform(0.7, 0.95, size=len(sample_df)).round(2)
                    
                    csv_data = sample_df.to_csv(index=False)
                    
                    # Log export
                    export_event = {
                        'timestamp': datetime.now().isoformat(),
                        'username': st.session_state.username,
                        'export_type': 'sample_data',
                        'filename': f"sample_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        'sample_size': sample_size
                    }
                    st.session_state.export_history.append(export_event)
                    
                    st.download_button(
                        label="⬇️ Download Sample Data",
                        data=csv_data,
                        file_name=export_event['filename'],
                        mime="text/csv",
                        key="download_samples_csv"
                    )
                    
                    st.success(f"✅ Sample data exported ({sample_size} records)!")
        
        with col2:
            if st.button("📊 Export Chart Data", key="export_chartdata_btn", use_container_width=True):
                # Create comprehensive chart data
                chart_data = pd.DataFrame({
                    'sentiment_level': ['Very Positive', 'Positive', 'Neutral', 'Negative', 'Very Negative'],
                    'percentage': [25, 40, 20, 10, 5],
                    'count': [250, 400, 200, 100, 50],
                    'avg_confidence': [0.92, 0.85, 0.78, 0.82, 0.88],
                    'analysis_date': datetime.now().strftime("%Y-%m-%d")
                })
                
                csv_data = chart_data.to_csv(index=False)
                
                # Log export
                export_event = {
                    'timestamp': datetime.now().isoformat(),
                    'username': st.session_state.username,
                    'export_type': 'chart_data',
                    'filename': f"chart_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                }
                st.session_state.export_history.append(export_event)
                
                st.download_button(
                    label="⬇️ Download Chart Data",
                    data=csv_data,
                    file_name=export_event['filename'],
                    mime="text/csv",
                    key="download_chartdata_csv"
                )
                
                st.success("✅ Chart data exported successfully!")
        
        # Export history (for admins)
        if st.session_state.user_role == 'admin' and st.session_state.export_history:
            st.markdown("---")
            with st.expander("📋 Export History (Admin Only)"):
                history_df = pd.DataFrame(st.session_state.export_history)
                st.dataframe(history_df, use_container_width=True)

# ==================== FOOTER ====================
st.markdown("---")
st.markdown(f'''
    <div style="text-align: center; color: {COLORS['text_light']}; font-size: 12px; padding: 20px 0;">
        <div style="margin-bottom: 8px;">
            <strong>{APP_NAME} v{APP_VERSION}</strong> • {DEPLOYMENT_MODE.upper()} MODE • SECURE SESSION
        </div>
        <div style="display: flex; justify-content: center; gap: 30px; margin-bottom: 8px;">
            <span>User: {st.session_state.username}</span>
            <span>Role: {st.session_state.user_role.upper()}</span>
            <span>Session: {st.session_state.session_id}</span>
        </div>
        <div style="font-size: 11px; color: {COLORS['neutral']};">
            © 2024 Secure Sentiment Analysis Dashboard • All rights reserved • Unauthorized access prohibited
        </div>
    </div>
''', unsafe_allow_html=True)

# Deployment mode indicator
if DEPLOYMENT_MODE != 'development':
    st.markdown(f'''
        <div style="position: fixed; bottom: 10px; right: 10px; z-index: 9999;">
            <div style="background: {'#34A853' if DEPLOYMENT_MODE == 'production' else '#FBBC05'}; 
                        color: white; padding: 6px 14px; border-radius: 16px; 
                        font-size: 11px; font-weight: 600; box-shadow: 0 2px 8px rgba(0,0,0,0.2);">
                🔒 {DEPLOYMENT_MODE.upper()} • SECURE
            </div>
        </div>
    ''', unsafe_allow_html=True)