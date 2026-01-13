"""Streamlit dashboard for BookSpring metrics - Strategic Goals Edition."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
from collections import Counter
from dateutil.relativedelta import relativedelta
import sys
import os
from pathlib import Path
import json
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote

# Google Sheets imports
import gspread
from google.oauth2.service_account import Credentials

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.fusioo_client import FusiooClient, ACTIVITY_REPORT_APP_ID, LEGACY_DATA_APP_ID, B3_CHILD_FAMILY_APP_ID, EVENTS_APP_ID, PARTNERS_APP_ID
from src.data.processor import DataProcessor, get_friendly_name, TimeUnit
from src.reports.excel_generator import generate_standard_report

# App IDs
ORIGINAL_BOOKS_APP_ID = os.getenv("ORIGINAL_BOOKS_APP_ID", "ib506ce2df9e6443e88ded1316581d74e")
CONTENT_VIEWS_APP_ID = os.getenv("CONTENT_VIEWS_APP_ID", "i43f611d038d24840907ff5b2970eeb3c")

# Google Sheets configuration
FINANCIAL_SHEET_ID = os.getenv("FINANCIAL_SHEET_ID", "17jObocsIQJnazyvWToi_AtsrLJ1I9bnMpWw9BMiixA8")

# DonorPerfect API configuration
DONORPERFECT_LOGIN = os.getenv("DONORPERFECT_LOGIN", "Yash")
DONORPERFECT_PASSWORD = os.getenv("DONORPERFECT_PASSWORD", "rumjec-gobpA5-rudbun")
DONORPERFECT_BASE_URL = "https://www.donorperfect.net/prod/xmlrequest.asp"

# Legacy fields that need to be renamed to match current schema
LEGACY_FIELD_MAP = {
    "average_engagement_duration": "minutes_of_activity",
    "date": "date_of_activity",  # Current data uses date_of_activity, legacy uses date
}

# Fields to copy as-is from legacy data (DataProcessor handles these natively)
LEGACY_PASSTHROUGH_FIELDS = [
    "children_03_years",
    "children_34_years",
    "children_512_years",
    "children_912_years",
    "teens",
    "parents_or_caregivers",
    "_of_books_distributed",
    "total_children",
    "previously_served_this_fy",
]

# Brand Colors
COLORS = {
    "primary": "#1a365d",       # Deep navy blue
    "primary_light": "#2c5282",
    "secondary": "#38a169",     # Success green
    "accent": "#ed8936",        # Warm orange
    "accent_alt": "#9f7aea",    # Purple
    "background": "#f7fafc",
    "surface": "#ffffff",
    "text": "#1a202c",
    "text_muted": "#718096",
    "border": "#e2e8f0",
    "gradient_start": "#667eea",
    "gradient_end": "#764ba2",
}

# Page config
st.set_page_config(
    page_title="BookSpring Strategic Dashboard",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern CSS with glassmorphism, animations, and beautiful styling
st.markdown("""
<style>
    /* ========================================
       ROOT & GLOBAL STYLES
       ======================================== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    :root {
        --primary: #1a365d;
        --primary-light: #2c5282;
        --secondary: #38a169;
        --accent: #ed8936;
        --accent-alt: #9f7aea;
        --surface: #ffffff;
        --background: #f7fafc;
        --text: #1a202c;
        --text-muted: #718096;
        --border: #e2e8f0;
        --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        --shadow-lg: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        --shadow-xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        --radius-sm: 8px;
        --radius: 12px;
        --radius-lg: 16px;
        --radius-xl: 24px;
    }

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Clean white background for main area */
    .stApp {
        background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
    }

    .main .block-container {
        padding: 1.5rem 2rem 3rem 2rem;
        max-width: 1400px;
        background: transparent;
    }

    /* Hide Streamlit branding but keep sidebar toggle */
    #MainMenu, footer {visibility: hidden;}

    /* Fix sidebar toggle button icon */
    button[kind="headerNoPadding"] span {
        font-size: 0 !important;
    }
    button[kind="headerNoPadding"] span::before {
        content: "☰";
        font-size: 1.5rem;
        color: #1a365d;
    }
    [data-testid="collapsedControl"] {
        color: #1a365d;
    }
    [data-testid="collapsedControl"] svg {
        display: none;
    }
    [data-testid="collapsedControl"]::before {
        content: "☰";
        font-size: 1.5rem;
    }

    /* ========================================
       HERO HEADER
       ======================================== */
    .hero-container {
        background: linear-gradient(135deg, #1a365d 0%, #2c5282 50%, #38a169 100%);
        border-radius: var(--radius-xl);
        padding: 2.5rem 3rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
        box-shadow: var(--shadow-xl);
    }

    .hero-container::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 60%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        transform: rotate(-15deg);
    }

    .hero-container::after {
        content: '';
        position: absolute;
        bottom: -30%;
        left: -10%;
        width: 40%;
        height: 150%;
        background: radial-gradient(circle, rgba(56,161,105,0.3) 0%, transparent 70%);
    }

    .hero-content {
        position: relative;
        z-index: 1;
    }

    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        color: white;
        margin: 0 0 0.5rem 0;
        letter-spacing: -0.02em;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .hero-subtitle {
        font-size: 1.1rem;
        color: rgba(255,255,255,0.9);
        margin: 0;
        font-weight: 400;
    }

    .hero-stats {
        display: flex;
        gap: 2rem;
        margin-top: 1.5rem;
        flex-wrap: wrap;
    }

    .hero-stat {
        background: rgba(255,255,255,0.15);
        backdrop-filter: blur(10px);
        padding: 1rem 1.5rem;
        border-radius: var(--radius);
        border: 1px solid rgba(255,255,255,0.2);
    }

    .hero-stat-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: white;
    }

    .hero-stat-label {
        font-size: 0.85rem;
        color: rgba(255,255,255,0.8);
        margin-top: 0.25rem;
    }

    /* ========================================
       SECTION HEADERS
       ======================================== */
    .section-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
        padding: 1.25rem 1.5rem;
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border-radius: 12px;
        border: 1px solid #e2e8f0;
    }

    .section-icon {
        width: 48px;
        height: 48px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        flex-shrink: 0;
    }

    .section-icon.goal1 { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .section-icon.goal2 { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .section-icon.goal3 { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    .section-icon.goal4 { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
    .section-icon.financial { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
    .section-icon.trends { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); }
    .section-icon.compare { background: linear-gradient(135deg, #d299c2 0%, #fef9d7 100%); }

    .section-title-group {
        flex: 1;
    }

    .section-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text);
        margin: 0;
        letter-spacing: -0.01em;
    }

    .section-subtitle {
        font-size: 0.9rem;
        color: var(--text-muted);
        margin: 0.25rem 0 0 0;
    }

    /* ========================================
       GOAL CARDS
       ======================================== */
    .goal-card {
        background: var(--surface);
        border-radius: var(--radius-lg);
        padding: 1.75rem;
        margin-bottom: 1.5rem;
        box-shadow: var(--shadow);
        border: 1px solid var(--border);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .goal-card:hover {
        box-shadow: var(--shadow-lg);
        transform: translateY(-2px);
    }

    .goal-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
    }

    .goal-card.goal1::before { background: linear-gradient(90deg, #667eea, #764ba2); }
    .goal-card.goal2::before { background: linear-gradient(90deg, #f093fb, #f5576c); }
    .goal-card.goal3::before { background: linear-gradient(90deg, #4facfe, #00f2fe); }
    .goal-card.goal4::before { background: linear-gradient(90deg, #43e97b, #38f9d7); }

    /* ========================================
       METRIC CARDS
       ======================================== */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    .metric-card {
        background: linear-gradient(135deg, var(--surface) 0%, #f7fafc 100%);
        border-radius: var(--radius);
        padding: 1.25rem 1.5rem;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
        transition: all 0.2s ease;
        position: relative;
        overflow: hidden;
    }

    .metric-card:hover {
        box-shadow: var(--shadow);
        border-color: #cbd5e0;
    }

    .metric-card::after {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 60px;
        height: 60px;
        background: linear-gradient(135deg, transparent 50%, rgba(26,54,93,0.03) 50%);
    }

    .metric-icon {
        font-size: 1.5rem;
        margin-bottom: 0.5rem;
    }

    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--text);
        margin: 0;
        letter-spacing: -0.02em;
    }

    .metric-label {
        font-size: 0.85rem;
        color: var(--text-muted);
        margin: 0.25rem 0 0 0;
        font-weight: 500;
    }

    .metric-delta {
        font-size: 0.75rem;
        font-weight: 600;
        margin-top: 0.5rem;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        display: inline-block;
    }

    .metric-delta.positive {
        background: #c6f6d5;
        color: #22543d;
    }

    .metric-delta.negative {
        background: #fed7d7;
        color: #822727;
    }

    /* Custom metric box to match Streamlit metrics */
    .metric-box {
        background: linear-gradient(135deg, var(--surface) 0%, #f7fafc 100%);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 1.25rem;
        box-shadow: var(--shadow-sm);
        transition: all 0.2s ease;
    }

    .metric-box:hover {
        box-shadow: var(--shadow);
        border-color: #cbd5e0;
    }

    /* ========================================
       STREAMLIT METRIC STYLING
       ======================================== */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
        transition: all 0.2s ease;
    }

    [data-testid="metric-container"]:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border-color: #cbd5e0;
        transform: translateY(-1px);
    }

    [data-testid="metric-container"] label {
        font-weight: 600 !important;
        color: #4a5568 !important;
        font-size: 0.875rem !important;
    }

    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-weight: 700 !important;
        color: #1a202c !important;
    }

    [data-testid="metric-container"] [data-testid="stMetricDelta"] {
        font-weight: 600 !important;
    }

    .metric-box .metric-label {
        font-size: 0.875rem;
        color: var(--text-muted);
        font-weight: 500;
        margin: 0 0 0.25rem 0;
    }

    .metric-box .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--text);
        margin: 0;
        letter-spacing: -0.02em;
    }

    .metric-box .metric-delta {
        font-size: 0.875rem;
        color: var(--text-muted);
        margin: 0.25rem 0 0 0;
        padding: 0;
        display: block;
        background: none;
    }

    /* Override Streamlit metric containers */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, var(--surface) 0%, #f7fafc 100%);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 1.25rem;
        box-shadow: var(--shadow-sm);
        transition: all 0.2s ease;
    }

    div[data-testid="metric-container"]:hover {
        box-shadow: var(--shadow);
        border-color: #cbd5e0;
    }

    div[data-testid="metric-container"] label {
        color: var(--text-muted) !important;
        font-weight: 500 !important;
    }

    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-weight: 700 !important;
        color: var(--text) !important;
    }

    /* ========================================
       PROGRESS BARS
       ======================================== */
    .progress-container {
        background: var(--border);
        border-radius: 100px;
        height: 12px;
        overflow: hidden;
        margin: 1rem 0;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
    }

    .progress-bar {
        height: 100%;
        border-radius: 100px;
        transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }

    .progress-bar::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(
            90deg,
            transparent,
            rgba(255,255,255,0.3),
            transparent
        );
        animation: shimmer 2s infinite;
    }

    @keyframes shimmer {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }

    .progress-bar.goal1 { background: linear-gradient(90deg, #667eea, #764ba2); }
    .progress-bar.goal2 { background: linear-gradient(90deg, #f093fb, #f5576c); }
    .progress-bar.goal3 { background: linear-gradient(90deg, #4facfe, #00f2fe); }
    .progress-bar.goal4 { background: linear-gradient(90deg, #43e97b, #38f9d7); }

    .progress-label {
        display: flex;
        justify-content: space-between;
        font-size: 0.85rem;
        color: var(--text-muted);
        margin-top: 0.5rem;
    }

    /* Override Streamlit progress bars */
    .stProgress > div > div {
        background: linear-gradient(90deg, #667eea, #764ba2) !important;
        border-radius: 100px;
    }

    .stProgress > div {
        background: var(--border) !important;
        border-radius: 100px;
        height: 10px !important;
    }

    /* ========================================
       PLACEHOLDER CARDS
       ======================================== */
    .placeholder-card {
        background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
        border: 2px dashed #cbd5e0;
        border-radius: var(--radius-lg);
        padding: 2rem;
        text-align: center;
        position: relative;
    }

    .placeholder-card h4 {
        color: var(--primary);
        font-weight: 600;
        margin: 0 0 1rem 0;
        font-size: 1.1rem;
    }

    .placeholder-card p {
        color: var(--text-muted);
        margin: 0;
        font-size: 0.9rem;
    }

    .placeholder-card ul {
        text-align: left;
        display: inline-block;
        margin: 1rem 0 0 0;
        padding-left: 1.5rem;
        color: var(--text-muted);
    }

    .placeholder-card li {
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }

    /* ========================================
       BUTTONS
       ======================================== */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
        color: white;
        border: none;
        border-radius: var(--radius);
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-size: 0.9rem;
        transition: all 0.3s ease;
        box-shadow: var(--shadow);
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-lg);
    }

    .stButton > button:active {
        transform: translateY(0);
    }

    /* Primary button style */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--secondary) 0%, #2f855a 100%);
    }

    /* ========================================
       SIDEBAR
       ======================================== */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        box-shadow: 2px 0 10px rgba(0,0,0,0.05);
        border-right: 1px solid #e2e8f0;
    }

    section[data-testid="stSidebar"] .stMarkdown {
        color: #475569;
    }

    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #1e3a5f !important;
    }

    section[data-testid="stSidebar"] label {
        color: #475569 !important;
    }

    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stDateInput label {
        color: #334155 !important;
        font-weight: 500;
    }

    section[data-testid="stSidebar"] hr {
        border-color: #e2e8f0;
        margin: 1.5rem 0;
    }

    section[data-testid="stSidebar"] .stButton > button {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        color: #1e3a5f;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #f1f5f9;
        border-color: #cbd5e1;
    }

    /* Sidebar targets section */
    .sidebar-targets {
        background: #ffffff;
        border-radius: var(--radius);
        padding: 1rem;
        margin-top: 1rem;
        border: 1px solid #e2e8f0;
    }

    .sidebar-target-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.5rem 0;
        border-bottom: 1px solid #e2e8f0;
        font-size: 0.85rem;
        color: #475569;
    }

    .sidebar-target-item:last-child {
        border-bottom: none;
    }

    /* ========================================
       DIVIDERS
       ======================================== */
    hr {
        border: none;
        border-top: 1px solid var(--border);
        margin: 2.5rem 0;
    }

    .section-divider {
        border: none;
        border-top: 2px solid var(--border);
        margin: 3rem 0;
        position: relative;
    }

    /* ========================================
       TABLES
       ======================================== */
    .stDataFrame {
        border-radius: var(--radius);
        overflow: hidden;
        border: 1px solid var(--border);
    }

    .stDataFrame [data-testid="stDataFrameResizable"] {
        border-radius: var(--radius);
    }

    /* ========================================
       EXPANDABLE SECTIONS
       ======================================== */
    .streamlit-expanderHeader {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        font-weight: 600;
        color: var(--text);
    }

    .streamlit-expanderContent {
        border: 1px solid var(--border);
        border-top: none;
        border-radius: 0 0 var(--radius) var(--radius);
    }

    /* ========================================
       PRINT VIEW STYLES
       ======================================== */
    .print-button-container {
        position: fixed;
        top: 70px;
        right: 20px;
        z-index: 1000;
    }

    .print-button {
        background: linear-gradient(135deg, #1a365d 0%, #2c5282 100%);
        color: white;
        border: none;
        border-radius: 50px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-size: 0.9rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        box-shadow: var(--shadow-lg);
        transition: all 0.3s ease;
    }

    .print-button:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-xl);
    }

    /* Print snapshot container */
    .print-snapshot {
        background: white;
        padding: 2rem;
        border-radius: var(--radius-xl);
        box-shadow: var(--shadow-xl);
        margin-bottom: 2rem;
        border: 1px solid var(--border);
    }

    .print-snapshot-header {
        text-align: center;
        margin-bottom: 2rem;
        padding-bottom: 1.5rem;
        border-bottom: 2px solid var(--border);
    }

    .print-snapshot-title {
        font-size: 1.75rem;
        font-weight: 800;
        color: var(--primary);
        margin: 0;
    }

    .print-snapshot-subtitle {
        color: var(--text-muted);
        margin: 0.5rem 0 0 0;
    }

    .print-goals-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1.5rem;
        margin-bottom: 1.5rem;
    }

    .print-goal-card {
        background: linear-gradient(135deg, #f7fafc 0%, white 100%);
        border-radius: var(--radius);
        padding: 1.25rem;
        border: 1px solid var(--border);
        position: relative;
        overflow: hidden;
    }

    .print-goal-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
    }

    .print-goal-card.g1::before { background: linear-gradient(90deg, #667eea, #764ba2); }
    .print-goal-card.g2::before { background: linear-gradient(90deg, #f093fb, #f5576c); }
    .print-goal-card.g3::before { background: linear-gradient(90deg, #4facfe, #00f2fe); }
    .print-goal-card.g4::before { background: linear-gradient(90deg, #43e97b, #38f9d7); }

    .print-goal-title {
        font-size: 0.9rem;
        font-weight: 700;
        color: var(--primary);
        margin: 0 0 0.75rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .print-metrics-row {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
    }

    .print-metric {
        flex: 1;
        min-width: 80px;
        text-align: center;
        padding: 0.5rem;
        background: white;
        border-radius: 6px;
        border: 1px solid var(--border);
    }

    .print-metric-value {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--text);
    }

    .print-metric-label {
        font-size: 0.7rem;
        color: var(--text-muted);
        margin-top: 0.25rem;
    }

    .print-progress {
        margin-top: 0.75rem;
    }

    .print-progress-bar {
        height: 6px;
        background: var(--border);
        border-radius: 100px;
        overflow: hidden;
    }

    .print-progress-fill {
        height: 100%;
        border-radius: 100px;
    }

    .print-progress-fill.g1 { background: linear-gradient(90deg, #667eea, #764ba2); }
    .print-progress-fill.g2 { background: linear-gradient(90deg, #f093fb, #f5576c); }
    .print-progress-fill.g3 { background: linear-gradient(90deg, #4facfe, #00f2fe); }
    .print-progress-fill.g4 { background: linear-gradient(90deg, #43e97b, #38f9d7); }

    .print-progress-text {
        font-size: 0.7rem;
        color: var(--text-muted);
        text-align: right;
        margin-top: 0.25rem;
    }

    /* ========================================
       PRINT MEDIA QUERIES
       ======================================== */
    @media print {
        /* Hide non-essential elements */
        section[data-testid="stSidebar"],
        .stButton,
        .print-button-container,
        header,
        footer,
        #MainMenu,
        .stSelectbox,
        .stDateInput,
        .stCheckbox,
        [data-testid="stToolbar"],
        .hero-container,
        hr {
            display: none !important;
        }

        /* Show only print snapshot */
        .main .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }

        .print-snapshot {
            box-shadow: none !important;
            border: none !important;
            padding: 0.5in !important;
            margin: 0 !important;
            page-break-inside: avoid;
        }

        .print-goals-grid {
            grid-template-columns: repeat(2, 1fr) !important;
        }

        /* Ensure colors print */
        * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }

        @page {
            size: letter landscape;
            margin: 0.25in;
        }
    }

    /* ========================================
       ANIMATIONS
       ======================================== */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .goal-card, .metric-card, div[data-testid="metric-container"] {
        animation: fadeInUp 0.5s ease-out forwards;
    }

    /* Staggered animation delays */
    .goal-card:nth-child(1) { animation-delay: 0.1s; }
    .goal-card:nth-child(2) { animation-delay: 0.2s; }
    .goal-card:nth-child(3) { animation-delay: 0.3s; }
    .goal-card:nth-child(4) { animation-delay: 0.4s; }

    /* ========================================
       RESPONSIVE / MOBILE STYLES
       ======================================== */

    /* Tablet styles */
    @media screen and (max-width: 1024px) {
        .main .block-container {
            padding: 1rem 1.5rem 2rem 1.5rem;
            max-width: 100%;
        }

        .hero-container {
            padding: 1.5rem 2rem;
        }

        .hero-stat-value {
            font-size: 2rem !important;
        }

        .section-title {
            font-size: 1.3rem !important;
        }
    }

    /* Mobile styles */
    @media screen and (max-width: 768px) {
        .main .block-container {
            padding: 0.75rem 1rem 2rem 1rem;
        }

        .hero-container {
            padding: 1.25rem 1.5rem;
            border-radius: var(--radius-lg);
        }

        .hero-stat-value {
            font-size: 1.5rem !important;
        }

        .hero-stat-label {
            font-size: 0.7rem !important;
        }

        .section-header {
            flex-direction: column;
            align-items: flex-start !important;
            gap: 0.5rem;
        }

        .section-icon {
            width: 40px;
            height: 40px;
            font-size: 1.25rem;
        }

        .section-title {
            font-size: 1.1rem !important;
        }

        .section-subtitle {
            font-size: 0.75rem !important;
        }

        /* Stack metric cards on mobile */
        div[data-testid="column"] {
            min-width: 100% !important;
        }

        div[data-testid="metric-container"] {
            padding: 0.75rem !important;
        }

        div[data-testid="metric-container"] label {
            font-size: 0.75rem !important;
        }

        div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
            font-size: 1.25rem !important;
        }

        /* Progress bars */
        .progress-container {
            height: 8px;
        }

        /* Charts responsive */
        .js-plotly-plot, .plotly {
            width: 100% !important;
        }

        /* Sidebar adjustments */
        section[data-testid="stSidebar"] {
            width: 280px !important;
            min-width: 280px !important;
        }

        section[data-testid="stSidebar"] > div {
            padding: 1rem;
        }
    }

    /* Small mobile styles */
    @media screen and (max-width: 480px) {
        .main .block-container {
            padding: 0.5rem 0.75rem 1.5rem 0.75rem;
        }

        .hero-container {
            padding: 1rem;
        }

        .hero-stat-value {
            font-size: 1.25rem !important;
        }

        .section-title {
            font-size: 1rem !important;
        }

        div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
            font-size: 1.1rem !important;
        }

        /* Hide less important elements on very small screens */
        .section-subtitle {
            display: none;
        }
    }

    /* Ensure touch-friendly tap targets */
    @media (hover: none) and (pointer: coarse) {
        button, .stButton > button {
            min-height: 44px;
            min-width: 44px;
        }

        input, select, textarea {
            font-size: 16px !important; /* Prevents zoom on iOS */
        }
    }
</style>
""", unsafe_allow_html=True)


# Chart theme configuration
CHART_TEMPLATE = {
    "layout": {
        "font": {"family": "Inter, sans-serif"},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "colorway": ["#667eea", "#38a169", "#ed8936", "#9f7aea", "#f5576c", "#4facfe"],
        "hoverlabel": {"bgcolor": "white", "font_size": 12, "font_family": "Inter"},
        "xaxis": {"gridcolor": "#e2e8f0", "linecolor": "#e2e8f0", "zerolinecolor": "#e2e8f0"},
        "yaxis": {"gridcolor": "#e2e8f0", "linecolor": "#e2e8f0", "zerolinecolor": "#e2e8f0"},
    }
}


def style_plotly_chart(fig, height=350):
    """Apply consistent styling to Plotly charts."""
    fig.update_layout(
        font_family="Inter, sans-serif",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter"),
        height=height,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#e2e8f0",
            borderwidth=1,
            font=dict(size=11)
        )
    )
    fig.update_xaxes(gridcolor="#e2e8f0", linecolor="#e2e8f0", tickfont=dict(size=11))
    fig.update_yaxes(gridcolor="#e2e8f0", linecolor="#e2e8f0", tickfont=dict(size=11))
    return fig


@st.cache_data(ttl=86400)  # Cache for 24 hours
def load_activity_data():
    """Load activity data from Fusioo API with caching."""
    try:
        client = FusiooClient()
        records = client.get_all_records(ACTIVITY_REPORT_APP_ID)
        return records
    except Exception as e:
        st.error(f"Failed to load activity data: {e}")
        return []


@st.cache_data(ttl=86400)  # Cache for 24 hours
def load_original_books():
    """Load Original Books data from Fusioo API."""
    try:
        client = FusiooClient()
        records = client.get_all_records(ORIGINAL_BOOKS_APP_ID)
        return records
    except Exception as e:
        st.error(f"Failed to load Original Books: {e}")
        return []


@st.cache_data(ttl=86400)  # Cache for 24 hours
def load_content_views():
    """Load Content Views data from Fusioo API."""
    try:
        client = FusiooClient()
        records = client.get_all_records(CONTENT_VIEWS_APP_ID)
        return records
    except Exception as e:
        st.error(f"Failed to load Content Views: {e}")
        return []


@st.cache_data(ttl=86400)  # Cache for 24 hours
def load_legacy_data():
    """Load legacy activity data from Fusioo API (pre-July 2025)."""
    try:
        client = FusiooClient()
        records = client.get_all_records(LEGACY_DATA_APP_ID)
        return records
    except Exception as e:
        st.error(f"Failed to load legacy data: {e}")
        return []


@st.cache_data(ttl=86400)  # Cache for 24 hours
def load_active_enrollment_count():
    """Load count of active enrollments from B3 Child/Family table.

    Only reads the active_enrollment field for counting - other fields are not stored.
    """
    try:
        client = FusiooClient()
        count = client.count_active_enrollments(B3_CHILD_FAMILY_APP_ID)
        return count
    except Exception as e:
        st.error(f"Failed to load enrollment count: {e}")
        return 0


@st.cache_data(ttl=86400)  # Cache for 24 hours
def load_financial_data():
    """Load financial data from Google Sheets."""
    try:
        # Get credentials from Streamlit secrets or environment
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
        else:
            # For local development, try to load from file
            creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if creds_path and os.path.exists(creds_path):
                with open(creds_path, 'r') as f:
                    creds_dict = json.load(f)
            else:
                return None

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)

        sheet = client.open_by_key(FINANCIAL_SHEET_ID).sheet1
        data = sheet.get_all_records()

        if data:
            df = pd.DataFrame(data)
            # Convert date column if present
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            return df
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"Could not load financial data: {e}")
        return None


@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_events_data():
    """Load events data from Fusioo."""
    try:
        client = FusiooClient()
        records = client.get_all_records(EVENTS_APP_ID)
        return records
    except Exception as e:
        st.error(f"Failed to load events data: {e}")
        return []


@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_partners_data():
    """Load partners data from Fusioo for partner name lookups (minimal fields for privacy)."""
    try:
        client = FusiooClient()
        # Only fetch fields needed for display - avoid loading PII
        records = client.get_all_records(PARTNERS_APP_ID, fields=["id", "site_name", "main_organization_from_list"])
        return records
    except Exception as e:
        st.error(f"Failed to load partners data: {e}")
        return []


@st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
def load_donorperfect_contacts(start_date: str, end_date: str, debug: bool = False) -> tuple:
    """Load contacts data from DonorPerfect API.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        debug: If True, return debug info along with data

    Returns:
        Tuple of (DataFrame, debug_info dict) if debug=True, else just DataFrame
    """
    debug_info = {}
    try:
        # Build the SQL query for DonorPerfect
        query = f"SELECT contact_date, activity_code, em_campaign_status, mailing_code FROM dpcontact WHERE contact_date BETWEEN '{start_date}' AND '{end_date}'"
        debug_info['query'] = query

        # URL encode the action parameter
        url = f"{DONORPERFECT_BASE_URL}?login={DONORPERFECT_LOGIN}&pass={DONORPERFECT_PASSWORD}&action={quote(query)}"
        # Mask password in debug URL
        debug_url = f"{DONORPERFECT_BASE_URL}?login={DONORPERFECT_LOGIN}&pass=****&action={quote(query)}"
        debug_info['url'] = debug_url

        response = requests.get(url, timeout=60)
        response.raise_for_status()
        debug_info['status_code'] = response.status_code
        debug_info['response_preview'] = response.text[:500] if response.text else "Empty response"

        # Parse XML response
        root = ET.fromstring(response.content)

        records = []
        for row in root.findall('.//row'):
            record = {}
            for field in row.findall('field'):
                name = field.get('name')
                value = field.text
                record[name] = value
            records.append(record)

        debug_info['records_found'] = len(records)

        df = pd.DataFrame(records)

        # Convert contact_date to datetime
        if 'contact_date' in df.columns:
            df['contact_date'] = pd.to_datetime(df['contact_date'], errors='coerce')

        if debug:
            return df, debug_info
        return df

    except Exception as e:
        debug_info['error'] = str(e)
        if debug:
            return pd.DataFrame(), debug_info
        return pd.DataFrame()


def get_fiscal_year_info(reference_date: date = None) -> dict:
    """Calculate fiscal year dates dynamically.

    BookSpring fiscal year runs July 1 - June 30.
    FY naming convention: FY26 = July 1, 2025 - June 30, 2026

    Args:
        reference_date: Date to calculate FY for (defaults to today)

    Returns:
        Dictionary with fiscal year info including start dates and labels
    """
    if reference_date is None:
        reference_date = date.today()

    # Determine current fiscal year start
    # If we're in Jan-Jun, FY started previous July
    # If we're in Jul-Dec, FY started this July
    if reference_date.month >= 7:
        current_fy_start_year = reference_date.year
    else:
        current_fy_start_year = reference_date.year - 1

    current_fy_start = date(current_fy_start_year, 7, 1)
    prior_fy_start = date(current_fy_start_year - 1, 7, 1)

    # FY number is the year the FY ends (e.g., FY26 ends June 30, 2026)
    current_fy_number = current_fy_start_year + 1
    prior_fy_number = current_fy_start_year

    # Short labels (e.g., "FY26", "FY25")
    current_fy_short = f"FY{current_fy_number % 100:02d}"
    prior_fy_short = f"FY{prior_fy_number % 100:02d}"

    return {
        'current_fy_start': current_fy_start,
        'prior_fy_start': prior_fy_start,
        'current_fy_number': current_fy_number,
        'prior_fy_number': prior_fy_number,
        'current_fy_short': current_fy_short,
        'prior_fy_short': prior_fy_short
    }


def get_contact_metrics_comparison(debug: bool = False) -> dict:
    """Get contact metrics for current FY vs prior FY to date.

    Args:
        debug: If True, include debug info in return dict

    Returns:
        Dictionary with 'current_fy' and 'prior_fy' DataFrames plus labels
    """
    today = date.today()
    fy_info = get_fiscal_year_info(today)

    # Current fiscal year: FY start to today
    current_fy_start = fy_info['current_fy_start'].strftime("%Y-%m-%d")
    current_fy_end = today.strftime("%Y-%m-%d")

    # Prior fiscal year to same date: Prior FY start to same date last year
    prior_fy_start = fy_info['prior_fy_start'].strftime("%Y-%m-%d")
    prior_fy_end = today.replace(year=today.year - 1).strftime("%Y-%m-%d")

    debug_info = {}
    if debug:
        current_result = load_donorperfect_contacts(current_fy_start, current_fy_end, debug=True)
        prior_result = load_donorperfect_contacts(prior_fy_start, prior_fy_end, debug=True)
        current_df, current_debug = current_result
        prior_df, prior_debug = prior_result
        debug_info = {
            'current_fy_debug': current_debug,
            'prior_fy_debug': prior_debug
        }
    else:
        current_df = load_donorperfect_contacts(current_fy_start, current_fy_end)
        prior_df = load_donorperfect_contacts(prior_fy_start, prior_fy_end)

    current_fy_short = fy_info['current_fy_short']
    prior_fy_short = fy_info['prior_fy_short']

    result = {
        'current_fy': current_df,
        'prior_fy': prior_df,
        'current_fy_label': f"{current_fy_short} YTD ({current_fy_start} - {current_fy_end})",
        'prior_fy_label': f"{prior_fy_short} YTD ({prior_fy_start} - {prior_fy_end})",
        'current_fy_short': current_fy_short,
        'prior_fy_short': prior_fy_short
    }

    if debug:
        result['debug'] = debug_info

    return result


def summarize_contacts(df: pd.DataFrame) -> dict:
    """Summarize contact data by activity type.

    Args:
        df: DataFrame with contact records

    Returns:
        Dictionary with summary metrics
    """
    if df.empty:
        return {
            'total': 0,
            'by_type': {},
            'cc_by_status': {},
            'lt_by_mailing': {},
            'by_month': {}
        }

    # Normalize activity_code - treat blank/None as 'LT' (Letter)
    df = df.copy()
    df['activity_code'] = df['activity_code'].fillna('LT')
    df['activity_code'] = df['activity_code'].replace('', 'LT')

    # Contact type labels
    type_labels = {
        'CC': 'Constant Contact',
        'EO': 'Email Out',
        'RCPTSNT': 'Receipt Sent',
        'LT': 'Letter'
    }

    # Count by activity type
    by_type = df['activity_code'].value_counts().to_dict()

    # For CC contacts, group by em_campaign_status
    cc_df = df[df['activity_code'] == 'CC']
    cc_by_status = cc_df['em_campaign_status'].fillna('Unknown').value_counts().to_dict() if not cc_df.empty else {}

    # For LT contacts, group by mailing_code
    lt_df = df[df['activity_code'] == 'LT']
    lt_by_mailing = lt_df['mailing_code'].fillna('Unknown').value_counts().to_dict() if not lt_df.empty else {}

    # Monthly breakdown
    by_month = {}
    if 'contact_date' in df.columns and not df['contact_date'].isna().all():
        df['month'] = df['contact_date'].dt.to_period('M')
        by_month = df.groupby('month').size().to_dict()
        # Convert Period keys to strings for JSON serialization
        by_month = {str(k): v for k, v in by_month.items()}

    return {
        'total': len(df),
        'by_type': by_type,
        'type_labels': type_labels,
        'cc_by_status': cc_by_status,
        'lt_by_mailing': lt_by_mailing,
        'by_month': by_month
    }


def normalize_legacy_record(record: dict) -> dict:
    """Normalize a legacy record, keeping original field names for DataProcessor."""
    normalized = {}

    # Copy passthrough fields as-is (DataProcessor handles these natively)
    for field in LEGACY_PASSTHROUGH_FIELDS:
        if field in record:
            value = record[field]
            # Handle list values (Fusioo sometimes returns single values as lists)
            if isinstance(value, list) and len(value) == 1:
                value = value[0]
            normalized[field] = value

    # Map fields that need renaming
    for legacy_field, current_field in LEGACY_FIELD_MAP.items():
        if legacy_field in record:
            value = record[legacy_field]
            if isinstance(value, list) and len(value) == 1:
                value = value[0]
            normalized[current_field] = value

    # Keep the record ID for tracking
    if "_id" in record:
        normalized["_id"] = record["_id"]
    if "id" in record:
        normalized["id"] = record["id"]

    # Mark as legacy data for potential filtering
    normalized["_is_legacy"] = True

    return normalized


def combine_activity_data(current_records: list, legacy_records: list, cutoff_date: str = "2025-07-01") -> list:
    """Combine current and legacy activity records, avoiding duplicates.

    Args:
        current_records: Records from the current activity report table
        legacy_records: Records from the legacy (pre-July 2025) table
        cutoff_date: Date string (YYYY-MM-DD) to filter legacy data before this date

    Returns:
        Combined list of records with legacy data normalized to current format
    """
    from datetime import datetime

    combined = list(current_records)  # Start with current data
    cutoff = datetime.strptime(cutoff_date, "%Y-%m-%d")

    for record in legacy_records:
        # Normalize the legacy record to current format
        normalized = normalize_legacy_record(record)

        # Parse the date to filter only pre-cutoff data
        # After normalization, date is mapped to date_of_activity
        date_val = normalized.get("date_of_activity", "")
        if isinstance(date_val, str) and date_val:
            # Handle Fusioo date format (may include timestamp after |)
            date_str = date_val.split("|")[0] if "|" in date_val else date_val
            try:
                record_date = datetime.strptime(date_str, "%Y-%m-%d")
                # Only include legacy records before the cutoff date
                if record_date < cutoff:
                    combined.append(normalized)
            except ValueError:
                # If date parsing fails, skip this record
                continue

    return combined


def render_hero_header(processor: DataProcessor):
    """Render the hero header with key stats."""
    stats = processor.get_summary_stats()
    books = int(stats.get("totals", {}).get("_of_books_distributed", 0))
    children = int(stats.get("totals", {}).get("total_children", 0))
    parents = int(stats.get("totals", {}).get("parents_or_caregivers", 0))

    # Use Streamlit native components for reliable rendering
    st.markdown("""
    <style>
    .hero-box {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #f0fdf4 100%);
        border-radius: 16px;
        padding: 1.5rem 2rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
        border: 1px solid #e0e7ff;
        text-align: center;
    }
    .hero-title {
        color: #1e3a5f;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
    }
    .hero-subtitle {
        color: #64748b;
        font-size: 0.9rem;
        margin: 0.25rem 0 0 0;
    }
    .hero-date {
        color: #94a3b8;
        font-size: 0.85rem;
        margin: 0.75rem 0 0 0;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="hero-box">
        <div style="display: flex; align-items: center; justify-content: center; gap: 0.75rem;">
            <span style="font-size: 2rem;">📚</span>
            <div style="text-align: left;">
                <h1 class="hero-title">BookSpring Strategic Dashboard</h1>
                <p class="hero-subtitle">Tracking Progress Toward 2025-2030 Strategic Goals</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Use native Streamlit metrics for the stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📚 Books Distributed", f"{books:,}")
    with col2:
        st.metric("👶 Children Served", f"{children:,}")
    with col3:
        st.metric("👨‍👩‍👧 Parents/Caregivers", f"{parents:,}")

    st.markdown("<br><br>", unsafe_allow_html=True)


def render_print_snapshot(processor: DataProcessor, views_data: list, books_data: list, start_date: date, end_date: date):
    """Render the one-page print snapshot of all four goals."""
    stats = processor.get_summary_stats()
    books = int(stats.get("totals", {}).get("_of_books_distributed", 0))
    children = int(stats.get("totals", {}).get("total_children", 0))
    avg_books = books / children if children > 0 else 0
    parents = int(stats.get("totals", {}).get("parents_or_caregivers", 0))

    # Calculate Goal 1 progress
    target_books_per_child = 4.0
    goal1_progress = min((avg_books / target_books_per_child) * 100, 100)

    # Calculate Goal 2 metrics (views)
    total_views = 0
    digital_views = 0
    newsletter_views = 0
    if views_data:
        df = pd.DataFrame(views_data)
        for col in df.columns:
            if df[col].apply(lambda x: isinstance(x, list)).any():
                df[col] = df[col].apply(lambda x: x[0] if isinstance(x, list) and len(x) == 1 else x)

        if "date" in df.columns:
            df["_parsed_date"] = df["date"].apply(lambda x: x.split("|")[0] if isinstance(x, str) and "|" in x else x)
            df["_parsed_date"] = pd.to_datetime(df["_parsed_date"], errors='coerce')
            mask = (df["_parsed_date"] >= pd.Timestamp(start_date)) & (df["_parsed_date"] <= pd.Timestamp(end_date))
            df = df[mask]

        if "total_digital_views" in df.columns:
            df["total_digital_views"] = pd.to_numeric(df["total_digital_views"], errors='coerce').fillna(0)
            digital_views = int(df["total_digital_views"].sum())
        if "total_newsletter_views" in df.columns:
            df["total_newsletter_views"] = pd.to_numeric(df["total_newsletter_views"], errors='coerce').fillna(0)
            newsletter_views = int(df["total_newsletter_views"].sum())
        total_views = digital_views + newsletter_views

    target_views = 1_500_000
    goal2_progress = min((total_views / target_views) * 100, 100)

    # Calculate Goal 3 metrics (original books)
    total_books_count = 0
    completed_books = 0
    in_progress_books = 0
    bilingual_books = 0
    if books_data:
        bdf = pd.DataFrame(books_data)
        for col in bdf.columns:
            if bdf[col].apply(lambda x: isinstance(x, list)).any():
                bdf[col] = bdf[col].apply(lambda x: x[0] if isinstance(x, list) and len(x) == 1 else x)
        total_books_count = len(bdf)
        if "status" in bdf.columns:
            completed_books = len(bdf[bdf["status"].str.contains("Complete|Published", case=False, na=False)])
            in_progress_books = total_books_count - completed_books
        if "language" in bdf.columns:
            bilingual_books = len(bdf[bdf["language"].str.contains("Spanish|Bi-lingual", case=False, na=False)])

    # Goal 4 metrics (sustainability)
    target_annual_books = 600_000
    goal4_progress = min((books / target_annual_books) * 100, 100)
    goal3_progress = (completed_books / max(total_books_count, 1)) * 100

    # CSS for print snapshot
    st.markdown("""
    <style>
    .snapshot-container {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
        border: 1px solid #e2e8f0;
    }
    .snapshot-header {
        text-align: center;
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid #e2e8f0;
    }
    .snapshot-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #0f2942;
        margin: 0;
    }
    .snapshot-date {
        color: #64748b;
        font-size: 0.9rem;
        margin: 0.5rem 0 0 0;
    }
    .snapshot-summary {
        color: #475569;
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }
    .goals-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1rem;
    }
    .goal-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid #e2e8f0;
        position: relative;
    }
    .goal-card-g1 { border-top: 4px solid #667eea; }
    .goal-card-g2 { border-top: 4px solid #f5576c; }
    .goal-card-g3 { border-top: 4px solid #4facfe; }
    .goal-card-g4 { border-top: 4px solid #43e97b; }
    .goal-title {
        font-size: 0.9rem;
        font-weight: 700;
        color: #0f2942;
        margin-bottom: 0.75rem;
    }
    .metrics-row {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
    }
    .metric-box {
        flex: 1;
        min-width: 60px;
        text-align: center;
        padding: 0.5rem;
        background: #f8fafc;
        border-radius: 8px;
    }
    .metric-val {
        font-size: 1rem;
        font-weight: 700;
        color: #1a202c;
    }
    .metric-lbl {
        font-size: 0.65rem;
        color: #718096;
        margin-top: 0.2rem;
    }
    .progress-wrap {
        margin-top: 0.75rem;
    }
    .progress-bg {
        height: 6px;
        background: #e2e8f0;
        border-radius: 100px;
        overflow: hidden;
    }
    .progress-fill-g1 { background: linear-gradient(90deg, #667eea, #764ba2); }
    .progress-fill-g2 { background: linear-gradient(90deg, #f093fb, #f5576c); }
    .progress-fill-g3 { background: linear-gradient(90deg, #4facfe, #00f2fe); }
    .progress-fill-g4 { background: linear-gradient(90deg, #43e97b, #38f9d7); }
    .progress-txt {
        font-size: 0.7rem;
        color: #718096;
        text-align: right;
        margin-top: 0.25rem;
    }
    .snapshot-footer {
        text-align: center;
        color: #94a3b8;
        font-size: 0.75rem;
        margin-top: 1rem;
        padding-top: 0.75rem;
        border-top: 1px solid #e2e8f0;
    }
    </style>
    """, unsafe_allow_html=True)

    # Build HTML with simple string formatting (no f-string style variables)
    date_str = f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
    today_str = date.today().strftime('%B %d, %Y')

    html = f'''
    <div class="snapshot-container">
        <div class="snapshot-header">
            <h2 class="snapshot-title">📚 BookSpring Strategic Goals Snapshot</h2>
            <p class="snapshot-date">{date_str}</p>
            <p class="snapshot-summary">
                <strong>{books:,}</strong> Books &nbsp;|&nbsp;
                <strong>{children:,}</strong> Children &nbsp;|&nbsp;
                <strong>{avg_books:.2f}</strong> Books/Child
            </p>
        </div>

        <div class="goals-grid">
            <div class="goal-card goal-card-g1">
                <div class="goal-title">🎯 Goal 1: Strengthen Impact</div>
                <div class="metrics-row">
                    <div class="metric-box"><div class="metric-val">{avg_books:.2f}</div><div class="metric-lbl">Books/Child</div></div>
                    <div class="metric-box"><div class="metric-val">4.0</div><div class="metric-lbl">Target</div></div>
                    <div class="metric-box"><div class="metric-val">{books:,}</div><div class="metric-lbl">Books</div></div>
                    <div class="metric-box"><div class="metric-val">{children:,}</div><div class="metric-lbl">Children</div></div>
                </div>
                <div class="progress-wrap">
                    <div class="progress-bg"><div class="progress-fill-g1" style="height:100%;width:{goal1_progress:.0f}%;border-radius:100px;"></div></div>
                    <div class="progress-txt">{goal1_progress:.1f}% toward target</div>
                </div>
            </div>

            <div class="goal-card goal-card-g2">
                <div class="goal-title">💡 Goal 2: Inspire Engagement</div>
                <div class="metrics-row">
                    <div class="metric-box"><div class="metric-val">{total_views:,}</div><div class="metric-lbl">Total Views</div></div>
                    <div class="metric-box"><div class="metric-val">{digital_views:,}</div><div class="metric-lbl">Digital</div></div>
                    <div class="metric-box"><div class="metric-val">{newsletter_views:,}</div><div class="metric-lbl">Newsletter</div></div>
                    <div class="metric-box"><div class="metric-val">1.5M</div><div class="metric-lbl">Target</div></div>
                </div>
                <div class="progress-wrap">
                    <div class="progress-bg"><div class="progress-fill-g2" style="height:100%;width:{goal2_progress:.0f}%;border-radius:100px;"></div></div>
                    <div class="progress-txt">{goal2_progress:.1f}% toward target</div>
                </div>
            </div>

            <div class="goal-card goal-card-g3">
                <div class="goal-title">🚀 Goal 3: Advance Innovation</div>
                <div class="metrics-row">
                    <div class="metric-box"><div class="metric-val">{total_books_count}</div><div class="metric-lbl">Total</div></div>
                    <div class="metric-box"><div class="metric-val">{completed_books}</div><div class="metric-lbl">Complete</div></div>
                    <div class="metric-box"><div class="metric-val">{in_progress_books}</div><div class="metric-lbl">In Progress</div></div>
                    <div class="metric-box"><div class="metric-val">{bilingual_books}</div><div class="metric-lbl">Bilingual</div></div>
                </div>
                <div class="progress-wrap">
                    <div class="progress-bg"><div class="progress-fill-g3" style="height:100%;width:{goal3_progress:.0f}%;border-radius:100px;"></div></div>
                    <div class="progress-txt">{completed_books}/{total_books_count} completed</div>
                </div>
            </div>

            <div class="goal-card goal-card-g4">
                <div class="goal-title">🌱 Goal 4: Optimize Sustainability</div>
                <div class="metrics-row">
                    <div class="metric-box"><div class="metric-val">{books:,}</div><div class="metric-lbl">Distributed</div></div>
                    <div class="metric-box"><div class="metric-val">600K</div><div class="metric-lbl">Target/Yr</div></div>
                    <div class="metric-box"><div class="metric-val">{parents:,}</div><div class="metric-lbl">Caregivers</div></div>
                    <div class="metric-box"><div class="metric-val">$3M</div><div class="metric-lbl">Budget</div></div>
                </div>
                <div class="progress-wrap">
                    <div class="progress-bg"><div class="progress-fill-g4" style="height:100%;width:{goal4_progress:.0f}%;border-radius:100px;"></div></div>
                    <div class="progress-txt">{goal4_progress:.1f}% toward target</div>
                </div>
            </div>
        </div>

        <div class="snapshot-footer">Generated on {today_str} • BookSpring Strategic Dashboard</div>
    </div>
    '''

    st.markdown(html, unsafe_allow_html=True)


def render_goal1_strengthen_impact(processor: DataProcessor, time_unit: str):
    """Render Goal 1: Strengthen Impact section."""
    st.markdown("""
    <div class="section-header">
        <div class="section-icon goal1">🎯</div>
        <div class="section-title-group">
            <h2 class="section-title">Goal 1: Strengthen Impact</h2>
            <p class="section-subtitle">Target: 4 books/child/year | Daily read-aloud 25%→75% | Home libraries 26%→50%</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Calculate weighted average
    total_books = processor.df["_of_books_distributed"].sum() if "_of_books_distributed" in processor.df.columns else 0
    total_children = processor.df["total_children"].sum() if "total_children" in processor.df.columns else 0
    avg_overall = total_books / total_children if total_children > 0 else 0
    target = 4.0
    progress = min(avg_overall / target * 100, 100)

    # Metrics row - show red when below target
    col1, col2 = st.columns(2)
    with col1:
        delta_val = avg_overall - target
        # Show red when below target (normal = green up/red down, off = no color)
        if delta_val >= 0:
            st.metric("Avg Books/Child (in date range)", f"{avg_overall:.2f}", delta=f"{delta_val:+.2f} vs target")
        else:
            # Custom HTML for red indicator when below target
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #fff 0%, #fef2f2 100%); border: 1px solid #fecaca; border-radius: 10px; padding: 1rem;">
                <p style="color: #718096; font-size: 0.85rem; margin: 0 0 0.25rem 0;">Avg Books/Child (in date range)</p>
                <p style="font-size: 1.75rem; font-weight: 700; color: #1a202c; margin: 0;">{avg_overall:.2f}</p>
                <p style="color: #dc2626; font-size: 0.85rem; margin: 0.25rem 0 0 0; font-weight: 600;">▼ {abs(delta_val):.2f} below target</p>
            </div>
            """, unsafe_allow_html=True)
    with col2:
        st.metric("Annual Target (by 2030)", "4.00 books/child")

    # Custom progress bar
    st.markdown(f"""
    <div class="progress-container">
        <div class="progress-bar goal1" style="width: {progress}%"></div>
    </div>
    <div class="progress-label">
        <span>Progress toward 4 books/child/year</span>
        <span><strong>{progress:.1f}%</strong></span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Trend charts
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Overall Trend")
        if "avg_books_per_child" in processor.df.columns:
            trend_df = processor.aggregate_by_time(time_unit, ["avg_books_per_child"])
            if not trend_df.empty:
                fig = px.area(
                    trend_df,
                    x="period",
                    y="avg_books_per_child",
                    color_discrete_sequence=["#667eea"]
                )
                fig.add_hline(y=4.0, line_dash="dash", line_color="#22c55e",
                             annotation_text="Target: 4.0", annotation_position="top right",
                             annotation_font_color="#22c55e")
                fig = style_plotly_chart(fig, height=280)
                fig.update_traces(fill='tozeroy', fillcolor='rgba(102, 126, 234, 0.2)')
                # Set Y-axis range from 0 to max of 5 or data max + 0.5 for granularity
                y_max = max(5, trend_df["avg_books_per_child"].max() + 0.5)
                fig.update_layout(
                    yaxis_title="Avg Books/Child",
                    xaxis_title="",
                    showlegend=False,
                    yaxis=dict(range=[0, y_max], dtick=0.5, gridcolor='#e5e7eb')
                )
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### By Age Group")
        age_metrics = ["books_per_child_0_2", "books_per_child_3_5",
                       "books_per_child_6_8", "books_per_child_9_12", "books_per_child_teens"]
        available_age = [m for m in age_metrics if m in processor.df.columns]

        if available_age:
            trend_df = processor.aggregate_by_time(time_unit, available_age)
            if not trend_df.empty:
                rename_map = {c: get_friendly_name(c) for c in trend_df.columns if c != "period"}
                trend_df = trend_df.rename(columns=rename_map)

                # Better color palette for age groups
                age_colors = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444"]
                fig = px.line(
                    trend_df,
                    x="period",
                    y=[get_friendly_name(m) for m in available_age],
                    markers=True,
                    color_discrete_sequence=age_colors
                )
                fig.add_hline(y=4.0, line_dash="dash", line_color="#22c55e",
                             annotation_text="Target", annotation_font_color="#22c55e")
                fig = style_plotly_chart(fig, height=280)
                # Granular Y-axis with 0.5 increments
                numeric_cols = [get_friendly_name(m) for m in available_age]
                y_max = max(5, trend_df[numeric_cols].max().max() + 0.5)
                fig.update_layout(
                    yaxis_title="Books/Child",
                    xaxis_title="",
                    yaxis=dict(range=[0, y_max], dtick=0.5, gridcolor='#e5e7eb')
                )
                st.plotly_chart(fig, use_container_width=True)


def render_goal2_inspire_engagement(views_data: list, time_unit: str, start_date: date, end_date: date, enrollment_count: int = 0, book_bank_children: int = 0, inperson_events: int = 0, activity_records: list = None, partners_data: list = None):
    """Render Goal 2: Inspire Engagement with Content Views."""
    st.markdown("""
    <div class="section-header">
        <div class="section-icon goal2">💡</div>
        <div class="section-title-group">
            <h2 class="section-title">Goal 2: Inspire Engagement</h2>
            <p class="section-subtitle">Target: 25K home delivery | 55K book bank model | 1.5M digital views annually</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Calculate recurring partners from activity records (filtered by date range)
    recurring_partners = []
    recurring_count = 0
    partner_names = {}
    if activity_records and partners_data:
        # Build partner ID to name mapping
        for partner in partners_data:
            pid = partner.get('id', '')
            site_name = partner.get('site_name', '')
            if isinstance(site_name, list):
                site_name = site_name[0] if site_name else ''

            # For "Various" partner, use main_organization_from_list instead
            if site_name and site_name.lower() == 'various':
                main_org = partner.get('main_organization_from_list', '')
                if isinstance(main_org, list):
                    main_org = main_org[0] if main_org else ''
                if main_org:
                    site_name = main_org

            if pid and site_name:
                partner_names[pid] = site_name

        # Filter activity records by date range and count partner occurrences
        partner_counts = Counter()
        for record in activity_records:
            # Check date range
            record_date = record.get('date_of_activity') or record.get('date')
            if record_date:
                if isinstance(record_date, str):
                    try:
                        record_dt = pd.to_datetime(record_date)
                        if not (pd.Timestamp(start_date) <= record_dt <= pd.Timestamp(end_date)):
                            continue
                    except:
                        continue
                else:
                    continue

            partner_id = record.get('partners_testing', '')
            if isinstance(partner_id, list):
                partner_id = partner_id[0] if partner_id else ''
            if partner_id:
                partner_counts[partner_id] += 1

        # Get recurring partners (appeared more than once)
        recurring_partners = [(pid, count) for pid, count in partner_counts.most_common() if count > 1]
        recurring_count = len(recurring_partners)

    # Calculate partners for in-person events (same date range filter)
    inperson_event_partners = set()
    if activity_records and partner_names:
        for record in activity_records:
            # Check date range
            record_date = record.get('date_of_activity') or record.get('date')
            if record_date:
                if isinstance(record_date, str):
                    try:
                        record_dt = pd.to_datetime(record_date)
                        if not (pd.Timestamp(start_date) <= record_dt <= pd.Timestamp(end_date)):
                            continue
                    except:
                        continue
                else:
                    continue

            # Check if it's an in-person event
            activity_type = record.get('activity_type', '')
            if isinstance(activity_type, list):
                activity_type = ', '.join(str(x) for x in activity_type)
            if not ("Literacy Materials Distribution" in str(activity_type) or "Family Literacy Activity" in str(activity_type)):
                continue

            # Get partner
            partner_id = record.get('partners_testing', '')
            if isinstance(partner_id, list):
                partner_id = partner_id[0] if partner_id else ''
            if partner_id and partner_id in partner_names:
                inperson_event_partners.add(partner_names[partner_id])

    # Build in-person event partners HTML
    inperson_partners_html = ""
    if inperson_event_partners:
        partner_items = [f"<span style='background: #fce7f3; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; color: #9d174d; white-space: nowrap;'>{name}</span>" for name in sorted(inperson_event_partners)]
        inperson_partners_html = " ".join(partner_items)

    # In-Person Events box
    st.markdown(f"""
    <div style="display: flex; align-items: flex-start; gap: 1.5rem; margin-bottom: 1rem; padding: 1.25rem 1.5rem; background: linear-gradient(135deg, #fef2f8 0%, #fce7f3 100%); border: 1px solid #fbcfe8; border-radius: 16px;">
        <div style="width: 80px; height: 80px; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 14px rgba(245, 87, 108, 0.4); flex-shrink: 0;">
            <span style="font-size: 1.75rem; font-weight: 800; color: white;">{inperson_events:,}</span>
        </div>
        <div style="flex: 1; min-width: 0;">
            <p style="font-size: 1.1rem; font-weight: 700; color: #1a202c; margin: 0;">BookSpring In-Person Events</p>
            <p style="font-size: 0.85rem; color: #6b7280; margin: 0.25rem 0 0 0;">(in date range)</p>
            <p style="font-size: 0.75rem; color: #9ca3af; margin: 0.5rem 0 0 0; font-style: italic;">Includes: Literacy Materials Distribution, Family Literacy Activity</p>
            <div style="margin-top: 0.75rem; display: flex; flex-wrap: wrap; gap: 0.4rem;">{inperson_partners_html if inperson_partners_html else ''}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Recurring Partners box (below In-Person Events) - show ALL recurring partners
    all_partners_html = ""
    if recurring_partners:
        partner_items = []
        for pid, count in recurring_partners:
            name = partner_names.get(pid, pid[:12] + '...')
            partner_items.append(f"<span style='background: #d1fae5; padding: 0.25rem 0.6rem; border-radius: 6px; font-size: 0.85rem; color: #065f46; white-space: nowrap;'>{name} <strong>({count})</strong></span>")
        all_partners_html = " ".join(partner_items)

    st.markdown(f"""
    <div style="display: flex; align-items: flex-start; gap: 1.5rem; margin-bottom: 1.5rem; padding: 1.5rem 1.75rem; background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); border: 1px solid #bbf7d0; border-radius: 16px; min-height: 140px;">
        <div style="width: 90px; height: 90px; background: linear-gradient(135deg, #4ade80 0%, #22c55e 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 14px rgba(34, 197, 94, 0.4); flex-shrink: 0;">
            <span style="font-size: 2rem; font-weight: 800; color: white;">{recurring_count:,}</span>
        </div>
        <div style="flex: 1; min-width: 0;">
            <p style="font-size: 1.15rem; font-weight: 700; color: #1a202c; margin: 0;">Recurring Partners</p>
            <p style="font-size: 0.85rem; color: #6b7280; margin: 0.25rem 0 0 0;">(2+ activities in date range)</p>
            <div style="margin-top: 0.85rem; display: flex; flex-wrap: wrap; gap: 0.5rem; line-height: 1.8;">{all_partners_html if all_partners_html else '<span style="font-size: 0.85rem; color: #9ca3af;">No recurring partners in date range</span>'}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Home Delivery Section
    st.markdown("##### 🏠 B3 In-Home Delivery Program")
    home_target = 25_000
    home_progress = min(enrollment_count / home_target * 100, 100) if home_target > 0 else 0

    col1, col2 = st.columns(2)
    with col1:
        delta_val = enrollment_count - home_target
        if delta_val >= 0:
            st.metric("B3 In-home delivery enrollments (all time)", f"{enrollment_count:,}", delta=f"+{delta_val:,} vs target")
        else:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #fff 0%, #fef2f2 100%); border: 1px solid #fecaca; border-radius: 10px; padding: 1rem;">
                <p style="color: #718096; font-size: 0.85rem; margin: 0 0 0.25rem 0;">B3 In-home delivery enrollments (all time)</p>
                <p style="font-size: 1.75rem; font-weight: 700; color: #1a202c; margin: 0;">{enrollment_count:,}</p>
                <p style="color: #dc2626; font-size: 0.85rem; margin: 0.25rem 0 0 0; font-weight: 600;">▼ {abs(delta_val):,} below target</p>
            </div>
            """, unsafe_allow_html=True)
    with col2:
        st.metric("2030 Target", "25K families")

    st.markdown(f"""
    <div class="progress-container">
        <div class="progress-bar goal2" style="width: {home_progress}%"></div>
    </div>
    <div class="progress-label">
        <span>Progress toward 25K home delivery enrollments</span>
        <span><strong>{home_progress:.1f}%</strong></span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Book Bank Section
    st.markdown("##### 📚 Book Bank Model (Open Book Distribution)")
    book_bank_target = 55_000
    book_bank_progress = min(book_bank_children / book_bank_target * 100, 100) if book_bank_target > 0 else 0

    col1, col2 = st.columns(2)
    with col1:
        delta_val = book_bank_children - book_bank_target
        if delta_val >= 0:
            st.metric("Children Served (in date range)", f"{book_bank_children:,}", delta=f"+{delta_val:,} vs target")
        else:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #fff 0%, #fef2f2 100%); border: 1px solid #fecaca; border-radius: 10px; padding: 1rem;">
                <p style="color: #718096; font-size: 0.85rem; margin: 0 0 0.25rem 0;">Children Served (in date range)</p>
                <p style="font-size: 1.75rem; font-weight: 700; color: #1a202c; margin: 0;">{book_bank_children:,}</p>
                <p style="color: #dc2626; font-size: 0.85rem; margin: 0.25rem 0 0 0; font-weight: 600;">▼ {abs(delta_val):,} below target</p>
            </div>
            """, unsafe_allow_html=True)
    with col2:
        st.metric("2030 Target", "55K children")

    st.markdown(f"""
    <div class="progress-container">
        <div class="progress-bar goal2" style="width: {book_bank_progress}%"></div>
    </div>
    <div class="progress-label">
        <span>Progress toward 55K partner program children</span>
        <span><strong>{book_bank_progress:.1f}%</strong></span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 📱 Digital Engagement")

    if not views_data:
        st.warning("No Content Views data available")
        return

    df = pd.DataFrame(views_data)

    # Convert list columns
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, list)).any():
            df[col] = df[col].apply(
                lambda x: x[0] if isinstance(x, list) and len(x) == 1
                else ", ".join(str(i) for i in x) if isinstance(x, list)
                else x
            )

    # Parse and filter by date
    if "date" in df.columns:
        df["_parsed_date"] = df["date"].apply(
            lambda x: x.split("|")[0] if isinstance(x, str) and "|" in x else x
        )
        df["_parsed_date"] = pd.to_datetime(df["_parsed_date"], errors='coerce')
        mask = (df["_parsed_date"] >= pd.Timestamp(start_date)) & (df["_parsed_date"] <= pd.Timestamp(end_date))
        df = df[mask].copy()

    # Calculate views
    digital_views = 0
    newsletter_views = 0
    if "total_digital_views" in df.columns:
        df["total_digital_views"] = pd.to_numeric(df["total_digital_views"], errors='coerce').fillna(0)
        digital_views = df["total_digital_views"].sum()
    if "total_newsletter_views" in df.columns:
        df["total_newsletter_views"] = pd.to_numeric(df["total_newsletter_views"], errors='coerce').fillna(0)
        newsletter_views = df["total_newsletter_views"].sum()

    total_views = digital_views + newsletter_views
    target_views = 1_500_000
    progress = min(total_views / target_views * 100, 100) if target_views > 0 else 0

    # Metrics - show red when below target
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        views_delta = total_views - target_views
        if views_delta >= 0:
            st.metric("Total Views", f"{int(total_views):,}", delta=f"+{int(views_delta):,} vs target")
        else:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #fff 0%, #fef2f2 100%); border: 1px solid #fecaca; border-radius: 10px; padding: 1rem;">
                <p style="color: #718096; font-size: 0.85rem; margin: 0 0 0.25rem 0;">Total Views</p>
                <p style="font-size: 1.75rem; font-weight: 700; color: #1a202c; margin: 0;">{int(total_views):,}</p>
                <p style="color: #dc2626; font-size: 0.85rem; margin: 0.25rem 0 0 0; font-weight: 600;">▼ {abs(int(views_delta)):,} below target</p>
            </div>
            """, unsafe_allow_html=True)
    with col2:
        st.metric("Digital Views", f"{int(digital_views):,}")
    with col3:
        st.metric("Newsletter Views", f"{int(newsletter_views):,}")
    with col4:
        st.metric("Annual Target (by 2030)", "1.5M views/year")

    # Progress bar
    st.markdown(f"""
    <div class="progress-container">
        <div class="progress-bar goal2" style="width: {progress}%"></div>
    </div>
    <div class="progress-label">
        <span>Progress toward 1.5M views/year</span>
        <span><strong>{progress:.1f}%</strong></span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts row
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Views Trend")
        if "_parsed_date" in df.columns:
            view_cols = [c for c in ["total_digital_views", "total_newsletter_views"] if c in df.columns]
            if view_cols:
                freq_map = {"day": "D", "week": "W", "month": "ME", "quarter": "QE", "year": "YE"}
                freq = freq_map.get(time_unit, "ME")

                valid_df = df[df["_parsed_date"].notna()]
                if not valid_df.empty:
                    trend_df = valid_df.groupby(pd.Grouper(key="_parsed_date", freq=freq))[view_cols].sum().reset_index()
                    trend_df = trend_df.rename(columns={
                        "_parsed_date": "Period",
                        "total_digital_views": "Digital",
                        "total_newsletter_views": "Newsletter"
                    })

                    # Consistent colors: Digital=blue, Newsletter=green
                    view_colors = {"Digital": "#3b82f6", "Newsletter": "#10b981"}
                    fig = px.area(
                        trend_df,
                        x="Period",
                        y=[c for c in ["Digital", "Newsletter"] if c in trend_df.columns],
                        color_discrete_map=view_colors
                    )
                    fig = style_plotly_chart(fig, height=280)
                    fig.update_traces(stackgroup='one')
                    fig.update_layout(
                        yaxis_title="Views",
                        xaxis_title="",
                        yaxis=dict(gridcolor='#e5e7eb')
                    )
                    st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### View Distribution")
        if total_views > 0:
            pie_data = pd.DataFrame({
                "Type": ["Digital Views", "Newsletter Views"],
                "Count": [digital_views, newsletter_views]
            })
            # Consistent colors: Digital=blue, Newsletter=green (matching area chart)
            fig = px.pie(
                pie_data,
                values="Count",
                names="Type",
                hole=0.5,
                color="Type",
                color_discrete_map={"Digital Views": "#3b82f6", "Newsletter Views": "#10b981"}
            )
            fig = style_plotly_chart(fig, height=280)
            fig.update_traces(
                textposition='outside',
                textinfo='percent+label',
                textfont_size=12,
                textfont_color='#374151',
                marker=dict(line=dict(color='#ffffff', width=2))
            )
            st.plotly_chart(fig, use_container_width=True)


def render_goal3_advance_innovation(books_data: list):
    """Render Goal 3: Advance Innovation with Original Books."""
    st.markdown("""
    <div class="section-header">
        <div class="section-icon goal3">🚀</div>
        <div class="section-title-group">
            <h2 class="section-title">Goal 3: Advance Innovation</h2>
            <p class="section-subtitle">Target: Grow digital library with high-quality, Texas-relevant original content</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not books_data:
        st.warning("No Original Books data available")
        return

    df = pd.DataFrame(books_data)

    # Convert list columns
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, list)).any():
            df[col] = df[col].apply(
                lambda x: x[0] if isinstance(x, list) and len(x) == 1
                else ", ".join(str(i) for i in x) if isinstance(x, list)
                else x
            )

    # Metrics
    total = len(df)
    completed = len(df[df["status"].str.contains("Complete|Published", case=False, na=False)]) if "status" in df.columns else 0
    in_progress = total - completed
    bilingual = len(df[df["language"].str.contains("Spanish|Bi-lingual", case=False, na=False)]) if "language" in df.columns else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Books", total)
    with col2:
        st.metric("Completed", completed)
    with col3:
        st.metric("In Progress", in_progress)
    with col4:
        st.metric("Spanish/Bilingual", bilingual)

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Production Pipeline")
        if "status" in df.columns:
            status_counts = df["status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]

            fig = px.bar(
                status_counts,
                x="Count",
                y="Status",
                orientation='h',
                color="Count",
                color_continuous_scale=[[0, "#a0e9ff"], [1, "#4facfe"]]
            )
            fig = style_plotly_chart(fig, height=300)
            fig.update_layout(
                showlegend=False,
                coloraxis_showscale=False,
                yaxis={'categoryorder':'total ascending'}
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Books by Target Age")
        if "sub_type" in df.columns:
            age_counts = df["sub_type"].value_counts().reset_index()
            age_counts.columns = ["Age Group", "Count"]

            # Clean, distinct, readable colors
            pie_colors = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"]
            fig = px.pie(
                age_counts,
                names="Age Group",
                values="Count",
                hole=0.4,
                color_discrete_sequence=pie_colors
            )
            fig = style_plotly_chart(fig, height=300)
            fig.update_traces(
                textposition='inside',
                textinfo='value+percent',
                textfont_size=11,
                textfont_color='#ffffff',
                marker=dict(line=dict(color='#ffffff', width=2))
            )
            st.plotly_chart(fig, use_container_width=True)


def render_goal4_sustainability(processor: DataProcessor, financial_df: pd.DataFrame = None):
    """Render Goal 4: Optimize Sustainability."""
    st.markdown("""
    <div class="section-header">
        <div class="section-icon goal4">🌱</div>
        <div class="section-title-group">
            <h2 class="section-title">Goal 4: Optimize Sustainability</h2>
            <p class="section-subtitle">Target: Diversified funding to $3M annually | 600K books distributed by 2030</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    stats = processor.get_summary_stats()
    books = int(stats.get("totals", {}).get("_of_books_distributed", 0))
    target = 600_000
    progress = min((books / target) * 100, 100)

    # Get grants data from financial data
    grants_received = 0
    grants_goal = 0
    if financial_df is not None and not financial_df.empty:
        if 'date' in financial_df.columns:
            latest = financial_df.sort_values('date', ascending=False).iloc[0] if len(financial_df) > 0 else {}
        else:
            latest = financial_df.iloc[0] if len(financial_df) > 0 else {}
        grants_received = float(latest.get('grants_received', 0) or 0)
        grants_goal = float(latest.get('grants_goal', 0) or 0)

    grants_pct_achieved = (grants_received / grants_goal * 100) if grants_goal > 0 else 0

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="placeholder-card">
            <h4>📦 Distribution Capacity</h4>
            <p>Track progress toward 600K annual books:</p>
            <ul>
                <li>Home delivery channel</li>
                <li>Partner distribution</li>
                <li>Book bank model</li>
                <li>Geographic expansion</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="placeholder-card">
            <h4>📈 Operational Efficiency</h4>
            <p>Key capacity indicators:</p>
            <ul>
                <li>Cost per book distributed</li>
                <li>Partner organization growth</li>
                <li>Staff productivity</li>
                <li>Inventory management</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    # Book distribution progress bar
    st.markdown(f"""
    <div style="margin-top: 1rem;">
        <div class="progress-container">
            <div class="progress-bar goal4" style="width: {progress}%"></div>
        </div>
        <div class="progress-label">
            <span>{books:,} books distributed</span>
            <span><strong>{progress:.1f}%</strong> of 600K target</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Grants progress
    if grants_goal > 0:
        grants_status = "🟢" if grants_pct_achieved >= 90 else "🟡" if grants_pct_achieved >= 70 else "🔴"
        st.markdown(f"""
        <div style="margin-top: 1rem;">
            <div class="progress-container">
                <div class="progress-bar" style="width: {min(grants_pct_achieved, 100)}%; background: linear-gradient(90deg, #fa709a, #fee140);"></div>
            </div>
            <div class="progress-label">
                <span>Grants Progress {grants_status} ${grants_received:,.0f} of ${grants_goal:,.0f}</span>
                <span><strong>{grants_pct_achieved:.1f}%</strong></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # === Donor Contacts Year-over-Year Comparison ===
    st.markdown("---")
    st.markdown("##### 📬 Donor Contacts - Year over Year Comparison")

    try:
        contact_data = get_contact_metrics_comparison(debug=True)
        current_summary = summarize_contacts(contact_data['current_fy'])
        prior_summary = summarize_contacts(contact_data['prior_fy'])

        # Dynamic FY labels
        current_fy = contact_data['current_fy_short']
        prior_fy = contact_data['prior_fy_short']
        current_col = f"{current_fy} YTD"
        prior_col = f"{prior_fy} YTD"

        # Debug info expander
        if 'debug' in contact_data:
            with st.expander("🔧 API Debug Info"):
                debug = contact_data['debug']
                if 'current_fy_debug' in debug:
                    st.markdown(f"**{current_fy} Query:**")
                    st.code(debug['current_fy_debug'].get('query', 'N/A'))
                    st.markdown(f"**{current_fy} URL (password masked):**")
                    st.code(debug['current_fy_debug'].get('url', 'N/A'))
                    st.markdown(f"**{current_fy} Response Status:** {debug['current_fy_debug'].get('status_code', 'N/A')}")
                    st.markdown(f"**{current_fy} Records Found:** {debug['current_fy_debug'].get('records_found', 'N/A')}")
                    if 'error' in debug['current_fy_debug']:
                        st.error(f"Error: {debug['current_fy_debug']['error']}")
                    st.markdown(f"**{current_fy} Response Preview:**")
                    st.code(debug['current_fy_debug'].get('response_preview', 'N/A'))

                if 'prior_fy_debug' in debug:
                    st.markdown("---")
                    st.markdown(f"**{prior_fy} Query:**")
                    st.code(debug['prior_fy_debug'].get('query', 'N/A'))
                    st.markdown(f"**{prior_fy} Records Found:** {debug['prior_fy_debug'].get('records_found', 'N/A')}")
                    if 'error' in debug['prior_fy_debug']:
                        st.error(f"Error: {debug['prior_fy_debug']['error']}")

        # Type labels for display
        type_labels = {
            'CC': 'Constant Contact',
            'EO': 'Email Out',
            'RCPTSNT': 'Receipt Sent',
            'LT': 'Letter'
        }

        # Build comparison dataframe for main contact types
        contact_types = ['CC', 'EO', 'RCPTSNT', 'LT']
        comparison_data = []
        for ct in contact_types:
            current_count = current_summary['by_type'].get(ct, 0)
            prior_count = prior_summary['by_type'].get(ct, 0)
            change = current_count - prior_count
            pct_change = ((current_count - prior_count) / prior_count * 100) if prior_count > 0 else (100 if current_count > 0 else 0)
            comparison_data.append({
                'Contact Type': type_labels.get(ct, ct),
                current_col: current_count,
                prior_col: prior_count,
                'Change': change,
                '% Change': pct_change
            })

        comparison_df = pd.DataFrame(comparison_data)

        # Add totals row
        totals_row = pd.DataFrame([{
            'Contact Type': 'TOTAL',
            current_col: current_summary['total'],
            prior_col: prior_summary['total'],
            'Change': current_summary['total'] - prior_summary['total'],
            '% Change': ((current_summary['total'] - prior_summary['total']) / prior_summary['total'] * 100) if prior_summary['total'] > 0 else 0
        }])
        comparison_df = pd.concat([comparison_df, totals_row], ignore_index=True)

        # Display main comparison table with visual bar chart
        col1, col2 = st.columns([2, 3])

        with col1:
            st.markdown("**Contact Summary by Type**")

            # Style the dataframe
            def style_change(val):
                if isinstance(val, (int, float)):
                    if val > 0:
                        return 'color: #38a169; font-weight: bold;'
                    elif val < 0:
                        return 'color: #e53e3e; font-weight: bold;'
                return ''

            styled_df = comparison_df.style.format({
                current_col: '{:,.0f}',
                prior_col: '{:,.0f}',
                'Change': '{:+,.0f}',
                '% Change': '{:+.1f}%'
            }).map(style_change, subset=['Change', '% Change'])

            st.dataframe(styled_df, hide_index=True, use_container_width=True)

        with col2:
            # Create grouped bar chart for comparison
            chart_df = comparison_df[comparison_df['Contact Type'] != 'TOTAL'].copy()

            fig = go.Figure()
            fig.add_trace(go.Bar(
                name=current_col,
                x=chart_df['Contact Type'],
                y=chart_df[current_col],
                marker_color='#43e97b',
                text=chart_df[current_col],
                textposition='outside'
            ))
            fig.add_trace(go.Bar(
                name=prior_col,
                x=chart_df['Contact Type'],
                y=chart_df[prior_col],
                marker_color='#a0aec0',
                text=chart_df[prior_col],
                textposition='outside'
            ))

            fig.update_layout(
                barmode='group',
                title='Contact Volume by Type',
                xaxis_title='',
                yaxis_title='Number of Contacts',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                margin=dict(l=40, r=40, t=60, b=40),
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)

        # Detailed breakdowns in expandable sections
        with st.expander("📧 Constant Contact Details (by Campaign Status)"):
            if current_summary['cc_by_status'] or prior_summary['cc_by_status']:
                all_statuses = set(current_summary['cc_by_status'].keys()) | set(prior_summary['cc_by_status'].keys())
                cc_details = []
                for status in sorted(all_statuses):
                    current_count = current_summary['cc_by_status'].get(status, 0)
                    prior_count = prior_summary['cc_by_status'].get(status, 0)
                    cc_details.append({
                        'Campaign Status': status,
                        current_col: current_count,
                        prior_col: prior_count,
                        'Change': current_count - prior_count
                    })
                cc_df = pd.DataFrame(cc_details)
                st.dataframe(cc_df.style.format({
                    current_col: '{:,.0f}',
                    prior_col: '{:,.0f}',
                    'Change': '{:+,.0f}'
                }), hide_index=True, use_container_width=True)
            else:
                st.info("No Constant Contact data available for this period.")

        with st.expander("✉️ Letter Details (by Mailing Code)"):
            if current_summary['lt_by_mailing'] or prior_summary['lt_by_mailing']:
                all_mailings = set(current_summary['lt_by_mailing'].keys()) | set(prior_summary['lt_by_mailing'].keys())
                lt_details = []
                for mailing in sorted(all_mailings):
                    current_count = current_summary['lt_by_mailing'].get(mailing, 0)
                    prior_count = prior_summary['lt_by_mailing'].get(mailing, 0)
                    lt_details.append({
                        'Mailing Code': mailing,
                        current_col: current_count,
                        prior_col: prior_count,
                        'Change': current_count - prior_count
                    })
                lt_df = pd.DataFrame(lt_details)
                st.dataframe(lt_df.style.format({
                    current_col: '{:,.0f}',
                    prior_col: '{:,.0f}',
                    'Change': '{:+,.0f}'
                }), hide_index=True, use_container_width=True)
            else:
                st.info("No Letter data available for this period.")

        # Monthly trend chart (only show if data is meaningful)
        with st.expander("📈 Monthly Contact Trend"):
            if current_summary['by_month'] or prior_summary['by_month']:
                # Combine monthly data for visualization
                all_months_current = current_summary['by_month']
                all_months_prior = prior_summary['by_month']

                if all_months_current:
                    monthly_df = pd.DataFrame([
                        {'Month': k, 'Contacts': v, 'Year': current_fy}
                        for k, v in all_months_current.items()
                    ])
                    if all_months_prior:
                        prior_monthly = pd.DataFrame([
                            {'Month': k, 'Contacts': v, 'Year': prior_fy}
                            for k, v in all_months_prior.items()
                        ])
                        monthly_df = pd.concat([monthly_df, prior_monthly], ignore_index=True)

                    # Sort by month
                    monthly_df = monthly_df.sort_values('Month')

                    fig_monthly = px.bar(
                        monthly_df,
                        x='Month',
                        y='Contacts',
                        color='Year',
                        barmode='group',
                        title='Monthly Contact Volume',
                        color_discrete_map={current_fy: '#43e97b', prior_fy: '#a0aec0'}
                    )
                    fig_monthly.update_layout(
                        xaxis_title='',
                        yaxis_title='Number of Contacts',
                        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                        margin=dict(l=40, r=40, t=60, b=40),
                        height=300
                    )
                    st.plotly_chart(fig_monthly, use_container_width=True)
                else:
                    st.info("No monthly data available.")
            else:
                st.info("No monthly trend data available.")

    except Exception as e:
        st.warning(f"Unable to load donor contacts data: {e}")
        st.info("Donor contacts metrics will appear here once the DonorPerfect API connection is configured.")


def render_financial_metrics(financial_df: pd.DataFrame = None):
    """Render Financial Metrics section with real data from Google Sheets."""
    st.markdown("""
    <div class="section-header">
        <div class="section-icon financial">💰</div>
        <div class="section-title-group">
            <h2 class="section-title">Financial Metrics</h2>
            <p class="section-subtitle">Fiscal year to date (July 1 – present) · Updated Sundays 9am</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Check if we have financial data
    if financial_df is None or financial_df.empty:
        st.info("📊 Financial data not yet connected. Set up Google Sheets integration to display metrics.")
        with st.expander("ℹ️ How to connect financial data"):
            st.markdown("""
            1. Install **Coefficient** add-on in Google Sheets
            2. Connect to QuickBooks and import reports
            3. Add service account credentials to Streamlit secrets
            4. Financial metrics will appear automatically
            """)
        return

    # Get the most recent data (assuming one row per period or latest snapshot)
    if 'date' in financial_df.columns:
        latest = financial_df.sort_values('date', ascending=False).iloc[0] if len(financial_df) > 0 else {}
    else:
        latest = financial_df.iloc[0] if len(financial_df) > 0 else {}

    # Extract metrics with safe defaults
    ytd_revenue = float(latest.get('ytd_revenue', 0) or 0)
    ytd_revenue_budget = float(latest.get('ytd_revenue_budget', 0) or 0)
    ytd_expenses = float(latest.get('ytd_expenses', 0) or 0)
    ytd_expenses_budget = float(latest.get('ytd_expenses_budget', 0) or 0)
    ytd_income = float(latest.get('ytd_income', 0) or 0)
    ytd_income_budget = float(latest.get('ytd_income_budget', 0) or 0)
    total_cash = float(latest.get('total_cash', 0) or 0)
    monthly_expenses_avg = float(latest.get('monthly_expenses_avg', 0) or 0)
    inventory_value = float(latest.get('inventory_value', 0) or 0)
    admin_expenses = float(latest.get('admin_expenses', 0) or 0)
    program_expenses = float(latest.get('program_expenses', 0) or 0)
    grants_received = float(latest.get('grants_received', 0) or 0)
    grants_goal = float(latest.get('grants_goal', 0) or 0)

    # Calculate derived metrics
    revenue_variance = ytd_revenue - ytd_revenue_budget
    revenue_variance_pct = (revenue_variance / ytd_revenue_budget * 100) if ytd_revenue_budget > 0 else 0
    expenses_variance = ytd_expenses - ytd_expenses_budget  # Positive means over budget (bad)
    expenses_variance_pct = (expenses_variance / ytd_expenses_budget * 100) if ytd_expenses_budget > 0 else 0
    months_cash_on_hand = total_cash / monthly_expenses_avg if monthly_expenses_avg > 0 else 0
    total_expenses = admin_expenses + program_expenses
    admin_pct_of_total = (admin_expenses / total_expenses * 100) if total_expenses > 0 else 0
    grants_pct_achieved = (grants_received / grants_goal * 100) if grants_goal > 0 else 0

    # Row 1: YTD Actuals with Budget Variance
    st.markdown("##### 📊 YTD Revenue & Expenses")
    col1, col2, col3 = st.columns(3)

    with col1:
        # Revenue: budget - actual
        # Positive = below budget (down arrow needed, red - bad)
        # Negative = above budget (up arrow needed, green - good)
        if ytd_revenue_budget > 0:
            rev_diff = ytd_revenue_budget - ytd_revenue  # positive if under budget
            rev_pct = (rev_diff / ytd_revenue_budget * 100)
            st.metric(
                "YTD Revenue",
                f"${ytd_revenue:,.0f}",
                delta=f"-${rev_diff:,.0f} ({-rev_pct:.1f}%)" if rev_diff > 0 else f"+${-rev_diff:,.0f} ({-rev_pct:.1f}%)",
                delta_color="normal"  # negative=red (bad), positive=green (good)
            )
        else:
            st.metric("YTD Revenue", f"${ytd_revenue:,.0f}")

    with col2:
        # Expenses: budget - actual
        # Positive = under budget (down arrow needed, green - good!)
        # Negative = over budget (up arrow needed, red - bad!)
        if ytd_expenses_budget > 0:
            exp_diff = ytd_expenses_budget - ytd_expenses  # positive if under budget
            exp_pct = (exp_diff / ytd_expenses_budget * 100)
            st.metric(
                "YTD Expenses",
                f"${ytd_expenses:,.0f}",
                delta=f"-${exp_diff:,.0f} ({-exp_pct:.1f}%)" if exp_diff > 0 else f"+${-exp_diff:,.0f} ({-exp_pct:.1f}%)",
                delta_color="inverse"
            )
        else:
            st.metric("YTD Expenses", f"${ytd_expenses:,.0f}")

    with col3:
        # Income: actual - budget (positive is good)
        if ytd_income_budget != 0:
            inc_diff = ytd_income - ytd_income_budget
            inc_pct = (inc_diff / abs(ytd_income_budget) * 100) if ytd_income_budget != 0 else 0
            st.metric(
                "YTD Net Income",
                f"${ytd_income:,.0f}",
                delta=f"+${inc_diff:,.0f} ({inc_pct:.1f}%)" if inc_diff >= 0 else f"${inc_diff:,.0f} ({inc_pct:.1f}%)",
                delta_color="normal"  # positive=green (good), negative=red (bad)
            )
        else:
            st.metric("YTD Net Income", f"${ytd_income:,.0f}")

    # Row 2: Budgets
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Revenue Budget", f"${ytd_revenue_budget:,.0f}")

    with col2:
        st.metric("Expenses Budget", f"${ytd_expenses_budget:,.0f}")

    with col3:
        st.metric("Net Income Budget", f"${ytd_income_budget:,.0f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Row 3: Cash, Inventory, Admin Ratio
    st.markdown("##### 💵 Financial Health")
    col1, col2, col3 = st.columns(3)

    with col1:
        # Color code months of cash
        if months_cash_on_hand > 0:
            cash_status = "🟢" if months_cash_on_hand >= 6 else "🟡" if months_cash_on_hand >= 3 else "🔴"
            runway_text = f"{months_cash_on_hand:.1f} months runway"
        else:
            cash_status = ""
            runway_text = "Set monthly_expenses_avg to calculate" if total_cash > 0 else None
        st.metric(
            f"Total Cash {cash_status}",
            f"${total_cash:,.0f}",
            delta=runway_text,
            delta_color="off"
        )

    with col2:
        st.metric("Inventory Value", f"${inventory_value:,.0f}")

    with col3:
        # Admin % of total - lower is generally better for nonprofits
        ratio_status = "🟢" if admin_pct_of_total <= 20 else "🟡" if admin_pct_of_total <= 30 else "🔴"
        st.metric(
            f"Admin % of Total Expenses {ratio_status}",
            f"{admin_pct_of_total:.1f}%"
        )

    # Show last updated date
    if 'date' in latest and pd.notna(latest.get('date')):
        last_updated = pd.to_datetime(latest['date']).strftime('%B %d, %Y')
        st.markdown(f"<p style='color: #94a3b8; font-size: 0.75rem; text-align: right; margin-top: 1rem;'>Financial data as of {last_updated}</p>", unsafe_allow_html=True)


def render_upcoming_events(events_data: list):
    """Render upcoming events section."""
    st.markdown("""
    <div class="section-header">
        <div class="section-icon" style="background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);">📅</div>
        <div class="section-title-group">
            <h2 class="section-title">Upcoming Events</h2>
            <p class="section-subtitle">BookSpring events in the next 2 months</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not events_data:
        st.info("No events data available")
        return

    # Convert to DataFrame
    df = pd.DataFrame(events_data)

    # Convert list columns to strings
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, list)).any():
            df[col] = df[col].apply(
                lambda x: x[0] if isinstance(x, list) and len(x) == 1
                else ", ".join(str(i) for i in x) if isinstance(x, list)
                else x
            )

    # Filter by status first
    valid_statuses = ["Date decided", "Ready for Delivery", "Completed"]
    if "status" in df.columns:
        status_mask = df["status"].isin(valid_statuses)
        df = df[status_mask].copy()

    if df.empty:
        st.info("No events with valid status")
        return

    # Find the date column (decided_date or similar)
    date_col = None
    for col in ['decided_date', 'event_date', 'date', 'start_date']:
        if col in df.columns:
            date_col = col
            break

    if not date_col:
        st.warning("No date field found in events data")
        return

    # Parse dates - handle date ranges (e.g., "2026-01-15 to 2026-01-17" or date range objects)
    def parse_event_date(date_val):
        """Parse event date, handling ranges by returning start date."""
        if pd.isna(date_val):
            return pd.NaT
        if isinstance(date_val, str):
            # Handle range format "date1 to date2" or "date1 - date2"
            for sep in [' to ', ' - ', '|']:
                if sep in date_val:
                    date_val = date_val.split(sep)[0].strip()
                    break
        return pd.to_datetime(date_val, errors='coerce')

    def parse_event_end_date(row):
        """Parse event end date if it's a range."""
        date_val = row.get(date_col)
        if pd.isna(date_val):
            return pd.NaT
        if isinstance(date_val, str):
            for sep in [' to ', ' - ', '|']:
                if sep in date_val:
                    parts = date_val.split(sep)
                    if len(parts) > 1:
                        return pd.to_datetime(parts[1].strip(), errors='coerce')
        return pd.NaT

    df['_event_date'] = df[date_col].apply(parse_event_date)
    df['_event_end_date'] = df.apply(parse_event_end_date, axis=1)

    # Filter for events within next 2 months
    today = pd.Timestamp.now().normalize()
    two_months_later = today + pd.DateOffset(months=2)
    upcoming_mask = (df['_event_date'] >= today) & (df['_event_date'] <= two_months_later)
    upcoming_df = df[upcoming_mask].sort_values('_event_date')

    if upcoming_df.empty:
        st.info("No upcoming events in the next 2 months")
        return

    # Display count
    st.markdown(f"**{len(upcoming_df)} upcoming event{'s' if len(upcoming_df) != 1 else ''}**")

    # Display events as compact cards - 2 per row
    events_list = upcoming_df.to_dict('records')
    for i in range(0, len(events_list), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j < len(events_list):
                event = events_list[i + j]
                event_dt = pd.to_datetime(event.get('_event_date'))
                event_end_dt = pd.to_datetime(event.get('_event_end_date')) if pd.notna(event.get('_event_end_date')) else None

                # Format date - show range if end date exists
                if pd.notna(event_dt):
                    event_day = event_dt.strftime('%a')
                    if event_end_dt and pd.notna(event_end_dt) and event_end_dt != event_dt:
                        # Date range
                        event_date = f"{event_dt.strftime('%b %d')} - {event_end_dt.strftime('%b %d')}"
                    else:
                        event_date = event_dt.strftime('%b %d, %Y')
                else:
                    event_day = ''
                    event_date = 'TBD'

                # Get event details from Fusioo fields
                org_site = event.get('organizationsite_name_1', '') or 'Event'
                program = event.get('program', '')
                contact = event.get('bookspring_contact', '')

                # Build details string
                details = []
                if program:
                    details.append(f"🏷️ {program}")
                if contact:
                    details.append(f"👤 {contact}")

                with col:
                    st.markdown(f"""
                    <div style="display: flex; gap: 0.75rem; padding: 0.875rem; background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 100%); border: 1px solid #e5e7eb; border-radius: 12px; border-left: 4px solid #8b5cf6; height: 100%; margin-bottom: 0.75rem;">
                        <div style="min-width: 55px; text-align: center;">
                            <div style="font-size: 0.7rem; color: #6b7280; text-transform: uppercase;">{event_day}</div>
                            <div style="font-size: 0.85rem; font-weight: 700; color: #1a202c;">{event_date}</div>
                        </div>
                        <div style="flex: 1; min-width: 0;">
                            <div style="font-weight: 600; color: #1a202c; margin-bottom: 0.25rem; font-size: 0.9rem;">📍 {org_site}</div>
                            <div style="font-size: 0.75rem; color: #6b7280; overflow: hidden; text-overflow: ellipsis;">{' · '.join(details) if details else ''}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)


def render_trends_section(processor: DataProcessor, time_unit: str, views_data: list = None, start_date: date = None, end_date: date = None):
    """Render trends over time section."""
    st.markdown("""
    <div class="section-header">
        <div class="section-icon trends">📈</div>
        <div class="section-title-group">
            <h2 class="section-title">Trends Over Time</h2>
            <p class="section-subtitle">Analyze metric patterns across different time periods</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    strategic_metrics = {
        "Core Metrics": ["_of_books_distributed", "total_children", "parents_or_caregivers"],
        "Books per Child": ["avg_books_per_child", "books_per_child_0_2", "books_per_child_3_5",
                           "books_per_child_6_8", "books_per_child_9_12", "books_per_child_teens"],
        "Children by Age": ["children_035_months", "children_35_years", "children_68_years",
                           "children_912_years", "teens"],
        "Engagement (Views)": ["views"]
    }

    category = st.selectbox("Select Metric Category", list(strategic_metrics.keys()), key="trend_category")

    if category == "Engagement (Views)" and views_data:
        views_df = pd.DataFrame(views_data)
        for col in views_df.columns:
            if views_df[col].apply(lambda x: isinstance(x, list)).any():
                views_df[col] = views_df[col].apply(
                    lambda x: x[0] if isinstance(x, list) and len(x) == 1 else x
                )

        view_cols = ["total_digital_views", "total_newsletter_views"]
        available_view_cols = [c for c in view_cols if c in views_df.columns]

        for col in available_view_cols:
            views_df[col] = pd.to_numeric(views_df[col], errors='coerce').fillna(0)

        if "date" in views_df.columns and available_view_cols:
            views_df["_parsed_date"] = views_df["date"].apply(
                lambda x: x.split("|")[0] if isinstance(x, str) and "|" in x else x
            )
            views_df["_parsed_date"] = pd.to_datetime(views_df["_parsed_date"], errors='coerce')
            valid_df = views_df[views_df["_parsed_date"].notna()].copy()

            if start_date and end_date:
                mask = (valid_df["_parsed_date"] >= pd.Timestamp(start_date)) & (valid_df["_parsed_date"] <= pd.Timestamp(end_date))
                valid_df = valid_df[mask].copy()

            if not valid_df.empty:
                freq_map = {"day": "D", "week": "W", "month": "ME", "quarter": "QE", "year": "YE"}
                freq = freq_map.get(time_unit, "ME")

                trend_df = valid_df.groupby(pd.Grouper(key="_parsed_date", freq=freq))[available_view_cols].sum().reset_index()
                trend_df = trend_df.rename(columns={
                    "_parsed_date": "period",
                    "total_digital_views": "Digital Views",
                    "total_newsletter_views": "Newsletter Views"
                })

                display_cols = [c for c in ["Digital Views", "Newsletter Views"] if c in trend_df.columns]

                if display_cols:
                    fig = px.line(trend_df, x="period", y=display_cols, markers=True,
                                 color_discrete_sequence=["#f093fb", "#f5576c"])
                    fig = style_plotly_chart(fig, height=400)
                    fig.update_layout(xaxis_title=time_unit.title(), yaxis_title="Views")
                    st.plotly_chart(fig, use_container_width=True)
    else:
        available_metrics = [m for m in strategic_metrics[category] if m in processor.df.columns]
        if available_metrics:
            time_df = processor.aggregate_by_time(time_unit, available_metrics)
            if not time_df.empty:
                rename_map = {c: get_friendly_name(c) for c in time_df.columns if c != "period"}
                display_df = time_df.rename(columns=rename_map)

                fig = px.line(display_df, x="period", y=[get_friendly_name(m) for m in available_metrics],
                             markers=True, color_discrete_sequence=["#667eea", "#38a169", "#ed8936", "#9f7aea", "#f5576c"])
                fig = style_plotly_chart(fig, height=400)
                fig.update_layout(xaxis_title=time_unit.title(), yaxis_title="Value")
                st.plotly_chart(fig, use_container_width=True)


def render_period_comparison(processor: DataProcessor):
    """Render period comparison section."""
    st.markdown("""
    <div class="section-header">
        <div class="section-icon compare">🔄</div>
        <div class="section-title-group">
            <h2 class="section-title">Period Comparison</h2>
            <p class="section-subtitle">Compare metrics between two date ranges</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    large_scale_metrics = ["_of_books_distributed", "total_children", "parents_or_caregivers"]
    small_scale_metrics = ["avg_books_per_child", "minutes_of_activity"]
    all_metrics = large_scale_metrics + small_scale_metrics
    available_metrics = [m for m in all_metrics if m in processor.df.columns]

    today = date.today()

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        st.markdown("##### Period 1")
        p1_col1, p1_col2 = st.columns(2)
        with p1_col1:
            p1_start = st.date_input("Start", today - relativedelta(months=6), key="p1_start")
        with p1_col2:
            p1_end = st.date_input("End", today - relativedelta(months=3), key="p1_end")

    with col2:
        st.markdown("##### Period 2")
        p2_col1, p2_col2 = st.columns(2)
        with p2_col1:
            p2_start = st.date_input("Start", today - relativedelta(months=3), key="p2_start")
        with p2_col2:
            p2_end = st.date_input("End", today, key="p2_end")

    with col3:
        st.markdown("##### &nbsp;")
        compare_clicked = st.button("Compare Periods", type="primary", use_container_width=True)

    if compare_clicked:
        comparison_df = processor.compare_periods(p1_start, p1_end, p2_start, p2_end, available_metrics)

        if not comparison_df.empty:
            comparison_df["metric"] = comparison_df["metric"].apply(get_friendly_name)

            col1, col2 = st.columns([1, 1])

            with col1:
                st.markdown("##### Volume Metrics")
                large_metrics_friendly = [get_friendly_name(m) for m in large_scale_metrics if m in available_metrics]
                large_df = comparison_df[comparison_df["metric"].isin(large_metrics_friendly)]

                if not large_df.empty:
                    fig = go.Figure(data=[
                        go.Bar(name="Period 1", x=large_df["metric"], y=large_df["period_1"], marker_color="#667eea"),
                        go.Bar(name="Period 2", x=large_df["metric"], y=large_df["period_2"], marker_color="#38a169")
                    ])
                    fig.update_layout(barmode="group")
                    fig = style_plotly_chart(fig, height=300)
                    fig.update_layout(yaxis_title="Count")
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown("##### Percent Change")
                fig = px.bar(
                    comparison_df,
                    x="metric",
                    y="percent_change",
                    color="percent_change",
                    color_continuous_scale=["#f5576c", "#f7fafc", "#38a169"],
                    color_continuous_midpoint=0
                )
                fig = style_plotly_chart(fig, height=300)
                fig.update_layout(showlegend=False, coloraxis_showscale=False, yaxis_title="% Change")
                st.plotly_chart(fig, use_container_width=True)


def render_export_section(processor: DataProcessor):
    """Render export section."""
    st.markdown("""
    <div class="section-header">
        <div class="section-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">📥</div>
        <div class="section-title-group">
            <h2 class="section-title">Export Report</h2>
            <p class="section-subtitle">Download comprehensive Excel reports</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        export_time_unit = st.selectbox("Time Unit", ["day", "week", "month", "quarter", "year", "fiscal_year"],
                                        index=2, key="export_time_unit")

    with col2:
        report_filename = st.text_input("Filename", f"bookspring_strategic_report_{date.today().isoformat()}.xlsx")

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Generate Report", type="primary", use_container_width=True):
            with st.spinner("Generating report..."):
                try:
                    output_path = f"reports/{report_filename}"
                    generate_standard_report(processor, output_path, export_time_unit)

                    with open(output_path, "rb") as f:
                        st.download_button(
                            label="Download Excel",
                            data=f.read(),
                            file_name=report_filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    st.success("Report generated successfully!")
                except Exception as e:
                    st.error(f"Error generating report: {e}")


def main():
    """Main dashboard function."""
    # Sidebar
    with st.sidebar:
        # 2030 Targets at the top
        st.markdown("##### 🎯 2030 Targets")
        st.markdown("""
        <div class="sidebar-targets">
            <div class="sidebar-target-item">📚 <strong>600K</strong> books/year</div>
            <div class="sidebar-target-item">👶 <strong>150K</strong> children/year</div>
            <div class="sidebar-target-item">📖 <strong>4</strong> books/child</div>
            <div class="sidebar-target-item">💰 <strong>$3M</strong> budget</div>
            <div class="sidebar-target-item">📱 <strong>1.5M</strong> digital views</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Date Range
        st.markdown("##### 📅 Date Range")
        today = date.today()
        # Fiscal year to date: July 1 of current fiscal year
        fiscal_year = today.year if today.month >= 7 else today.year - 1
        default_start = date(fiscal_year, 7, 1)
        start_date = st.date_input("From", default_start)
        end_date = st.date_input("To", today)

        st.markdown("---")

        # Display Settings
        st.markdown("##### ⚙️ Display Settings")
        time_unit = st.selectbox("Time Aggregation", ["day", "week", "month", "quarter", "year", "fiscal_year"], index=2)

        st.markdown("---")

        # Refresh buttons
        # Check if running on localhost for financial refresh button
        is_localhost = os.getenv("HOSTNAME", "localhost") == "localhost" or "localhost" in os.getenv("STREAMLIT_SERVER_ADDRESS", "localhost")

        if is_localhost:
            if st.button("🔄 Refresh Financial Metrics", use_container_width=True, help="Refresh financial data from Google Sheets"):
                load_financial_data.clear()
                st.toast("Refreshing financial metrics...", icon="💰")
                st.rerun()

        if st.button("🔄 Refresh Data from Fusioo", use_container_width=True, help="Click to pull latest data from Fusioo"):
            st.cache_data.clear()
            st.toast("Fetching fresh data from Fusioo...", icon="🔄")
            st.rerun()

        if st.button("📅 Refresh Events", use_container_width=True, help="Refresh only upcoming events data"):
            load_events_data.clear()
            st.toast("Refreshing events data...", icon="📅")
            st.rerun()

    # Load data
    with st.spinner("Loading data..."):
        activity_records = load_activity_data()
        legacy_records = load_legacy_data()
        original_books = load_original_books()
        content_views = load_content_views()
        financial_data = load_financial_data()
        enrollment_count = load_active_enrollment_count()
        events_data = load_events_data()
        partners_data = load_partners_data()

    # Combine current and legacy activity data
    legacy_count = 0
    if legacy_records:
        combined_records = combine_activity_data(activity_records, legacy_records)
        legacy_count = len(combined_records) - len(activity_records)
    else:
        combined_records = activity_records

    if not combined_records:
        st.error("Could not load activity data. Please check API credentials.")
        return

    # Show data source info in sidebar
    with st.sidebar:
        if legacy_count > 0:
            st.info(f"📊 Includes {legacy_count:,} legacy records (pre-July 2025)")

    processor = DataProcessor(combined_records)
    processor = processor.filter_by_date_range(start_date, end_date)

    if processor.df.empty:
        st.warning("No data found for the selected date range.")
        return

    # Zero out children counts for previously served rows
    if "previously_served_this_fy" in processor.df.columns:
        prev_served = processor.df["previously_served_this_fy"] == True
        children_cols = [
            "total_children", "children_035_months", "children_03_years",
            "children_35_years", "children_34_years", "children_68_years",
            "children_512_years", "children_912_years", "teens"
        ]
        for col in children_cols:
            if col in processor.df.columns:
                processor.df.loc[prev_served, col] = 0

        # Recalculate average books per child metrics after zeroing
        books_col = "_of_books_distributed"
        if books_col in processor.df.columns:
            # Recalculate total children from age columns
            age_cols = [c for c in children_cols if c != "total_children" and c in processor.df.columns]
            processor.df["_total_children_calc"] = processor.df[age_cols].fillna(0).sum(axis=1)

            # Recalculate overall avg books per child
            processor.df["avg_books_per_child"] = processor.df.apply(
                lambda row: row[books_col] / row["_total_children_calc"]
                if row["_total_children_calc"] > 0 else 0, axis=1
            )

            # Recalculate books per child by age group
            age_group_sources = {
                "books_per_child_0_2": ["children_035_months", "children_03_years"],
                "books_per_child_3_5": ["children_35_years", "children_34_years"],
                "books_per_child_6_8": ["children_68_years", "children_512_years"],
                "books_per_child_9_12": ["children_912_years"],
                "books_per_child_teens": ["teens"],
            }
            for metric_col, source_cols in age_group_sources.items():
                available_sources = [c for c in source_cols if c in processor.df.columns]
                if available_sources:
                    age_children = processor.df[available_sources].fillna(0).sum(axis=1)
                    processor.df[metric_col] = 0.0
                    mask = (processor.df["_total_children_calc"] > 0) & (age_children > 0)
                    processor.df.loc[mask, metric_col] = (
                        processor.df.loc[mask, books_col] / processor.df.loc[mask, "_total_children_calc"]
                    )

            # Clean up temp column
            if "_total_children_calc" in processor.df.columns:
                processor.df.drop("_total_children_calc", axis=1, inplace=True)

    # Calculate book bank children (Open Book Distribution program)
    book_bank_children = 0
    if "program" in processor.df.columns:
        # Filter for book bank programs
        book_bank_mask = processor.df["program"].isin([
            "Open Book Distribution",
            "ReBook/Open Book Distribution"
        ])
        if "total_children" in processor.df.columns:
            book_bank_children = int(processor.df.loc[book_bank_mask, "total_children"].sum())

    # Calculate in-person events count
    # Count records where activity_type contains "Literacy Materials Distribution" OR "Family Literacy Activity"
    # A record with both types counts as one event
    inperson_events = 0
    if "activity_type" in processor.df.columns:
        # Check if activity_type contains either value (handles both single values and comma-separated lists)
        event_mask = processor.df["activity_type"].apply(
            lambda x: "Literacy Materials Distribution" in str(x) or "Family Literacy Activity" in str(x)
            if pd.notna(x) else False
        )
        inperson_events = int(event_mask.sum())

    # Hero header
    render_hero_header(processor)

    # Dashboard sections
    render_goal1_strengthen_impact(processor, time_unit)
    st.markdown("---")

    render_goal2_inspire_engagement(content_views, time_unit, start_date, end_date, enrollment_count, book_bank_children, inperson_events, activity_records, partners_data)
    st.markdown("---")

    render_goal3_advance_innovation(original_books)
    st.markdown("---")

    render_goal4_sustainability(processor, financial_data)
    st.markdown("---")

    render_financial_metrics(financial_data)
    st.markdown("---")

    render_upcoming_events(events_data)
    st.markdown("---")

    render_trends_section(processor, time_unit, content_views, start_date, end_date)
    st.markdown("---")

    render_period_comparison(processor)
    st.markdown("---")

    render_export_section(processor)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem 0;">
        <p style="color: #64748b; font-size: 0.85rem; margin: 0;">
            📚 <strong>BookSpring Strategic Dashboard</strong>
        </p>
        <p style="color: #94a3b8; font-size: 0.75rem; margin: 0.5rem 0 0 0;">
            Click "Refresh Data from Fusioo" in sidebar to pull latest data &nbsp;•&nbsp; Built with Streamlit
        </p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
