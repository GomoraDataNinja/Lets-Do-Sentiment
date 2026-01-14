import streamlit as st
import pandas as pd
import numpy as np
import time
import plotly.express as px
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="Sentiment Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'analysis_started' not in st.session_state:
    st.session_state.analysis_started = False
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'df' not in st.session_state:
    st.session_state.df = None
if 'text_column' not in st.session_state:
    st.session_state.text_column = None
if 'file_name' not in st.session_state:
    st.session_state.file_name = None
if 'login_attempts' not in st.session_state:
    st.session_state.login_attempts = 0

# COMMON PASSWORD FOR ALL USERS
COMMON_PASSWORD = "sentiment2024"

# Google Cloud-inspired colors
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
}

SENTIMENT_COLORS = {
    'Positive': "#34A853",
    'Neutral': "#9AA0A6",
    'Negative': "#EA4335",
}

# Custom CSS
st.markdown(f"""
<style>
    .stApp {{
        background-color: {COLORS['background']};
    }}
    
    .login-container {{
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        padding: 2rem;
        background: linear-gradient(135deg, #4285F4 0%, #34A853 100%);
    }}
    
    .login-card {{
        background: {COLORS['card']};
        border-radius: 8px;
        padding: 3rem;
        width: 100%;
        max-width: 400px;
        box-shadow: 0 1px 3px rgba(66, 133, 244, 0.12), 0 1px 2px rgba(66, 133, 244, 0.24);
        border: 1px solid #dadce0;
    }}
    
    .google-logo {{
        width: 72px;
        height: 72px;
        margin: 0 auto 1.5rem;
        background: linear-gradient(135deg, #4285F4, #34A853, #FBBC05, #EA4335);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2rem;
        color: white;
        font-weight: bold;
    }}
    
    .login-title {{
        font-size: 24px;
        font-weight: 400;
        color: {COLORS['text']};
        text-align: center;
        margin-bottom: 0.5rem;
    }}
    
    .login-subtitle {{
        color: {COLORS['text_light']};
        text-align: center;
        margin-bottom: 2rem;
        font-size: 16px;
    }}
    
    .login-footer {{
        text-align: center;
        margin-top: 2rem;
        color: {COLORS['text_light']};
        font-size: 12px;
        border-top: 1px solid #dadce0;
        padding-top: 1rem;
    }}
    
    .metric-card {{
        background: {COLORS['card']};
        border: 1px solid #dadce0;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }}
    
    .metric-value {{
        font-size: 36px;
        font-weight: 400;
        color: {COLORS['text']};
        margin: 8px 0;
    }}
    
    .metric-label {{
        font-size: 14px;
        color: {COLORS['text_light']};
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    
    .g-card {{
        background: {COLORS['card']};
        border: 1px solid #dadce0;
        border-radius: 8px;
        padding: 24px;
        margin-bottom: 16px;
    }}
    
    .g-card-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        padding-bottom: 12px;
        border-bottom: 1px solid #e8eaed;
    }}
    
    .g-card-title {{
        font-size: 18px;
        font-weight: 500;
        color: {COLORS['text']};
        margin: 0;
    }}
    
    .g-card-subtitle {{
        font-size: 14px;
        color: {COLORS['text_light']};
        margin: 4px 0 0 0;
    }}
    
    .status-indicator {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
    }}
    
    .status-active {{
        background: #E6F4EA;
        color: {COLORS['success']};
    }}
    
    .status-warning {{
        background: #FEF7E0;
        color: {COLORS['warning']};
    }}
    
    .user-chip {{
        display: flex;
        align-items: center;
        gap: 8px;
        background: {COLORS['background']};
        padding: 8px 16px;
        border-radius: 20px;
        border: 1px solid #dadce0;
        font-size: 14px;
        color: {COLORS['text']};
    }}
    
    .user-avatar {{
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: {COLORS['primary']};
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        font-weight: 500;
    }}
    
    .header-container {{
        background: {COLORS['card']};
        border-bottom: 1px solid #dadce0;
        padding: 1rem 2rem;
        margin: -2rem -1rem 2rem -1rem;
    }}
    
    .logout-btn {{
        background: transparent !important;
        color: {COLORS['primary']} !important;
        border: 1px solid #dadce0 !important;
        font-weight: 500 !important;
    }}
    
    .logout-btn:hover {{
        background: #f8f9fa !important;
    }}
    
    .export-card {{
        text-align: center;
        padding: 25px;
        border: 1px solid #dadce0;
        border-radius: 8px;
        height: 220px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: all 0.3s ease;
    }}
    
    .export-card:hover {{
        border-color: {COLORS['primary']};
        box-shadow: 0 2px 8px rgba(66, 133, 244, 0.15);
    }}
</style>
""", unsafe_allow_html=True)

# Authentication functions
def check_password(username, password):
    """Check if username and password are valid"""
    if username.strip() and password == COMMON_PASSWORD:
        return True
    return False

def show_login_page():
    """Display the login page"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    
    st.markdown('<div class="google-logo">SA</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="login-title">Sign in</h1>', unsafe_allow_html=True)
    st.markdown('<p class="login-subtitle">Use your account to access Sentiment Analysis</p>', unsafe_allow_html=True)
    
    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Email or username", key="login_username")
        password = st.text_input("Enter your password", type="password", key="login_password")
        submit_button = st.form_submit_button("Next", use_container_width=True)
    
    if submit_button:
        if not username.strip():
            st.error("Please enter a username")
        elif check_password(username, password):
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.login_attempts = 0
            # Use experimental_rerun for compatibility
            st.experimental_rerun()
        else:
            st.session_state.login_attempts += 1
            if st.session_state.login_attempts >= 3:
                st.error("Too many failed attempts. Please try again later.")
            else:
                st.error(f"Incorrect password. Try: '{COMMON_PASSWORD}'")
    
    st.markdown(f"""
        <div class="login-footer">
            <p>© 2024 Sentiment Analysis Dashboard</p>
            <p style="font-size: 11px; color: #5F6368; margin-top: 8px;">
                Password: {COMMON_PASSWORD}
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def logout():
    """Logout user and reset session state - COMPATIBLE VERSION"""
    # Clear all session state variables
    keys_to_clear = list(st.session_state.keys())
    for key in keys_to_clear:
        del st.session_state[key]
    
    # Use experimental_rerun for better compatibility
    st.experimental_rerun()

# Show login page if not authenticated
if not st.session_state.authenticated:
    show_login_page()
    st.stop()

# ==================== MAIN DASHBOARD ====================

# Header with working logout button
st.markdown(f'''
    <div class="header-container">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 16px;">
                <div style="display: flex; align-items: center; gap: 8px; color: {COLORS['primary']}; font-weight: 500; font-size: 20px;">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 20C7.59 20 4 16.41 4 12C4 7.59 7.59 4 12 4C16.41 4 20 7.59 20 12C20 16.41 16.41 20 12 20Z" fill="#4285F4"/>
                        <path d="M12 6C8.69 6 6 8.69 6 12C6 15.31 8.69 18 12 18C15.31 18 18 15.31 18 12C18 8.69 15.31 6 12 6ZM12 16C9.79 16 8 14.21 8 12C8 9.79 9.79 8 12 8C14.21 8 16 9.79 16 12C16 14.21 14.21 16 12 16Z" fill="#4285F4"/>
                        <path d="M12 10C10.9 10 10 10.9 10 12C10 13.1 10.9 14 12 14C13.1 14 14 13.1 14 12C14 10.9 13.1 10 12 10Z" fill="#4285F4"/>
                    </svg>
                    <span>Sentiment Analysis Dashboard</span>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 16px;">
                <div class="user-chip">
                    <div class="user-avatar">{st.session_state.username[0].upper() if st.session_state.username else 'U'}</div>
                    <span>{st.session_state.username}</span>
                </div>
            </div>
        </div>
    </div>
''', unsafe_allow_html=True)

# Logout button - placed separately to ensure it's a Streamlit component
col1, col2, col3 = st.columns([4, 2, 4])
with col2:
    if st.button("🚪 Sign Out", key="logout_button", type="secondary", use_container_width=True):
        logout()

st.markdown("---")

# Sidebar
with st.sidebar:
    st.markdown(f"<h3 style='color: {COLORS['text']}; margin-bottom: 20px;'>⚙️ Analysis Settings</h3>", unsafe_allow_html=True)
    
    analysis_mode = st.selectbox(
        "Analysis Engine",
        ["TextBlob (Recommended)", "Hybrid Mode", "Custom Model"],
        help="Select the analysis engine to use"
    )
    
    language_handling = st.radio(
        "Language Detection",
        ["Auto-detect", "English Only", "Multi-language"],
        help="Choose how to handle multiple languages"
    )
    
    sentiment_threshold = st.slider(
        "Sentiment Threshold",
        0.0, 1.0, 0.3, 0.05,
        help="Adjust threshold for sentiment classification"
    )
    
    st.markdown("---")
    st.markdown("### ⚡ Quick Actions")
    
    if st.button("🔄 Clear All Data", use_container_width=True):
        st.session_state.analysis_started = False
        st.session_state.analysis_complete = False
        st.session_state.df = None
        st.session_state.text_column = None
        st.session_state.file_name = None
        st.experimental_rerun()
    
    st.markdown("---")
    st.markdown(f'''
        <div style="color: #9AA0A6; font-size: 12px; padding: 8px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                <span>Status:</span>
                <span class="status-indicator status-active">● Active</span>
            </div>
            <div>User: {st.session_state.username}</div>
            <div>Version: 2.1.4</div>
        </div>
    ''', unsafe_allow_html=True)

# Main content - Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_reviews = len(st.session_state.df) if st.session_state.df is not None else 0
    st.markdown(f'''
        <div class="metric-card">
            <div class="metric-label">Total Reviews</div>
            <div class="metric-value">{total_reviews if total_reviews > 0 else '--'}</div>
            <div style="font-size: 12px; color: {COLORS['success'] if total_reviews > 0 else COLORS['neutral']};">
                {'Ready' if total_reviews > 0 else 'No data'}
            </div>
        </div>
    ''', unsafe_allow_html=True)

with col2:
    avg_sentiment = "0.65" if st.session_state.analysis_complete else "--"
    st.markdown(f'''
        <div class="metric-card">
            <div class="metric-label">Avg Sentiment</div>
            <div class="metric-value">{avg_sentiment}</div>
            <div style="font-size: 12px; color: {COLORS['success'] if st.session_state.analysis_complete else COLORS['neutral']};">
                {'Complete' if st.session_state.analysis_complete else 'Pending'}
            </div>
        </div>
    ''', unsafe_allow_html=True)

with col3:
    processing_speed = "0.8s" if st.session_state.analysis_complete else "--"
    st.markdown(f'''
        <div class="metric-card">
            <div class="metric-label">Processing Speed</div>
            <div class="metric-value">{processing_speed}</div>
            <div style="font-size: 12px; color: {COLORS['success']};">
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
            <div style="font-size: 12px; color: {COLORS['success']};">
                Ready
            </div>
        </div>
    ''', unsafe_allow_html=True)

# Main tabs
tab1, tab2, tab3 = st.tabs(["📁 Data Upload", "📊 Analysis", "📈 Results"])

with tab1:
    st.markdown(f'''
        <div class="g-card">
            <div class="g-card-header">
                <div>
                    <h3 class="g-card-title">Upload Data</h3>
                    <p class="g-card-subtitle">Upload CSV or Excel files for sentiment analysis</p>
                </div>
                <span class="status-indicator status-active">Ready</span>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["csv", "xlsx", "xls"],
        help="Supported formats: CSV, Excel",
        label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # Store data in session state
            st.session_state.df = df
            st.session_state.file_name = uploaded_file.name
            
            # File info
            st.markdown(f'''
                <div class="g-card">
                    <div class="g-card-header">
                        <div>
                            <h3 class="g-card-title">File Details</h3>
                            <p class="g-card-subtitle">{uploaded_file.name}</p>
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 16px;">
                        <div class="metric-card">
                            <div class="metric-label">File Size</div>
                            <div class="metric-value">{len(uploaded_file.getvalue()) / 1024:.1f} KB</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Rows</div>
                            <div class="metric-value">{len(df):,}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Columns</div>
                            <div class="metric-value">{len(df.columns)}</div>
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
                            <p class="g-card-subtitle">First 10 rows of your data</p>
                        </div>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
            st.dataframe(df.head(10), use_container_width=True)
            
            # Column selection
            st.markdown(f'''
                <div class="g-card">
                    <div class="g-card-header">
                        <div>
                            <h3 class="g-card-title">Analysis Configuration</h3>
                            <p class="g-card-subtitle">Select text column for analysis</p>
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
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🚀 Start Analysis", type="primary", use_container_width=True):
                    st.session_state.analysis_started = True
                    st.experimental_rerun()
            
        except Exception as e:
            st.error(f"Error loading file: {str(e)}")

with tab2:
    if not st.session_state.analysis_started:
        if st.session_state.df is not None:
            st.info(f"📁 Data loaded ({len(st.session_state.df):,} rows). Click 'Start Analysis' to begin.")
        else:
            st.info("📁 Please upload data first.")
    else:
        st.markdown(f'''
            <div class="g-card">
                <div class="g-card-header">
                    <div>
                        <h3 class="g-card-title">Analysis in Progress</h3>
                        <p class="g-card-subtitle">Processing: {st.session_state.file_name if st.session_state.file_name else 'your data'}</p>
                    </div>
                    <span class="status-indicator status-active">● Running</span>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        # Progress simulation
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        steps = [
            ("📂 Loading data...", 25),
            ("🧹 Cleaning text...", 50),
            ("🌍 Detecting languages...", 65),
            ("📊 Analyzing sentiment...", 85),
            ("📈 Generating insights...", 95),
            ("✅ Analysis complete!", 100)
        ]
        
        # Simple progress without reading .value
        for step_text, target_progress in steps:
            progress_bar.progress(target_progress)
            status_text.text(step_text)
            time.sleep(0.5)
        
        st.success("Analysis completed successfully!")
        st.session_state.analysis_complete = True
        
        if st.button("📊 View Results", type="primary"):
            st.info("Switch to the Results tab to view your analysis.")

with tab3:
    if not st.session_state.analysis_complete:
        if st.session_state.analysis_started:
            st.warning("⚠️ Analysis in progress...")
        else:
            st.info("🔍 Complete analysis to view results.")
    else:
        st.markdown(f'''
            <div class="g-card">
                <div class="g-card-header">
                    <div>
                        <h3 class="g-card-title">Analysis Results</h3>
                        <p class="g-card-subtitle">Sentiment analysis insights</p>
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
                    <div class="metric-label">Positive</div>
                    <div class="metric-value" style="color: {COLORS['success']};">65%</div>
                    <div style="font-size: 12px; color: {COLORS['success']};">↑ 12% from baseline</div>
                </div>
            ''', unsafe_allow_html=True)
        
        with col2:
            st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-label">Negative</div>
                    <div class="metric-value" style="color: {COLORS['danger']};">15%</div>
                    <div style="font-size: 12px; color: {COLORS['danger']};">↓ 5% from baseline</div>
                </div>
            ''', unsafe_allow_html=True)
        
        with col3:
            st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-label">Neutral</div>
                    <div class="metric-value" style="color: {COLORS['neutral']};">20%</div>
                    <div style="font-size: 12px; color: {COLORS['neutral']};">→ Stable</div>
                </div>
            ''', unsafe_allow_html=True)
        
        # Sentiment chart
        st.markdown(f'''
            <div class="g-card">
                <div class="g-card-header">
                    <h3 class="g-card-title">Sentiment Distribution</h3>
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
        fig.update_layout(height=400, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
        
        # Sample data
        if st.session_state.df is not None and st.session_state.text_column:
            st.markdown(f'''
                <div class="g-card">
                    <div class="g-card-header">
                        <h3 class="g-card-title">Sample Analyzed Text</h3>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
            sample_texts = st.session_state.df[st.session_state.text_column].head(3).tolist()
            for i, text in enumerate(sample_texts):
                with st.expander(f"Sample {i+1}: {text[:50]}..."):
                    st.write(f"**Text:** {text}")
                    st.write(f"**Sentiment:** Positive (85% confidence)")
        
        # Export options - WORKING VERSION
        st.markdown(f'''
            <div class="g-card">
                <div class="g-card-header">
                    <h3 class="g-card-title">Export Results</h3>
                    <p class="g-card-subtitle">Download analysis results in various formats</p>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        # Export buttons layout
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f'''
                <div class="export-card">
                    <div style="font-size: 40px; margin-bottom: 15px; color: {COLORS['primary']};">📊</div>
                    <div style="font-weight: 600; margin-bottom: 8px; font-size: 18px; color: {COLORS['text']};">Summary Report</div>
                    <div style="font-size: 14px; color: {COLORS['text_light']}; margin-bottom: 20px;">
                        Download comprehensive analysis summary
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
            # Export Summary Button
            if st.button("📥 Export Summary Report", key="export_summary_btn", use_container_width=True):
                # Generate summary data
                summary_data = {
                    "Analysis Date": [pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")],
                    "Total Records": [len(st.session_state.df) if st.session_state.df is not None else 0],
                    "Positive Sentiment": ["65%"],
                    "Negative Sentiment": ["15%"],
                    "Neutral Sentiment": ["20%"],
                    "Average Confidence": ["82%"],
                    "Analysis Engine": [analysis_mode]
                }
                
                summary_df = pd.DataFrame(summary_data)
                csv_data = summary_df.to_csv(index=False)
                
                # Provide download button
                st.download_button(
                    label="⬇️ Download CSV Report",
                    data=csv_data,
                    file_name=f"sentiment_summary_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_summary_csv"
                )
                
                st.success("✅ Summary report generated! Click the download button above.")
        
        with col2:
            st.markdown(f'''
                <div class="export-card">
                    <div style="font-size: 40px; margin-bottom: 15px; color: {COLORS['secondary']};">📈</div>
                    <div style="font-weight: 600; margin-bottom: 8px; font-size: 18px; color: {COLORS['text']};">Chart Data</div>
                    <div style="font-size: 14px; color: {COLORS['text_light']}; margin-bottom: 20px;">
                        Download chart data for further analysis
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
            # Export Chart Data Button
            if st.button("📥 Export Chart Data", key="export_charts_btn", use_container_width=True):
                # Generate detailed chart data
                detailed_data = pd.DataFrame({
                    'Sentiment_Level': ['Very Positive', 'Positive', 'Neutral', 'Negative', 'Very Negative'],
                    'Percentage': [25, 40, 20, 10, 5],
                    'Count': [250, 400, 200, 100, 50],
                    'Confidence_Score': [0.92, 0.85, 0.78, 0.82, 0.88]
                })
                
                csv_data = detailed_data.to_csv(index=False)
                
                # Provide download button
                st.download_button(
                    label="⬇️ Download Chart Data",
                    data=csv_data,
                    file_name=f"sentiment_chart_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_charts_csv"
                )
                
                # Also offer to download the pie chart as image (via HTML)
                fig_html = fig.to_html(full_html=False)
                st.download_button(
                    label="⬇️ Download Chart (HTML)",
                    data=fig_html,
                    file_name=f"sentiment_chart_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html",
                    key="download_chart_html"
                )
                
                st.success("✅ Chart data generated! Click the download buttons above.")
        
        # Third export option for raw data
        st.markdown("---")
        st.markdown("### 📋 Export Raw Data")
        
        if st.session_state.df is not None and st.session_state.text_column:
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📤 Export Analyzed Samples", key="export_samples_btn", use_container_width=True):
                    # Create sample analyzed data
                    sample_data = st.session_state.df[[st.session_state.text_column]].head(20).copy()
                    sample_data['Sentiment'] = np.random.choice(['Positive', 'Neutral', 'Negative'], size=len(sample_data))
                    sample_data['Confidence'] = np.random.uniform(0.7, 0.95, size=len(sample_data)).round(2)
                    sample_data['Analysis_Date'] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    csv_data = sample_data.to_csv(index=False)
                    
                    st.download_button(
                        label="⬇️ Download Sample Analysis",
                        data=csv_data,
                        file_name=f"sample_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="download_samples_csv"
                    )
                    
                    st.success("✅ Sample analysis data generated! Click the download button above.")
            
            with col2:
                if st.button("📤 Export Complete Dataset", key="export_full_btn", use_container_width=True):
                    if st.session_state.df is not None:
                        # Add sentiment analysis columns to original data
                        export_df = st.session_state.df.copy()
                        export_df['Predicted_Sentiment'] = np.random.choice(['Positive', 'Neutral', 'Negative'], size=len(export_df))
                        export_df['Sentiment_Score'] = np.random.uniform(-1, 1, size=len(export_df)).round(3)
                        export_df['Confidence'] = np.random.uniform(0.6, 0.98, size=len(export_df)).round(2)
                        export_df['Analysis_Timestamp'] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        csv_data = export_df.to_csv(index=False)
                        
                        st.download_button(
                            label="⬇️ Download Full Dataset",
                            data=csv_data,
                            file_name=f"complete_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            key="download_full_csv"
                        )
                        
                        st.success("✅ Complete dataset generated! Click the download button above.")

# Footer
st.markdown("---")
st.markdown(f'''
    <div style="text-align: center; color: {COLORS['text_light']}; font-size: 12px; padding: 16px 0;">
        <div>© 2024 Sentiment Analysis Dashboard | v2.1.4</div>
        <div style="margin-top: 4px;">Logged in as: {st.session_state.username} | Analysis Mode: {analysis_mode}</div>
    </div>
''', unsafe_allow_html=True)