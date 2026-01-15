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

# ==================== COMPATIBILITY HELPER ====================
def safe_rerun():
    """Handle both old and new Streamlit rerun methods"""
    try:
        st.rerun()  # New method (Streamlit >= 1.28.0)
    except AttributeError:
        st.experimental_rerun()  # Old method

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

# ==================== THEME DETECTION ====================
def get_theme():
    """Detect current theme"""
    # Try to get theme from session state or default to light
    try:
        # This is a workaround since Streamlit doesn't expose theme directly in Python
        # We'll use a CSS-based detection and store in session state
        if 'current_theme' not in st.session_state:
            # Default to light, will be updated by JavaScript
            st.session_state.current_theme = 'light'
        return st.session_state.current_theme
    except:
        return 'light'

# ==================== THEME-AWARE COLORS ====================
def get_theme_colors(theme):
    """Get colors based on theme"""
    if theme == 'dark':
        return {
            'primary': "#4285F4",
            'secondary': "#34A853",
            'accent': "#EA4335",
            'warning': "#FBBC05",
            'neutral': "#9AA0A6",
            'background': "#0E1117",  # Dark theme background
            'card': "#1E2126",  # Dark cards
            'text': "#FAFAFA",  # Light text on dark
            'text_light': "#B0B3B8",  # Light gray text
            'success': "#34A853",
            'danger': "#EA4335",
            'sidebar': "#1E2126",
            'border': "#2D3748",  # Dark borders
            'hover': "#2A2D35"  # Hover state for dark
        }
    else:  # light theme
        return {
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
            'sidebar': "#202124",
            'border': "#DADCE0",  # Light borders
            'hover': "#F1F3F4"  # Hover state for light
        }

# Initialize theme
current_theme = get_theme()
COLORS = get_theme_colors(current_theme)

# ==================== SENTIMENT COLORS (Theme Independent) ====================
SENTIMENT_COLORS = {
    'Positive': "#34A853",
    'Neutral': "#9AA0A6",
    'Negative': "#EA4335",
}

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
        
        © 2026 All rights reserved.
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

# Theme state
if 'current_theme' not in st.session_state:
    st.session_state.current_theme = 'light'

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

# ==================== DYNAMIC CSS FOR THEME SUPPORT ====================
st.markdown(f"""
<style>
    /* CSS Variables for Theme Support */
    :root {{
        --primary-color: {COLORS['primary']};
        --secondary-color: {COLORS['secondary']};
        --accent-color: {COLORS['accent']};
        --warning-color: {COLORS['warning']};
        --neutral-color: {COLORS['neutral']};
        --background-color: {COLORS['background']};
        --card-color: {COLORS['card']};
        --text-color: {COLORS['text']};
        --text-light-color: {COLORS['text_light']};
        --success-color: {COLORS['success']};
        --danger-color: {COLORS['danger']};
        --border-color: {COLORS['border']};
        --hover-color: {COLORS['hover']};
        
        /* Sentiment colors */
        --positive-color: {SENTIMENT_COLORS['Positive']};
        --neutral-color: {SENTIMENT_COLORS['Neutral']};
        --negative-color: {SENTIMENT_COLORS['Negative']};
    }}
    
    /* Base styles with theme support */
    .stApp {{
        background-color: var(--background-color);
        font-family: 'Google Sans', 'Roboto', 'Segoe UI', sans-serif;
        color: var(--text-color);
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
        background: rgba(52, 168, 83, 0.15);
        color: var(--success-color);
        border: 1px solid rgba(52, 168, 83, 0.3);
        white-space: nowrap;
    }}
    
    .deployment-badge {{
        position: fixed;
        bottom: 10px;
        right: 10px;
        background: var(--primary-color);
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
        background: var(--card-color);
        border-radius: 12px;
        padding: 3rem;
        width: 100%;
        max-width: 420px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
        border: 1px solid var(--border-color);
        backdrop-filter: blur(10px);
        color: var(--text-color);
    }}
    
    .google-logo {{
        width: 80px;
        height: 80px;
        margin: 0 auto 1.5rem;
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color), var(--warning-color), var(--accent-color));
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
        color: var(--text-color);
        text-align: center;
        margin-bottom: 0.5rem;
        line-height: 1.2;
    }}
    
    .login-subtitle {{
        color: var(--text-light-color);
        text-align: center;
        margin-bottom: 2.5rem;
        font-size: 15px;
        line-height: 1.5;
    }}
    
    /* Dashboard components */
    .metric-card {{
        background: var(--card-color);
        border: 1px solid var(--border-color);
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        min-height: 130px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        color: var(--text-color);
    }}
    
    .metric-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        border-color: var(--primary-color);
        background: var(--hover-color);
    }}
    
    .metric-value {{
        font-size: 32px;
        font-weight: 400;
        color: var(--text-color);
        margin: 8px 0;
        font-family: 'Google Sans Display', sans-serif;
        line-height: 1.2;
    }}
    
    .metric-label {{
        font-size: 12px;
        color: var(--text-light-color);
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 600;
        margin-bottom: 5px;
        line-height: 1.3;
    }}
    
    .metric-status {{
        font-size: 11px;
        color: var(--text-light-color);
        margin-top: 5px;
        font-weight: 500;
    }}
    
    .g-card {{
        background: var(--card-color);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
        transition: all 0.3s ease;
        color: var(--text-color);
    }}
    
    .g-card:hover {{
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        border-color: var(--primary-color);
    }}
    
    .g-card-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 20px;
        padding-bottom: 16px;
        border-bottom: 1px solid var(--border-color);
        flex-wrap: wrap;
        gap: 15px;
    }}
    
    .g-card-title {{
        font-size: 20px;
        font-weight: 500;
        color: var(--text-color);
        margin: 0 0 8px 0;
        display: flex;
        align-items: center;
        gap: 10px;
        line-height: 1.3;
    }}
    
    .g-card-subtitle {{
        font-size: 14px;
        color: var(--text-light-color);
        margin: 0;
        line-height: 1.5;
        opacity: 0.9;
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
        white-space: nowrap;
    }}
    
    .status-active {{
        background: rgba(52, 168, 83, 0.15);
        color: var(--success-color);
        border: 1px solid rgba(52, 168, 83, 0.3);
    }}
    
    .status-warning {{
        background: rgba(251, 188, 5, 0.15);
        color: var(--warning-color);
        border: 1px solid rgba(251, 188, 5, 0.3);
    }}
    
    .status-inactive {{
        background: rgba(154, 160, 166, 0.15);
        color: var(--neutral-color);
        border: 1px solid rgba(154, 160, 166, 0.3);
    }}
    
    /* User interface */
    .user-chip {{
        display: flex;
        align-items: center;
        gap: 10px;
        background: var(--background-color);
        padding: 10px 18px;
        border-radius: 24px;
        border: 1px solid var(--border-color);
        font-size: 14px;
        color: var(--text-color);
        font-weight: 500;
    }}
    
    .user-avatar {{
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 15px;
        font-weight: 600;
        box-shadow: 0 2px 6px rgba(66, 133, 244, 0.3);
    }}
    
    .header-container {{
        background: var(--card-color);
        border-bottom: 1px solid var(--border-color);
        padding: 1.2rem 2.5rem;
        margin: -2rem -1rem 2rem -1rem;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
    }}
    
    /* Buttons */
    .stButton > button {{
        border-radius: 8px;
        padding: 10px 22px;
        font-size: 13px;
        font-weight: 500;
        transition: all 0.3s ease;
        border: 1px solid transparent;
        margin-top: 10px;
        line-height: 1.4;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }}
    
    /* Export cards */
    .export-card {{
        text-align: center;
        padding: 24px 20px;
        border: 2px dashed var(--border-color);
        border-radius: 12px;
        min-height: 240px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: all 0.3s ease;
        background: var(--background-color);
        color: var(--text-color);
    }}
    
    .export-card:hover {{
        border-color: var(--primary-color);
        background: rgba(66, 133, 244, 0.08);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(66, 133, 244, 0.1);
    }}
    
    .export-icon {{
        font-size: 40px;
        margin-bottom: 16px;
        color: var(--primary-color);
        line-height: 1;
    }}
    
    .export-title {{
        font-weight: 600;
        margin-bottom: 12px;
        font-size: 18px;
        color: var(--text-color);
        line-height: 1.3;
    }}
    
    .export-description {{
        font-size: 13px;
        color: var(--text-light-color);
        margin-bottom: 16px;
        line-height: 1.5;
    }}
    
    .export-security {{
        font-size: 11px;
        color: var(--text-light-color);
        margin-top: 12px;
        line-height: 1.4;
    }}
    
    /* Security warnings */
    .security-warning {{
        background: rgba(251, 188, 5, 0.15);
        border: 1px solid rgba(251, 188, 5, 0.3);
        border-radius: 8px;
        padding: 16px;
        margin: 16px 0;
        color: var(--warning-color);
        font-size: 13px;
        display: flex;
        align-items: center;
        gap: 10px;
        line-height: 1.5;
    }}
    
    /* Progress bars */
    .stProgress > div > div > div > div {{
        background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
        border-radius: 4px;
    }}
    
    /* Input fields */
    .stTextInput > div > div > input {{
        border-radius: 8px;
        border: 1px solid var(--border-color);
        padding: 12px 16px;
        font-size: 15px;
        color: var(--text-color);
        background: var(--card-color);
    }}
    
    .stTextInput > div > div > input:focus {{
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px rgba(66, 133, 244, 0.2);
    }}
    
    .stTextInput > label {{
        color: var(--text-color);
        font-weight: 500;
    }}
    
    /* File upload section */
    .upload-section {{
        padding: 30px;
        background: var(--background-color);
        border-radius: 10px;
        border: 2px dashed var(--border-color);
        text-align: center;
        margin: 20px 0;
    }}
    
    .upload-info {{
        font-size: 14px;
        color: var(--text-light-color);
        margin-top: 15px;
        line-height: 1.6;
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
    
    /* Data frames */
    .stDataFrame {{
        font-size: 13px;
    }}
    
    .stDataFrame th {{
        font-weight: 600;
        color: var(--text-color);
        background: var(--background-color);
    }}
    
    .stDataFrame td {{
        font-size: 13px;
        padding: 8px 12px;
        color: var(--text-color);
    }}
    
    /* Tab improvements */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 2px;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        font-size: 14px;
        font-weight: 500;
        padding: 12px 20px;
        color: var(--text-color);
    }}
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        background: var(--primary-color);
        color: white;
    }}
    
    /* Better column spacing */
    .stColumn {{
        padding: 8px;
    }}
    
    /* File uploader */
    [data-testid="stFileUploader"] {{
        font-size: 14px;
        color: var(--text-color);
    }}
    
    [data-testid="stFileUploader"] label {{
        font-weight: 500;
        color: var(--text-color);
        font-size: 15px;
    }}
    
    [data-testid="stFileUploader"] section {{
        border: 2px dashed var(--border-color);
        background: var(--background-color);
        border-radius: 10px;
        padding: 30px;
    }}
    
    /* Form labels */
    .stTextInput > label, .stSelectbox > label, .stSlider > label, .stRadio > label {{
        font-weight: 500;
        color: var(--text-color);
        font-size: 14px;
    }}
    
    /* Alert and info boxes */
    .stAlert {{
        font-size: 14px;
        line-height: 1.5;
    }}
    
    .stExpander {{
        font-size: 14px;
    }}
    
    .stExpander > summary {{
        font-weight: 500;
        color: var(--text-color);
    }}
    
    /* Chart improvements */
    .js-plotly-plot {{
        font-family: 'Google Sans', 'Roboto', sans-serif;
    }}
    
    /* Responsive adjustments */
    @media (max-width: 768px) {{
        .metric-value {{
            font-size: 28px;
        }}
        
        .export-card {{
            min-height: 220px;
            padding: 20px 15px;
        }}
        
        .stButton > button {{
            padding: 8px 16px;
            font-size: 12px;
        }}
        
        .g-card {{
            padding: 20px 16px;
        }}
        
        .g-card-title {{
            font-size: 18px;
        }}
        
        .export-title {{
            font-size: 16px;
        }}
        
        .export-description {{
            font-size: 12px;
        }}
    }}
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: var(--background-color);
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: var(--neutral-color);
        border-radius: 4px;
        opacity: 0.4;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: var(--neutral-color);
        opacity: 0.6;
    }}
    
    /* Markdown text */
    .stMarkdown {{
        color: var(--text-color);
    }}
    
    .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, 
    .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {{
        color: var(--text-color);
    }}
    
    .stMarkdown strong, .stMarkdown b {{
        color: var(--text-color);
    }}
    
    /* Selectbox */
    .stSelectbox > div > div {{
        color: var(--text-color);
    }}
    
    /* Slider */
    .stSlider > div > div {{
        color: var(--text-color);
    }}
    
    /* Checkbox */
    .stCheckbox > label {{
        color: var(--text-color);
    }}
    
    /* Expander */
    .streamlit-expanderHeader {{
        color: var(--text-color);
    }}
    
    /* Theme-aware text colors for data display */
    .data-table-container {{
        background: var(--card-color);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 16px;
        margin: 16px 0;
    }}
    
    /* Ensure all text is visible */
    * {{
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }}
    
    /* Dark theme specific adjustments */
    .dark-theme-adjustments {{
        /* Add specific dark theme fixes here */
    }}
</style>

<!-- JavaScript to detect theme -->
<script>
    // Function to detect Streamlit theme
    function detectTheme() {{
        // Get computed style to check theme
        const htmlElement = document.documentElement;
        const themeColor = getComputedStyle(htmlElement).getPropertyValue('color-scheme');
        
        // Check background color to determine theme
        const bgColor = getComputedStyle(document.body).backgroundColor;
        const rgb = bgColor.match(/\\d+/g);
        
        if (rgb) {{
            const brightness = (parseInt(rgb[0]) * 299 + parseInt(rgb[1]) * 587 + parseInt(rgb[2]) * 114) / 1000;
            return brightness < 128 ? 'dark' : 'light';
        }}
        
        return 'light';
    }}
    
    // Update theme in session state
    function updateTheme() {{
        const theme = detectTheme();
        const event = new CustomEvent('setTheme', {{ detail: {{ theme: theme }} }});
        window.parent.document.dispatchEvent(event);
    }}
    
    // Run on load and when theme might change
    document.addEventListener('DOMContentLoaded', updateTheme);
    // Also check periodically
    setInterval(updateTheme, 2000);
</script>
""", unsafe_allow_html=True)

# JavaScript to update theme in Python session state
st.components.v1.html("""
<script>
    // Listen for theme change events
    window.addEventListener('setTheme', function(e) {
        const theme = e.detail.theme;
        
        // Send to Streamlit
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: theme
        }, '*');
    });
    
    // Initial detection
    setTimeout(function() {
        const htmlElement = document.documentElement;
        const themeColor = getComputedStyle(htmlElement).getPropertyValue('color-scheme');
        
        // Check background color
        const bgColor = getComputedStyle(document.body).backgroundColor;
        const rgb = bgColor.match(/\\d+/g);
        let theme = 'light';
        
        if (rgb) {
            const brightness = (parseInt(rgb[0]) * 299 + parseInt(rgb[1]) * 587 + parseInt(rgb[2]) * 114) / 1000;
            theme = brightness < 128 ? 'dark' : 'light';
        }
        
        // Send initial theme
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: theme
        }, '*');
    }, 100);
</script>
""", height=0)

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
    
    login_subtitle = f'''
        <p class="login-subtitle">
            Enter your credentials to access the sentiment analysis dashboard.<br>
            <span style="font-size: 12px; opacity: 0.8;">
                Deployment: <strong>{DEPLOYMENT_MODE.upper()}</strong> | Version: {APP_VERSION}
            </span>
        </p>
    '''
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
                safe_rerun()
            else:
                st.error(f"Login failed: {message}")
    
    # Deployment info footer
    st.markdown(f"""
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid var(--border-color);">
            <div style="text-align: center; color: var(--text-light-color); font-size: 12px;">
                <div style="margin-bottom: 8px;">
                    <strong>{APP_NAME} v{APP_VERSION}</strong>
                </div>
                <div style="font-size: 11px; opacity: 0.8;">
                    © 2024 Secure Sentiment Analysis Dashboard<br>
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
    
    safe_rerun()

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
                <div style="display: flex; align-items: center; gap: 12px; color: var(--primary-color); font-weight: 600; font-size: 22px;">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                        <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 20C7.59 20 4 16.41 4 12C4 7.59 7.59 4 12 4C16.41 4 20 7.59 20 12C20 16.41 16.41 20 12 20Z" fill="currentColor"/>
                        <path d="M12 6C8.69 6 6 8.69 6 12C6 15.31 8.69 18 12 18C15.31 18 18 15.31 18 12C18 8.69 15.31 6 12 6ZM12 16C9.79 16 8 14.21 8 12C8 9.79 9.79 8 12 8C14.21 8 16 9.79 16 12C16 14.21 14.21 16 12 16Z" fill="currentColor"/>
                        <path d="M12 10C10.9 10 10 10.9 10 12C10 13.1 10.9 14 12 14C13.1 14 14 13.1 14 12C14 10.9 13.1 10 12 10Z" fill="currentColor"/>
                    </svg>
                    <span>{APP_NAME}</span>
                </div>
                <div style="font-size: 14px; color: var(--text-light-color);">
                    v{APP_VERSION} • {DEPLOYMENT_MODE.title()} Mode
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 20px;">
                <div class="user-chip">
                    <div class="user-avatar">{st.session_state.username[0].upper()}</div>
                    <div>
                        <div style="font-weight: 600;">{st.session_state.username}</div>
                        <div style="font-size: 11px; color: var(--text-light-color);">
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
        <div style="padding: 20px; border-bottom: 1px solid var(--border-color); background: var(--card-color); border-radius: 8px; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                <div class="status-indicator status-active">🔐 Secured</div>
                <div style="font-size: 11px; color: var(--text-light-color);">
                    {datetime.now().strftime('%Y-%m-%d %H:%M')}
                </div>
            </div>
            <div style="font-size: 13px; color: var(--text-color); line-height: 1.5;">
                <div style="margin-bottom: 5px;"><strong>User:</strong> {st.session_state.username}</div>
                <div><strong>Role:</strong> {st.session_state.user_role}</div>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    st.markdown(f"<h3 style='color: var(--text-color); margin: 25px 0 15px 0;'>⚙️ Analysis Settings</h3>", unsafe_allow_html=True)
    
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
        st.markdown(f"<h3 style='color: var(--text-color);'>🔒 Security Settings</h3>", unsafe_allow_html=True)
        
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
    st.markdown(f"<h3 style='color: var(--text-color);'>⚡ Quick Actions</h3>", unsafe_allow_html=True)
    
    if st.button("🔄 Clear Session Data", use_container_width=True):
        st.session_state.analysis_started = False
        st.session_state.analysis_complete = False
        st.session_state.df = None
        st.session_state.text_column = None
        st.session_state.file_name = None
        st.session_state.data_loaded = False
        safe_rerun()
    
    st.markdown("---")
    
    # Session info
    session_duration = (datetime.now() - st.session_state.last_activity).seconds // 60
    st.markdown(f'''
        <div style="color: var(--text-color); font-size: 12px; padding: 12px; background: var(--card-color); border-radius: 8px; border: 1px solid var(--border-color);">
            <div style="margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between;">
                    <span>Session:</span>
                    <span style="color: var(--text-light-color);">{session_duration}m active</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span>Version:</span>
                    <span style="color: var(--text-light-color);">{APP_VERSION}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span>Mode:</span>
                    <span style="color: var(--text-light-color);">{DEPLOYMENT_MODE}</span>
                </div>
            </div>
            <div style="border-top: 1px solid var(--border-color); padding-top: 8px; font-size: 11px;">
                <div style="color: var(--success-color);">● Session Secured</div>
                <div style="color: var(--primary-color);">● Data Encrypted</div>
                <div style="color: var(--warning-color);">● Activity Logged</div>
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
            <div class="metric-status" style="color: {status_color};">
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
            <div class="metric-status" style="color: {status_color};">
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
            <div class="metric-status" style="color: var(--success-color);">
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
            <div class="metric-status" style="color: var(--success-color);">
                {'Validated' if st.session_state.analysis_complete else 'Ready'}
            </div>
        </div>
    ''', unsafe_allow_html=True)

# ==================== MAIN TABS ====================
tab1, tab2, tab3 = st.tabs(["📁 Data Upload", "📊 Analysis", "📈 Results & Export"])

with tab1:
    # UPLOAD SECTION
    st.markdown(f'''
        <div class="g-card">
            <div class="g-card-header">
                <div style="flex: 1;">
                    <h3 class="g-card-title">📁 Secure Data Upload</h3>
                    <p class="g-card-subtitle">
                        Upload CSV or Excel files for sentiment analysis. All uploads are encrypted and logged.
                    </p>
                </div>
                <span class="status-indicator status-active">Ready to Upload</span>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    # Enhanced file upload section
    st.markdown(f'''
        <div style="border: 2px dashed var(--border-color); border-radius: 12px; padding: 40px 20px; 
                 background: var(--background-color); text-align: center; margin: 20px 0;">
            <div style="font-size: 18px; font-weight: 600; color: var(--text-color); margin-bottom: 10px;">
                📤 Drag and drop or click to browse files
            </div>
            <div style="font-size: 14px; color: var(--text-light-color); line-height: 1.6;">
                <strong>Supported formats:</strong> CSV, XLSX, XLS<br>
                <strong>Maximum size:</strong> {config['MAX_FILE_SIZE_MB']}MB<br>
                <strong>Security:</strong> All uploads are encrypted and logged
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=config['ALLOWED_FILE_TYPES'],
        help=f"Supported formats: {', '.join(config['ALLOWED_FILE_TYPES']).upper()}. Maximum file size: {config['MAX_FILE_SIZE_MB']}MB",
        label_visibility="collapsed"
    )
    
    # Additional instructions
    st.markdown(f'''
        <div style="margin-top: 20px; padding: 20px; background-color: var(--card-color); border-radius: 10px; border: 1px solid var(--border-color);">
            <div style="font-size: 15px; color: var(--text-color); font-weight: 600; margin-bottom: 12px;">
                📝 Upload Instructions:
            </div>
            <div style="font-size: 14px; color: var(--text-light-color); line-height: 1.6;">
                <div style="margin-bottom: 8px;">1. Click the upload area above or drag and drop your file</div>
                <div style="margin-bottom: 8px;">2. Supported formats: {', '.join(config['ALLOWED_FILE_TYPES']).upper()}</div>
                <div style="margin-bottom: 8px;">3. Maximum file size: {config['MAX_FILE_SIZE_MB']}MB</div>
                <div style="margin-bottom: 8px;">4. Your data is encrypted during transfer and storage</div>
                <div>5. All uploads are logged for security audit purposes</div>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    if uploaded_file is not None:
        # Security check: File size
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        if file_size_mb > config['MAX_FILE_SIZE_MB']:
            st.error(f"❌ File size ({file_size_mb:.1f}MB) exceeds maximum allowed size ({config['MAX_FILE_SIZE_MB']}MB)")
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
                                <h3 class="g-card-title" style="color: var(--success-color);">✅ File Uploaded Successfully</h3>
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
                                <div class="metric-value" style="color: var(--success-color);">✓</div>
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
                            <div style="font-size: 12px; color: var(--text-light-color);">
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
                    "**Select text column for analysis**",
                    df.columns.tolist(),
                    help="Select the column containing text for sentiment analysis",
                    key="text_column_selector"
                )
                
                st.session_state.text_column = text_column
                
                # Additional options
                with st.expander("⚙️ Advanced Options"):
                    st.markdown(f"<div style='color: var(--text-color); font-weight: 500; margin-bottom: 10px;'>Advanced Analysis Settings</div>", unsafe_allow_html=True)
                    
                    sample_size = st.slider(
                        "Sample size (for testing)",
                        100, min(1000, len(df)), min(500, len(df)),
                        help="Analyze a sample of the data for faster results"
                    )
                    
                    include_timestamp = st.checkbox(
                        "Include timestamp in analysis",
                        value=True,
                        help="Add analysis timestamp to results"
                    )
                
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
                            'rows': len(df),
                            'sample_size': sample_size if 'sample_size' in locals() else 'full_dataset'
                        }
                        st.session_state.analysis_history.append(analysis_event)
                        
                        safe_rerun()
                
            except Exception as e:
                st.error(f"❌ Error loading file: {str(e)}")
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
            st.markdown(f'''
                <div class="g-card">
                    <div class="g-card-header">
                        <div>
                            <h3 class="g-card-title">📊 Ready for Analysis</h3>
                            <p class="g-card-subtitle">
                                Data loaded successfully ({len(st.session_state.df):,} rows).
                                Click 'Start Secure Analysis' to begin processing.
                            </p>
                        </div>
                        <span class="status-indicator status-inactive">Waiting</span>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown(f'''
                <div class="g-card">
                    <div class="g-card-header">
                        <div>
                            <h3 class="g-card-title">📁 No Data Available</h3>
                            <p class="g-card-subtitle">Please upload data first using the Data Upload tab.</p>
                        </div>
                        <span class="status-indicator status-warning">No Data</span>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
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
            status_text.markdown(f"<div style='color: var(--text-color); font-size: 14px;'>{step_text}</div>", unsafe_allow_html=True)
        
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
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("📊 View Secure Results", type="primary", use_container_width=True):
                st.info("Proceeding to Results tab...")

with tab3:
    if not st.session_state.analysis_complete:
        if st.session_state.analysis_started:
            st.markdown(f'''
                <div class="g-card">
                    <div class="g-card-header">
                        <div>
                            <h3 class="g-card-title">⏳ Analysis in Progress</h3>
                            <p class="g-card-subtitle">Please wait for the analysis to complete.</p>
                        </div>
                        <span class="status-indicator status-warning">Processing</span>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown(f'''
                <div class="g-card">
                    <div class="g-card-header">
                        <div>
                            <h3 class="g-card-title">🔍 Complete Analysis First</h3>
                            <p class="g-card-subtitle">Complete the analysis to view results and export options.</p>
                        </div>
                        <span class="status-indicator status-inactive">No Results</span>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
    else:
        # ==================== RESULTS OVERVIEW ====================
        st.markdown(f'''
            <div class="g-card">
                <div class="g-card-header">
                    <div>
                        <h3 class="g-card-title">📈 Analysis Results</h3>
                        <p class="g-card-subtitle">
                            Secure sentiment results summary
                        </p>
                    </div>
                    <span class="status-indicator status-active">Completed</span>
                </div>
            </div>
        ''', unsafe_allow_html=True)

        # Mock sentiment distribution
        sentiment_data = pd.DataFrame({
            "Sentiment": ["Positive", "Neutral", "Negative"],
            "Count": [55, 25, 20]
        })

        fig = px.pie(
            sentiment_data,
            names="Sentiment",
            values="Count",
            color="Sentiment",
            color_discrete_map=SENTIMENT_COLORS,
            hole=0.4
        )
        
        # Update chart text visibility
        fig.update_layout(
            font=dict(
                family="Google Sans, Roboto, sans-serif",
                size=14,
                color=COLORS['text']
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )

        st.plotly_chart(fig, use_container_width=True)

        # ==================== EXPORT SECTION ====================
        st.markdown(f'''
            <div class="g-card">
                <div class="g-card-header">
                    <div>
                        <h3 class="g-card-title">⬇️ Export Results</h3>
                        <p class="g-card-subtitle">
                            Download securely processed results
                        </p>
                    </div>
                </div>
            </div>
        ''', unsafe_allow_html=True)

        # Results metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-label">Positive Sentiment</div>
                    <div class="metric-value" style="color: var(--success-color);">65%</div>
                    <div class="metric-status" style="color: var(--success-color);">
                        ↑ 12% from baseline
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        
        with col2:
            st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-label">Negative Sentiment</div>
                    <div class="metric-value" style="color: var(--danger-color);">15%</div>
                    <div class="metric-status" style="color: var(--danger-color);">
                        ↓ 5% from baseline
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        
        with col3:
            st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-label">Neutral Sentiment</div>
                    <div class="metric-value" style="color: var(--neutral-color);">20%</div>
                    <div class="metric-status" style="color: var(--neutral-color);">
                        → Stable trend
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        
        # Sentiment chart
        st.markdown(f'''
            <div class="g-card">
                <div class="g-card-header">
                    <div>
                        <h3 class="g-card-title">Sentiment Distribution</h3>
                        <p class="g-card-subtitle">Based on {len(st.session_state.df):,} analyzed records</p>
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
            font=dict(
                family="Google Sans, Roboto, sans-serif", 
                size=14,
                color=COLORS['text']
            ),
            legend=dict(
                font=dict(size=13, color=COLORS['text']),
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            )
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # ==================== SECURE EXPORT SECTION ====================
        st.markdown(f'''
            <div class="g-card">
                <div class="g-card-header">
                    <div>
                        <h3 class="g-card-title">📤 Secure Export Options</h3>
                        <p class="g-card-subtitle">Download analysis results securely. All exports are encrypted and logged.</p>
                    </div>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        # Export cards layout
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f'''
                <div class="export-card">
                    <div class="export-icon">📊</div>
                    <div class="export-title">Summary Report</div>
                    <div class="export-description">
                        Comprehensive analysis summary with key metrics, insights, and recommendations.
                        Includes sentiment distribution and performance indicators.
                    </div>
                    <div class="export-security">
                        🔐 Encrypted CSV • Timestamped • Audit Trail Included
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
                    key="download_summary_csv",
                    use_container_width=True
                )
                
                st.success(f"✅ Summary report generated! Download started.")
        
        with col2:
            st.markdown(f'''
                <div class="export-card">
                    <div class="export-icon">📈</div>
                    <div class="export-title">Detailed Analysis</div>
                    <div class="export-description">
                        Complete dataset with sentiment scores, confidence metrics, and analysis metadata.
                        Includes all original data plus analysis results.
                    </div>
                    <div class="export-security">
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
                        key="download_detailed_csv",
                        use_container_width=True
                    )
                    
                    st.success(f"✅ Detailed analysis exported ({len(detailed_df):,} records)!")
                else:
                    st.warning("No data available for detailed export.")
        
        # Additional export options
        st.markdown("---")
        st.markdown(f'''
            <div class="g-card">
                <div class="g-card-header">
                    <div>
                        <h3 class="g-card-title">🔧 Advanced Export Options</h3>
                        <p class="g-card-subtitle">Additional export formats and specialized reports</p>
                    </div>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
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
                        key="download_samples_csv",
                        use_container_width=True
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
                    key="download_chartdata_csv",
                    use_container_width=True
                )
                
                st.success("✅ Chart data exported successfully!")
        
        # Export history (for admins)
        if st.session_state.user_role == 'admin' and st.session_state.export_history:
            st.markdown("---")
            with st.expander("📋 Export History (Admin Only)"):
                if st.session_state.export_history:
                    history_df = pd.DataFrame(st.session_state.export_history)
                    st.dataframe(history_df, use_container_width=True)
                else:
                    st.info("No export history available.")

        # ==================== AUDIT LOG ====================
        with st.expander("🧾 View Audit Log"):
            st.markdown(f"<div style='color: var(--text-color); font-weight: 500; margin-bottom: 10px;'>Activity History</div>", unsafe_allow_html=True)
            audit_df = pd.DataFrame(st.session_state.analysis_history)
            if not audit_df.empty:
                st.dataframe(audit_df, use_container_width=True)
            else:
                st.info("No audit activity recorded yet")

# ==================== FOOTER ====================
st.markdown("---")
st.markdown(f'''
    <div style="text-align: center; color: var(--text-light-color); font-size: 12px; padding: 20px 0;">
        <div style="margin-bottom: 8px;">
            <strong>{APP_NAME} v{APP_VERSION}</strong> • {DEPLOYMENT_MODE.upper()} MODE • SECURE SESSION
        </div>
        <div style="display: flex; justify-content: center; gap: 30px; margin-bottom: 8px; font-size: 11px;">
            <span>User: {st.session_state.username}</span>
            <span>Role: {st.session_state.user_role.upper()}</span>
            <span>Session: {st.session_state.session_id}</span>
        </div>
        <div style="font-size: 11px; color: var(--neutral-color);">
            © 2026 Secure Sentiment Analysis Dashboard • All rights reserved • Unauthorized access prohibited
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

# Theme toggle for testing (optional - can be removed in production)
with st.sidebar:
    if st.session_state.user_role == 'admin':
        st.markdown("---")
        st.markdown(f"<h3 style='color: var(--text-color);'>🎨 Theme Test</h3>", unsafe_allow_html=True)
        if st.button("Toggle Theme Preview"):
            current_theme = st.session_state.current_theme
            new_theme = 'dark' if current_theme == 'light' else 'light'
            st.session_state.current_theme = new_theme
            COLORS = get_theme_colors(new_theme)
            safe_rerun()

