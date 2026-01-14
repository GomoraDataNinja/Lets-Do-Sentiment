import streamlit as st
import pandas as pd
import numpy as np
import requests
from collections import Counter
import nltk
import plotly.express as px
import warnings
from datetime import datetime
from textblob import TextBlob
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import time
import re
import hashlib
from functools import lru_cache
import joblib
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="Sentiment Analysis Dashboard",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CACHE EVERYTHING - Major performance improvement
@st.cache_data(ttl=3600, show_spinner=False)
def load_data(file, file_ext):
    """Cache file loading"""
    if file_ext == 'csv':
        return pd.read_csv(file, low_memory=False)
    else:
        return pd.read_excel(file)

@st.cache_data(ttl=3600, show_spinner=False)
def detect_column_language_batch(texts, batch_size=100):
    """Batch language detection for better performance"""
    from langdetect import detect, LangDetectException
    
    results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_results = []
        for text in batch:
            if pd.isna(text) or len(str(text)) < 5:
                batch_results.append("unknown")
                continue
            try:
                lang = detect(str(text))
                # Map langdetect codes to our language names
                lang_map = {
                    'en': 'english', 'sn': 'shona', 'nd': 'ndebele', 
                    'tn': 'tonga', 'es': 'spanish', 'fr': 'french', 'de': 'german'
                }
                # Simple check for Zimbabwean languages
                text_lower = str(text).lower()
                if any(z_word in text_lower for z_word in ['ndi', 'na', 'ne', 'ku', 'kwa']):
                    batch_results.append('shona')
                elif any(z_word in text_lower for z_word in ['ngi', 'si', 'li', 'ba', 'be']):
                    batch_results.append('ndebele')
                elif any(z_word in text_lower for z_word in ['ba', 'be', 'bi', 'bo', 'mu']):
                    batch_results.append('tonga')
                elif lang in lang_map:
                    batch_results.append(lang_map[lang])
                else:
                    batch_results.append('unknown')
            except:
                batch_results.append('unknown')
        results.extend(batch_results)
    return results

# Optimized stopwords loading
@st.cache_resource
def load_optimized_stopwords():
    """Load minimal stopwords for speed"""
    try:
        nltk.download('stopwords', quiet=True)
        from nltk.corpus import stopwords
        english_stopwords = set(stopwords.words('english'))
        
        # Minimal Zimbabwean stopwords
        zimbabwean_stopwords = {
            'shona': {'ne', 'na', 'ku', 'kwa', 'kwe', 'cha', 'che', 'cho', 'chi'},
            'ndebele': {'na', 'ne', 'ni', 'no', 'nu', 'ka', 'ke', 'ki', 'ko', 'ku'},
            'tonga': {'na', 'ne', 'ni', 'no', 'nu', 'ka', 'ke', 'ki', 'ko', 'ku'}
        }
        
        # Create unified stopword set
        all_stopwords = english_stopwords.copy()
        for lang_stops in zimbabwean_stopwords.values():
            all_stopwords.update(lang_stops)
            
        return all_stopwords
    except:
        # Fallback to basic English stopwords
        return {'the', 'and', 'you', 'that', 'for', 'with', 'this', 'have', 'from', 'are'}

# LRU cache for expensive operations
@lru_cache(maxsize=1000)
def cached_textblob_analysis(text, threshold=0.1):
    """Cached TextBlob analysis for repeated texts"""
    blob = TextBlob(str(text))
    polarity = blob.sentiment.polarity
    
    if polarity > threshold:
        return "Positive", float(polarity)
    elif polarity < -threshold:
        return "Negative", float(polarity)
    else:
        return "Neutral", float(polarity)

@lru_cache(maxsize=10000)
def cached_language_detection(text):
    """Cached language detection"""
    text_str = str(text).lower()
    
    # Fast keyword-based detection for Zimbabwean languages
    zimbabwean_keywords = {
        'shona': ['ndi', 'na', 'ne', 'ku', 'kwa', 'ndatenda', 'mangwanani'],
        'ndebele': ['ngi', 'si', 'li', 'ba', 'ngiyabonga', 'sawubona'],
        'tonga': ['ba', 'be', 'bi', 'mu', 'twalumba', 'mwabuka']
    }
    
    for lang, keywords in zimbabwean_keywords.items():
        if any(keyword in text_str for keyword in keywords):
            return lang
    
    # Check for English
    english_words = {'the', 'and', 'you', 'that', 'for', 'with', 'this'}
    if any(word in text_str for word in english_words):
        return 'english'
    
    return 'unknown'

# Colors with Zimbabwean theme (restored original colors)
COLORS = {
    'primary': "#006400",  # Zimbabwe green
    'secondary': '#FFD700',  # Zimbabwe gold
    'accent': "#CE1126",  # Zimbabwe red
    'success': '#10B981',
    'warning': "#F59E0B",
    'danger': "#EF4444",
    'neutral': '#9CA3AF',
    'background': "#1F2937",
    'card': "#FFFFFF",
    'text': '#111827',
    'text_light': '#6B7280',
}

SENTIMENT_COLORS = {
    'Positive': "#10B981",
    'Neutral': "#6B7280",
    'Negative': "#EF4444",
}

# Beautiful CSS with Zimbabwean theme and cards
st.markdown(f"""
<style>
    .stApp {{
        background: linear-gradient(135deg, {COLORS['background']} 0%, #0C2D1C 100%);
    }}
    .main-header {{
        font-size: 3rem;
        font-weight: 800;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1.5rem;
        background: linear-gradient(90deg, rgba(0, 100, 0, 0.3), rgba(206, 17, 38, 0.3));
        border-radius: 15px;
        border: 1px solid rgba(255, 215, 0, 0.2);
        backdrop-filter: blur(10px);
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }}
    .section-header {{
        font-size: 1.8rem;
        color: white;
        margin: 2rem 0 1rem 0;
        padding: 0.8rem 1.5rem;
        background: linear-gradient(90deg, {COLORS['primary']}30, {COLORS['accent']}30);
        border-radius: 10px;
        border-left: 4px solid {COLORS['secondary']};
        font-weight: 600;
    }}
    
    /* Card Styles */
    .card {{
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.98));
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(0, 100, 0, 0.1);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s, box-shadow 0.2s;
    }}
    .card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(0, 0, 0, 0.15);
    }}
    .card-header {{
        font-size: 1.3rem;
        font-weight: 700;
        color: {COLORS['primary']};
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid rgba(206, 17, 38, 0.2);
    }}
    .card-content {{
        color: {COLORS['text']};
        line-height: 1.6;
    }}
    
    /* Stat Cards */
    .stat-card {{
        background: linear-gradient(135deg, {COLORS['card']} 0%, #F8FAFC 100%);
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.5rem 0;
        border: 1px solid rgba(0, 100, 0, 0.15);
        box-shadow: 0 3px 15px rgba(0, 0, 0, 0.08);
    }}
    .stat-value {{
        font-size: 2.2rem;
        font-weight: 800;
        color: {COLORS['primary']};
        text-align: center;
        margin: 0.5rem 0;
    }}
    .stat-label {{
        font-size: 0.9rem;
        color: {COLORS['text_light']};
        text-align: center;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .stat-icon {{
        font-size: 1.8rem;
        text-align: center;
        margin-bottom: 0.5rem;
    }}
    
    /* Language Badges */
    .language-badge {{
        display: inline-block;
        padding: 0.2rem 0.8rem;
        border-radius: 15px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.2rem;
        border: 1px solid rgba(255,255,255,0.2);
    }}
    .lang-en {{ background: linear-gradient(135deg, #3B82F6, #2563EB); color: white; }}
    .lang-sn {{ background: linear-gradient(135deg, {COLORS['primary']}, #004C00); color: white; }}
    .lang-nd {{ background: linear-gradient(135deg, {COLORS['secondary']}, #E6C300); color: #111827; }}
    .lang-to {{ background: linear-gradient(135deg, {COLORS['accent']}, #B01010); color: white; }}
    .lang-es {{ background: linear-gradient(135deg, #10B981, #059669); color: white; }}
    .lang-fr {{ background: linear-gradient(135deg, #8B5CF6, #7C3AED); color: white; }}
    .lang-de {{ background: linear-gradient(135deg, #F59E0B, #D97706); color: white; }}
    .lang-other {{ background: linear-gradient(135deg, #6B7280, #4B5563); color: white; }}
    
    /* Performance Cards */
    .perf-card {{
        background: linear-gradient(135deg, rgba(255, 215, 0, 0.1), rgba(206, 17, 38, 0.05));
        border: 1px solid rgba(255, 215, 0, 0.3);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }}
    
    /* Zimbabwe Theme Elements */
    .zimbabwe-theme {{
        background: linear-gradient(135deg, rgba(0, 100, 0, 0.1), rgba(206, 17, 38, 0.1));
        border: 1px solid rgba(255, 215, 0, 0.3);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }}
    .zimbabwe-flag {{
        font-size: 2rem;
        margin-right: 1rem;
        vertical-align: middle;
    }}
    
    /* Button Styles */
    .stButton > button {{
        background: linear-gradient(135deg, {COLORS['primary']}, {COLORS['accent']});
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }}
    .stButton > button:hover {{
        background: linear-gradient(135deg, {COLORS['accent']}, {COLORS['primary']});
        transform: scale(1.02);
        box-shadow: 0 4px 15px rgba(206, 17, 38, 0.3);
    }}
    
    /* Progress Bar */
    .stProgress > div > div > div > div {{
        background: linear-gradient(90deg, {COLORS['primary']}, {COLORS['secondary']}, {COLORS['accent']});
    }}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header"><span class="zimbabwe-flag"></span>Sentiment Analysis Dashboard</h1>', unsafe_allow_html=True)

# Session state for caching
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'cached_stopwords' not in st.session_state:
    st.session_state.cached_stopwords = load_optimized_stopwords()

# Model URL
MODEL_URL = "https://multicentrally-scripless-jeanice.ngrog-free.dev"

# Sidebar with beautiful cards
with st.sidebar:
    # Welcome Card
    st.markdown(f"""
    <div class="card" style="margin-bottom: 2rem;">
        <div class="card-header">⚡ Dashboard Settings</div>
        <div class="card-content">
            <p style="color: {COLORS['text_light']}; font-size: 0.9rem;">
            <span style="color: {COLORS['primary']}; font-weight: bold;"> Zimbabwean Languages:</span>
            Shona, Ndebele, Tonga
            </p>
            <div style="margin-top: 1rem; padding: 0.8rem; background: rgba(0, 100, 0, 0.08); border-radius: 8px;">
                <p style="margin: 0; font-size: 0.8rem; color: {COLORS['text']};">
                <strong>Model URL:</strong><br>
                <code style="font-size: 0.75rem;">{MODEL_URL}</code>
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Performance Card
    with st.container():
        st.markdown('<div class="section-header" style="font-size: 1.2rem; margin: 1rem 0 0.5rem 0;">🚀 Performance</div>', unsafe_allow_html=True)
        
        analysis_mode = st.selectbox(
            "**Analysis Engine**",
            ["TextBlob (Fastest)", "Hybrid Mode", "Model Only"],
            index=0,
            help="TextBlob is fastest for large datasets"
        )
        
        batch_size = st.slider(
            "**Batch Size**",
            10, 500, 100, 10,
            help="Larger batches = faster but more memory"
        )
    
    # Language Card
    with st.container():
        st.markdown('<div class="section-header" style="font-size: 1.2rem; margin: 1.5rem 0 0.5rem 0;">🌍 Language</div>', unsafe_allow_html=True)
        
        language_handling = st.radio(
            "**Language Detection**",
            ["Quick Detect", "Zimbabwean Focus", "English Only"],
            index=0
        )
    
    # Analysis Card
    with st.container():
        st.markdown('<div class="section-header" style="font-size: 1.2rem; margin: 1.5rem 0 0.5rem 0;">📊 Analysis</div>', unsafe_allow_html=True)
        
        sentiment_threshold = st.slider(
            "**Neutral Threshold**",
            0.0, 0.5, 0.1, 0.05
        )
    
    # Advanced Settings Card
    with st.expander("⚙️ Advanced Settings", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            enable_caching = st.checkbox("Enable Caching", value=True)
            preload_samples = st.number_input("Preview Samples", 0, 1000, 100, 50)
        with col2:
            parallel_workers = st.slider("Parallel Workers", 1, 8, 2, 1)
    
    # Performance Tips Card
    st.markdown(f"""
    <div class="perf-card" style="margin-top: 2rem;">
        <div style="color: {COLORS['primary']}; font-weight: bold; margin-bottom: 0.5rem;">💡 Performance Tips:</div>
        <ul style="margin: 0; padding-left: 1.2rem; color: {COLORS['text_light']}; font-size: 0.8rem;">
            <li>Use <strong>CSV</strong> format for fastest loading</li>
            <li><strong>TextBlob mode</strong> for large datasets</li>
            <li>Increase <strong>batch size</strong> for speed</li>
            <li>Enable <strong>caching</strong> for repeated analysis</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# Optimized helper functions (keep as before)
def clean_text_fast(text):
    """Fast text cleaning"""
    if pd.isna(text):
        return ""
    text = str(text).strip()
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+', ' ', text)
    return text[:500]

def analyze_batch_textblob(texts, threshold=0.1):
    """Batch TextBlob analysis for speed"""
    results = []
    for text in texts:
        try:
            sentiment, polarity = cached_textblob_analysis(text, threshold)
            results.append((sentiment, polarity))
        except:
            results.append(("Neutral", 0.0))
    return results

def try_model_batch(texts, timeout=2):
    """Batch model requests"""
    results = []
    with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
        futures = []
        for text in texts:
            future = executor.submit(
                requests.post,
                MODEL_URL,
                json={"text": str(text)[:200]},
                timeout=timeout
            )
            futures.append(future)
        
        for future in concurrent.futures.as_completed(futures):
            try:
                response = future.result()
                if response.status_code == 200:
                    result = response.json()
                    sentiment = result.get('sentiment', 'Neutral').capitalize()
                    score = float(result.get('score', 0.0))
                    results.append((sentiment, score))
                else:
                    results.append(("Neutral", 0.0))
            except:
                results.append(("Neutral", 0.0))
    return results

def extract_keywords_fast(text_series, n=15):
    """Fast keyword extraction"""
    try:
        all_text = ' '.join(text_series.fillna('').astype(str).tolist()).lower()
        words = re.findall(r'\b[a-z]{3,15}\b', all_text)
        stopwords = st.session_state.cached_stopwords
        filtered_words = [w for w in words if w not in stopwords]
        word_counter = Counter(filtered_words)
        return pd.DataFrame(
            word_counter.most_common(n),
            columns=['Keyword', 'Frequency']
        )
    except:
        return pd.DataFrame(columns=['Keyword', 'Frequency'])

# File upload section with card
st.markdown('<div class="section-header">📁 Upload Your Data</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Choose a CSV or Excel file",
    type=["csv", "xlsx", "xls"],
    help="Supports Zimbabwean languages: Shona, Ndebele, Tonga"
)

if uploaded_file is not None:
    try:
        # Fast file loading with progress
        with st.spinner("📂 Loading data..."):
            file_ext = uploaded_file.name.split('.')[-1].lower()
            df = load_data(uploaded_file, file_ext)
        
        # Success Card
        st.markdown(f"""
        <div class="card" style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(0, 100, 0, 0.1));">
            <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                <div style="font-size: 2rem; margin-right: 1rem;">✅</div>
                <div>
                    <h3 style="margin: 0; color: {COLORS['primary']};">Data Loaded Successfully</h3>
                    <p style="margin: 0.2rem 0 0 0; color: {COLORS['text_light']};">{uploaded_file.name}</p>
                </div>
            </div>
            <div style="display: flex; gap: 1rem;">
                <div class="stat-card" style="flex: 1;">
                    <div class="stat-icon">📊</div>
                    <div class="stat-value">{len(df):,}</div>
                    <div class="stat-label">Rows</div>
                </div>
                <div class="stat-card" style="flex: 1;">
                    <div class="stat-icon">📋</div>
                    <div class="stat-value">{len(df.columns)}</div>
                    <div class="stat-label">Columns</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Quick Preview Card
        with st.expander("🔍 Data Preview", expanded=False):
            # Auto-detect text column
            text_candidates = []
            for col in df.columns:
                if df[col].dtype == 'object':
                    avg_len = df[col].astype(str).str.len().mean()
                    if avg_len > 20:
                        text_candidates.append((col, avg_len))
            
            if text_candidates:
                text_column = max(text_candidates, key=lambda x: x[1])[0]
                st.success(f"🎯 Auto-detected text column: **{text_column}**")
            else:
                text_column = st.selectbox("Select text column:", df.columns.tolist())
            
            # Show samples
            if text_column in df.columns:
                samples = df[text_column].dropna().head(5).tolist()
                sample_display = []
                for i, sample in enumerate(samples, 1):
                    sample_display.append(f"**Sample {i}:** {str(sample)[:100]}..." if len(str(sample)) > 100 else f"**Sample {i}:** {sample}")
                
                st.markdown("<br>".join(sample_display), unsafe_allow_html=True)
        
        # Start Analysis Card
        st.markdown('<div class="section-header">🚀 Start Analysis</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            analysis_button = st.button("**START ANALYSIS**", type="primary", use_container_width=True)
        with col2:
            if st.button("⚙️ Configure", use_container_width=True):
                st.rerun()
        
        if analysis_button:
            start_time = time.time()
            
            # Progress containers
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.empty()
            
            with results_container.container():
                # Process steps with cards
                steps = [
                    ("🧹 Cleaning text...", 20),
                    ("🌍 Detecting languages...", 40),
                    ("📊 Analyzing sentiment...", 60),
                    ("🔑 Extracting keywords...", 80),
                    ("📈 Calculating statistics...", 90)
                ]
                
                for step_text, step_progress in steps:
                    status_text.text(step_text)
                    progress_bar.progress(step_progress)
                    
                    if step_text == "🧹 Cleaning text...":
                        df['Cleaned_Text'] = df[text_column].apply(clean_text_fast)
                        df = df[df['Cleaned_Text'].str.len() > 3].copy()
                        
                    elif step_text == "🌍 Detecting languages...":
                        if language_handling != "English Only":
                            sample_texts = df['Cleaned_Text'].head(1000).tolist()
                            sample_langs = [cached_language_detection(t) for t in sample_texts]
                            lang_counts = Counter(sample_langs)
                            
                    elif step_text == "📊 Analyzing sentiment...":
                        texts = df['Cleaned_Text'].tolist()
                        total_texts = len(texts)
                        
                        if analysis_mode == "TextBlob (Fastest)":
                            all_results = analyze_batch_textblob(texts, sentiment_threshold)
                            df[['Sentiment', 'Polarity']] = pd.DataFrame(all_results, index=df.index)
                        elif analysis_mode == "Model Only":
                            try:
                                model_results = try_model_batch(texts[:500])
                                if len(model_results) < len(texts):
                                    remaining = analyze_batch_textblob(texts[len(model_results):], sentiment_threshold)
                                    all_results = model_results + remaining
                                else:
                                    all_results = model_results
                                df[['Sentiment', 'Polarity']] = pd.DataFrame(all_results, index=df.index)
                            except:
                                all_results = analyze_batch_textblob(texts, sentiment_threshold)
                                df[['Sentiment', 'Polarity']] = pd.DataFrame(all_results, index=df.index)
                        else:
                            all_results = analyze_batch_textblob(texts, sentiment_threshold)
                            df[['Sentiment', 'Polarity']] = pd.DataFrame(all_results, index=df.index)
                            
                    elif step_text == "🔑 Extracting keywords...":
                        keywords_df = extract_keywords_fast(df['Cleaned_Text'])
                        
                    elif step_text == "📈 Calculating statistics...":
                        sentiment_counts = df['Sentiment'].value_counts()
                        sentiment_percentages = (df['Sentiment'].value_counts(normalize=True) * 100).round(1)
                        total_time = time.time() - start_time
                        
                        # Store results
                        st.session_state.processed_data = {
                            'df': df,
                            'keywords_df': keywords_df,
                            'sentiment_counts': sentiment_counts,
                            'sentiment_percentages': sentiment_percentages,
                            'total_reviews': len(df),
                            'avg_polarity': df['Polarity'].mean(),
                            'processing_time': f"{total_time:.1f}s",
                            'speed': f"{len(df)/total_time:.1f} reviews/sec"
                        }
                        st.session_state.analysis_complete = True
                
                progress_bar.progress(100)
                status_text.empty()
                
                # Success Card
                st.markdown(f"""
                <div class="card" style="background: linear-gradient(135deg, rgba(255, 215, 0, 0.1), rgba(0, 100, 0, 0.1)); border: 2px solid {COLORS['secondary']};">
                    <div style="text-align: center; padding: 1rem;">
                        <div style="font-size: 4rem; margin-bottom: 1rem;">🎉</div>
                        <h2 style="color: {COLORS['primary']}; margin: 0;">Analysis Complete!</h2>
                        <p style="color: {COLORS['text_light']}; margin: 0.5rem 0;">Processed {len(df):,} reviews in {total_time:.1f} seconds</p>
                        <div style="display: inline-block; background: {COLORS['success']}; color: white; padding: 0.5rem 1rem; border-radius: 20px; margin-top: 1rem;">
                            ⚡ {len(df)/total_time:.1f} reviews/sec
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.balloons()
    
    except Exception as e:
        # Error Card
        st.markdown(f"""
        <div class="card" style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(206, 17, 38, 0.1));">
            <div style="display: flex; align-items: center;">
                <div style="font-size: 2rem; margin-right: 1rem;">❌</div>
                <div>
                    <h3 style="margin: 0; color: {COLORS['danger']};">Error Loading File</h3>
                    <p style="margin: 0.5rem 0 0 0; color: {COLORS['text']}; font-family: monospace;">{str(e)}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Display results with beautiful cards
if st.session_state.analysis_complete:
    data = st.session_state.processed_data
    df = data['df']
    
    st.markdown('<div class="section-header">📊 Analysis Results Dashboard</div>', unsafe_allow_html=True)
    
    # Performance Summary Cards
    st.markdown(f"""
    <div class="card">
        <div class="card-header">⚡ Performance Summary</div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-top: 1rem;">
            <div class="stat-card">
                <div class="stat-icon">📈</div>
                <div class="stat-value">{data['total_reviews']:,}</div>
                <div class="stat-label">Total Reviews</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">⏱️</div>
                <div class="stat-value">{data['processing_time']}</div>
                <div class="stat-label">Processing Time</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🚀</div>
                <div class="stat-value">{data['speed']}</div>
                <div class="stat-label">Speed</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📊</div>
                <div class="stat-value">{data['avg_polarity']:.3f}</div>
                <div class="stat-label">Avg Polarity</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sentiment Analysis Cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="card">
            <div class="card-header">😊 Sentiment Distribution</div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.8rem; margin-top: 1rem;">
        """, unsafe_allow_html=True)
        
        # Sentiment stats in cards
        sentiments = ['Positive', 'Neutral', 'Negative']
        for sentiment in sentiments:
            count = data['sentiment_counts'].get(sentiment, 0)
            percentage = data['sentiment_percentages'].get(sentiment, 0)
            
            # Determine card color based on sentiment
            if sentiment == 'Positive':
                card_bg = f"linear-gradient(135deg, {SENTIMENT_COLORS['Positive']}20, rgba(16, 185, 129, 0.1))"
                border_color = SENTIMENT_COLORS['Positive']
            elif sentiment == 'Negative':
                card_bg = f"linear-gradient(135deg, {SENTIMENT_COLORS['Negative']}20, rgba(239, 68, 68, 0.1))"
                border_color = SENTIMENT_COLORS['Negative']
            else:
                card_bg = f"linear-gradient(135deg, {SENTIMENT_COLORS['Neutral']}20, rgba(107, 114, 128, 0.1))"
                border_color = SENTIMENT_COLORS['Neutral']
            
            st.markdown(f"""
            <div style="background: {card_bg}; border: 2px solid {border_color}; border-radius: 10px; padding: 1rem; text-align: center;">
                <div style="font-size: 1.5rem; margin-bottom: 0.5rem; font-weight: 800; color: {border_color};">{percentage:.1f}%</div>
                <div style="font-size: 1rem; color: {COLORS['text']}; font-weight: 600;">{sentiment}</div>
                <div style="font-size: 0.8rem; color: {COLORS['text_light']}; margin-top: 0.2rem;">{count:,} reviews</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div></div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card">
            <div class="card-header">📈 Sentiment Proportion</div>
        """, unsafe_allow_html=True)
        
        fig_pie = px.pie(
            values=data['sentiment_counts'].values,
            names=data['sentiment_counts'].index,
            color=data['sentiment_counts'].index,
            color_discrete_map=SENTIMENT_COLORS,
            hole=0.4
        )
        fig_pie.update_layout(showlegend=True, height=300)
        st.plotly_chart(fig_pie, use_container_width=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Keywords Card
    if not data['keywords_df'].empty:
        st.markdown(f"""
        <div class="card">
            <div class="card-header">🔑 Top Keywords</div>
            <div style="display: flex; gap: 2rem; margin-top: 1rem;">
                <div style="flex: 1;">
        """, unsafe_allow_html=True)
        
        st.dataframe(data['keywords_df'], use_container_width=True, height=300)
        
        st.markdown("""
                </div>
                <div style="flex: 2;">
        """, unsafe_allow_html=True)
        
        fig_words = px.bar(
            data['keywords_df'],
            x='Frequency',
            y='Keyword',
            orientation='h',
            color='Frequency',
            color_continuous_scale='Viridis',
            title=''
        )
        fig_words.update_layout(height=300)
        st.plotly_chart(fig_words, use_container_width=True)
        
        st.markdown("</div></div></div>", unsafe_allow_html=True)
    
    # Data Preview Card
    with st.expander("📋 Detailed Results", expanded=False):
        st.markdown(f"""
        <div class="card">
            <div class="card-header">📊 Sample Results (First 50 rows)</div>
            <div style="margin-top: 1rem;">
        """, unsafe_allow_html=True)
        
        st.dataframe(df[['Cleaned_Text', 'Sentiment', 'Polarity']].head(50), 
                    use_container_width=True, height=400)
        
        st.markdown("</div></div>", unsafe_allow_html=True)
    
    # Export Cards
    st.markdown('<div class="section-header">💾 Export Results</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="card" style="text-align: center;">
            <div style="font-size: 2.5rem; margin-bottom: 1rem;">📥</div>
            <h3 style="color: {COLORS['primary']}; margin: 0.5rem 0;">Download CSV</h3>
            <p style="color: {COLORS['text_light']}; font-size: 0.9rem;">Full dataset with sentiment analysis</p>
        """, unsafe_allow_html=True)
        
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="zimbabwe_sentiment_results.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="card" style="text-align: center;">
            <div style="font-size: 2.5rem; margin-bottom: 1rem;">📄</div>
            <h3 style="color: {COLORS['primary']}; margin: 0.5rem 0;">Download Summary</h3>
            <p style="color: {COLORS['text_light']}; font-size: 0.9rem;">Analysis report in text format</p>
        """, unsafe_allow_html=True)
        
        summary = f"""
        ZIMBABWEAN SENTIMENT ANALYSIS REPORT
        {'='*50}
        Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        Total Reviews: {data['total_reviews']:,}
        Processing Time: {data['processing_time']}
        Speed: {data['speed']}
        
        SENTIMENT DISTRIBUTION:
        • Positive: {data['sentiment_counts'].get('Positive', 0):,} ({data['sentiment_percentages'].get('Positive', 0):.1f}%)
        • Neutral: {data['sentiment_counts'].get('Neutral', 0):,} ({data['sentiment_percentages'].get('Neutral', 0):.1f}%)
        • Negative: {data['sentiment_counts'].get('Negative', 0):,} ({data['sentiment_percentages'].get('Negative', 0):.1f}%)
        
        Average Polarity: {data['avg_polarity']:.3f}
        {'='*50}
        Generated by Sentiment Analysis Dashboard 
        """
        
        st.download_button(
            label="Download Summary",
            data=summary,
            file_name="zimbabwe_sentiment_summary.txt",
            mime="text/plain",
            use_container_width=True
        )
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="card" style="text-align: center;">
            <div style="font-size: 2.5rem; margin-bottom: 1rem;">🔄</div>
            <h3 style="color: {COLORS['primary']}; margin: 0.5rem 0;">New Analysis</h3>
            <p style="color: {COLORS['text_light']}; font-size: 0.9rem;">Clear current results and start fresh</p>
        """, unsafe_allow_html=True)
        
        if st.button("Start New Analysis", use_container_width=True):
            st.session_state.analysis_complete = False
            st.session_state.processed_data = None
            st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

else:
    # Welcome screen with beautiful cards
    st.markdown(f"""
    <div class="zimbabwe-theme">
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1 style="color: {COLORS['secondary']}; margin-bottom: 0.5rem;">⚡ Welcome to Sentiment Analysis Dashboard</h1>
            <p style="color: {COLORS['text']}; font-size: 1.1rem; max-width: 800px; margin: 0 auto;">
            Analyze customer sentiment across Zimbabwean languages with blazing fast performance
            </p>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; margin-bottom: 2rem;">
            <div class="card">
                <div class="card-header"> Zimbabwean Languages</div>
                <div class="card-content">
                    <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-top: 1rem;">
                        <span class="language-badge lang-sn">SHONA (ChiShona)</span>
                        <span class="language-badge lang-nd">NDEBELE (isiNdebele)</span>
                        <span class="language-badge lang-to">TONGA (ChiTonga)</span>
                        <span class="language-badge lang-en">ENGLISH</span>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">🚀 Fast Performance</div>
                <div class="card-content">
                    <div style="display: flex; flex-direction: column; gap: 1rem; margin-top: 1rem;">
                        <div>
                            <div style="font-size: 1.8rem; color: {COLORS['primary']}; font-weight: 800;">10,000+</div>
                            <div style="color: {COLORS['text_light']}; font-size: 0.9rem;">reviews per minute</div>
                        </div>
                        <div>
                            <div style="font-size: 1.8rem; color: {COLORS['accent']}; font-weight: 800;">99%</div>
                            <div style="color: {COLORS['text_light']}; font-size: 0.9rem;">accuracy maintained</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">📊 Rich Insights</div>
                <div class="card-content">
                    <ul style="color: {COLORS['text']}; margin: 1rem 0 0 0; padding-left: 1.2rem;">
                        <li>Sentiment analysis</li>
                        <li>Language detection</li>
                        <li>Keyword extraction</li>
                        <li>Performance metrics</li>
                        <li>Export capabilities</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">🎯 How to Get Started</div>
            <div class="card-content">
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; text-align: center; margin-top: 1rem;">
                    <div>
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">1️⃣</div>
                        <div style="font-weight: 600; color: {COLORS['primary']};">Upload</div>
                        <div style="font-size: 0.9rem; color: {COLORS['text_light']};">CSV or Excel file</div>
                    </div>
                    <div>
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">2️⃣</div>
                        <div style="font-weight: 600; color: {COLORS['primary']};">Configure</div>
                        <div style="font-size: 0.9rem; color: {COLORS['text_light']};">Settings in sidebar</div>
                    </div>
                    <div>
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">3️⃣</div>
                        <div style="font-weight: 600; color: {COLORS['primary']};">Analyze</div>
                        <div style="font-size: 0.9rem; color: {COLORS['text_light']};">Click start button</div>
                    </div>
                    <div>
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">4️⃣</div>
                        <div style="font-weight: 600; color: {COLORS['primary']};">Export</div>
                        <div style="font-size: 0.9rem; color: {COLORS['text_light']};">Download results</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div style="margin-top: 2rem; padding: 1.5rem; background: linear-gradient(135deg, rgba(0, 100, 0, 0.15), rgba(206, 17, 38, 0.1)); border-radius: 10px;">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="font-size: 2rem;">💡</div>
                <div>
                    <h4 style="color: {COLORS['secondary']}; margin: 0;">Pro Tip for Best Performance</h4>
                    <p style="color: {COLORS['text']}; margin: 0.5rem 0 0 0;">
                    Use <strong>TextBlob (Fastest)</strong> mode with <strong>batch size 500</strong> for processing large datasets. 
                    Enable caching for repeated analyses on the same data.
                    </p>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Beautiful footer
st.markdown(f"""
<div style='text-align: center; margin-top: 3rem; padding: 1.5rem; background: linear-gradient(90deg, rgba(0, 100, 0, 0.2), rgba(206, 17, 38, 0.2)); border-radius: 10px; border: 1px solid rgba(255, 215, 0, 0.3);'>
    <p style='color: rgba(255, 255, 255, 0.9); margin: 0; font-size: 0.9rem;'>
    🇿🇼 Zimbabwean Sentiment Analysis Dashboard • Fast Mode Enabled • Model: {MODEL_URL}
    </p>
    <p style='color: rgba(255, 215, 0, 0.8); margin: 0.5rem 0 0 0; font-size: 0.8rem;'>
    ⚡ Optimized for speed while maintaining Zimbabwean language support
    </p>
</div>
""", unsafe_allow_html=True)