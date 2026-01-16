"""Streamlit dashboard for BookSpring metrics - Strategic Goals Edition."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
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
INVENTORY_APP_ID = os.getenv("INVENTORY_APP_ID", "i9b10a433e9414b67ae1a5d77b4a7769d")

# Google Sheets configuration
FINANCIAL_SHEET_ID = os.getenv("FINANCIAL_SHEET_ID", "17jObocsIQJnazyvWToi_AtsrLJ1I9bnMpWw9BMiixA8")

# DonorPerfect API configuration
DONORPERFECT_API_KEY = os.getenv("DONORPERFECT_API_KEY", "0rmTeFqHOlaFmZM%2fOlUhnixnvaJaEazzlUh%2bAvxFuukjhgKf6K3ISsVEnom4rg%2bV0kuHNUIVceApdPdPviy0OjeEpKLbkUL3QZaXKvH0Veo%3d")
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
    "percentage_low_income",
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


@st.cache_data(ttl=259200)  # Cache for 72 hours (legacy data changes infrequently)
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
def load_b3_low_income_stats():
    """Load B3 enrollment stats including % low income eligible.

    Uses server-side count/filter API only (no record fetching for privacy).
    Returns tuple of (active_count, low_income_pct).
    """
    try:
        client = FusiooClient()

        # Count all active enrollments
        active_filters = {"active_enrollment": {"equal": True}}
        result = client._request("POST", f"records/apps/{B3_CHILD_FAMILY_APP_ID}/count/filter", json=active_filters)
        active_count = result.get("data", {}).get("count", 0)

        # Count active enrollments that are also low income eligible (Yes)
        # Field is an array, so use "contains" instead of "equal"
        low_income_filters = {
            "active_enrollment": {"equal": True},
            "low_income_eligible": {"contains": "Yes"}
        }
        result = client._request("POST", f"records/apps/{B3_CHILD_FAMILY_APP_ID}/count/filter", json=low_income_filters)
        low_income_count = result.get("data", {}).get("count", 0)

        low_income_pct = (low_income_count / active_count * 100) if active_count > 0 else 0.0
        return active_count, low_income_pct
    except Exception as e:
        st.error(f"Failed to load B3 low income stats: {e}")
        return 0, 0.0


def _get_ttl_until_noon_refresh():
    """Calculate seconds until next 12:05pm for financial data refresh.

    Returns TTL in seconds that will cause cache to expire at 12:05pm daily,
    aligning with the Google Sheets update schedule (updates at noon).
    """
    now = datetime.now()
    target_time = now.replace(hour=12, minute=5, second=0, microsecond=0)

    # If it's already past 12:05pm today, target tomorrow's 12:05pm
    if now >= target_time:
        target_time += timedelta(days=1)

    ttl_seconds = (target_time - now).total_seconds()
    return int(ttl_seconds)


@st.cache_data(ttl=_get_ttl_until_noon_refresh())  # Cache until 12:05pm daily
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


@st.cache_data(ttl=86400)  # Cache for 24 hours
def load_events_data():
    """Load events data from Fusioo."""
    try:
        client = FusiooClient()
        records = client.get_all_records(EVENTS_APP_ID)
        return records
    except Exception as e:
        st.error(f"Failed to load events data: {e}")
        return []


@st.cache_data(ttl=86400)  # Cache for 24 hours
def load_partners_data():
    """Load partners data from Fusioo for partner name lookups and low income stats."""
    try:
        client = FusiooClient()
        # Fetch fields needed for display and low income calculation - avoid loading PII
        records = client.get_all_records(PARTNERS_APP_ID, fields=["id", "site_name", "main_organization_from_list", "percentage_lowincome"])
        return records
    except Exception as e:
        st.error(f"Failed to load partners data: {e}")
        return []


@st.cache_data(ttl=86400)  # Cache for 24 hours
def load_donated_books_count(start_date: str, end_date: str):
    """Load donated books count from Fusioo Inventory Data for a date range.

    Filters for: receiving_or_distributing = Receiving, books_in_purchase_or_donation = Donated,
    date_of_transaction within start_date to end_date.
    Returns sum of total_books_this_entry for matching records.
    """
    try:
        client = FusiooClient()
        records = client.get_all_records(INVENTORY_APP_ID)

        # Parse date range
        start_dt = pd.to_datetime(start_date).date()
        end_dt = pd.to_datetime(end_date).date()

        # Filter for donated receiving transactions and sum books
        total_donated = 0
        for record in records:
            # Check date is within range
            transaction_date = record.get('date_of_transaction', '')
            if not transaction_date:
                continue

            try:
                if isinstance(transaction_date, str):
                    record_date = pd.to_datetime(transaction_date).date()
                else:
                    record_date = pd.to_datetime(str(transaction_date)).date()

                if not (start_dt <= record_date <= end_dt):
                    continue
            except (ValueError, TypeError):
                continue

            receiving_or_distributing = record.get('receiving_or_distributing', '')
            books_in_purchase_or_donation = record.get('books_in_purchase_or_donation', '')

            # Normalize values for comparison (handle list values from Fusioo)
            if isinstance(receiving_or_distributing, list):
                receiving_or_distributing = receiving_or_distributing[0] if receiving_or_distributing else ''
            if isinstance(books_in_purchase_or_donation, list):
                books_in_purchase_or_donation = books_in_purchase_or_donation[0] if books_in_purchase_or_donation else ''

            # Check if this is a donated receiving transaction
            if str(receiving_or_distributing).lower() == 'receiving' and str(books_in_purchase_or_donation).lower() == 'donated':
                books_count = record.get('total_books_this_entry', 0)
                if isinstance(books_count, (int, float)):
                    total_donated += int(books_count)
                elif isinstance(books_count, str) and books_count.isdigit():
                    total_donated += int(books_count)

        return total_donated
    except Exception as e:
        st.error(f"Failed to load inventory data: {e}")
        return 0


def _execute_donorperfect_query(query: str) -> tuple:
    """Execute a single DonorPerfect query and return results.

    Args:
        query: SQL query string

    Returns:
        Tuple of (list of record dicts, debug_info dict)
    """
    debug_info = {'query': query}
    try:
        url = f"{DONORPERFECT_BASE_URL}?apikey={DONORPERFECT_API_KEY}&action={quote(query)}"
        debug_info['url'] = f"{DONORPERFECT_BASE_URL}?apikey=****&action={quote(query)}"

        response = requests.get(url, timeout=60)
        response.raise_for_status()
        debug_info['status_code'] = response.status_code
        debug_info['response_preview'] = response.text[:1000] if response.text else "Empty response"

        # Parse XML response
        # DonorPerfect returns: <result><record><field name='x' value='y'/></record></result>
        root = ET.fromstring(response.content)

        records = []
        for rec in root.findall('.//record'):
            record = {}
            for field in rec.findall('field'):
                name = field.get('name')
                value = field.get('value')  # Value is in 'value' attribute, not text
                record[name] = value
            records.append(record)

        debug_info['records_found'] = len(records)
        return records, debug_info

    except Exception as e:
        debug_info['error'] = str(e)
        return [], debug_info


@st.cache_data(ttl=86400, show_spinner=False)  # Cache for 24 hours
def load_donorperfect_contact_metrics(start_date: str, end_date: str) -> dict:
    """Load aggregated contact metrics from DonorPerfect using GROUP BY queries.

    Uses multiple small aggregated queries instead of pulling raw data to avoid
    DonorPerfect's 500 row limit.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Dictionary with aggregated metrics and debug info
    """
    debug_info = {'queries': []}

    # Query 1: Count by activity_code
    query_by_type = f"SELECT activity_code, COUNT(*) as cnt FROM dpcontact WHERE contact_date BETWEEN '{start_date}' AND '{end_date}' GROUP BY activity_code"
    by_type_records, by_type_debug = _execute_donorperfect_query(query_by_type)
    debug_info['queries'].append({'name': 'by_type', **by_type_debug})

    # Query 2: CC contacts by em_campaign_status
    query_cc_status = f"SELECT em_campaign_status, COUNT(*) as cnt FROM dpcontact WHERE contact_date BETWEEN '{start_date}' AND '{end_date}' AND activity_code = 'CC' GROUP BY em_campaign_status"
    cc_status_records, cc_status_debug = _execute_donorperfect_query(query_cc_status)
    debug_info['queries'].append({'name': 'cc_by_status', **cc_status_debug})

    # Query 3: LT/blank contacts by mailing_code
    query_lt_mailing = f"SELECT mailing_code, COUNT(*) as cnt FROM dpcontact WHERE contact_date BETWEEN '{start_date}' AND '{end_date}' AND (activity_code = 'LT' OR activity_code IS NULL OR activity_code = '') GROUP BY mailing_code"
    lt_mailing_records, lt_mailing_debug = _execute_donorperfect_query(query_lt_mailing)
    debug_info['queries'].append({'name': 'lt_by_mailing', **lt_mailing_debug})

    # Query 4: Monthly breakdown
    query_monthly = f"SELECT MONTH(contact_date) as month, YEAR(contact_date) as year, COUNT(*) as cnt FROM dpcontact WHERE contact_date BETWEEN '{start_date}' AND '{end_date}' GROUP BY YEAR(contact_date), MONTH(contact_date)"
    monthly_records, monthly_debug = _execute_donorperfect_query(query_monthly)
    debug_info['queries'].append({'name': 'monthly', **monthly_debug})

    # Process results into metrics dict
    by_type = {}
    total = 0
    for rec in by_type_records:
        code = rec.get('activity_code') or 'LT'  # Treat blank as LT
        if code == '':
            code = 'LT'
        cnt = int(rec.get('cnt', 0) or 0)
        # Merge blank into LT
        if code in by_type:
            by_type[code] += cnt
        else:
            by_type[code] = cnt
        total += cnt

    cc_by_status = {}
    for rec in cc_status_records:
        status = rec.get('em_campaign_status') or 'Unknown'
        if status == '':
            status = 'Unknown'
        cnt = int(rec.get('cnt', 0) or 0)
        cc_by_status[status] = cnt

    lt_by_mailing = {}
    for rec in lt_mailing_records:
        mailing = rec.get('mailing_code') or 'Unknown'
        if mailing == '':
            mailing = 'Unknown'
        cnt = int(rec.get('cnt', 0) or 0)
        lt_by_mailing[mailing] = cnt

    by_month = {}
    for rec in monthly_records:
        month = rec.get('month')
        year = rec.get('year')
        cnt = int(rec.get('cnt', 0) or 0)
        if month and year:
            period = f"{year}-{int(month):02d}"
            by_month[period] = cnt

    return {
        'total': total,
        'by_type': by_type,
        'cc_by_status': cc_by_status,
        'lt_by_mailing': lt_by_mailing,
        'by_month': by_month,
        'debug': debug_info
    }


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


def get_contact_metrics_comparison() -> dict:
    """Get contact metrics for current FY vs prior FY to date using aggregated queries.

    Returns:
        Dictionary with current and prior FY metrics plus labels and debug info
    """
    today = date.today()
    fy_info = get_fiscal_year_info(today)

    # Current fiscal year: FY start to today
    current_fy_start = fy_info['current_fy_start'].strftime("%Y-%m-%d")
    current_fy_end = today.strftime("%Y-%m-%d")

    # Prior fiscal year to same date: Prior FY start to same date last year
    prior_fy_start = fy_info['prior_fy_start'].strftime("%Y-%m-%d")
    prior_fy_end = today.replace(year=today.year - 1).strftime("%Y-%m-%d")

    # Load aggregated metrics (these use GROUP BY queries to avoid 500 row limit)
    current_metrics = load_donorperfect_contact_metrics(current_fy_start, current_fy_end)
    prior_metrics = load_donorperfect_contact_metrics(prior_fy_start, prior_fy_end)

    current_fy_short = fy_info['current_fy_short']
    prior_fy_short = fy_info['prior_fy_short']

    return {
        'current_fy': current_metrics,
        'prior_fy': prior_metrics,
        'current_fy_label': f"{current_fy_short} YTD ({current_fy_start} - {current_fy_end})",
        'prior_fy_label': f"{prior_fy_short} YTD ({prior_fy_start} - {prior_fy_end})",
        'current_fy_short': current_fy_short,
        'prior_fy_short': prior_fy_short
    }


# =============================================================================
# DONOR COMPARISON METRICS (from DonorPerfect)
# =============================================================================

# Outlier threshold - exclude gifts >= this amount from metrics to avoid skewing comparisons
DONOR_GIFT_OUTLIER_THRESHOLD = 500000  # $500K

# GL_CODE categorization (from DonorPerfect)
GL_CODE_GIFTS = {
    '5100_GIFTS_UNRES': 'Gifts - Unrestricted',
    '5111_GIFTS_RES': 'Gifts - Restricted',
    '5130_CAPITALGIFT': 'Capital Gift',
}

GL_CODE_GRANTS = {
    '5120_GRANTS_RES': 'Grants - Restricted',
    '5121_GRANTS_UNRES': 'Grants - Unrestricted',
}

GL_CODE_OTHER = {
    '4110_FEES_PROGRAM': 'Program Fees',
    '4120_CONTRACTS': 'Contracts - Revenue',
    '4210_SPONSORSHIPS': 'Sponsorships',
    '4310_EVENT_REVENUE': 'Event Revenue',
    '5210_INK_BOOKS': 'In-Kind Books',
    '5220_IN_KIND_PROD': 'In-Kind Products',
    '5230_IK_SVC': 'In-Kind Services',
    '5310_INVESTMENT': 'Investment Income',
    'OTHERINCOME': 'Other Income',
}

# Combined lookup for all GL codes
GL_CODE_LABELS = {**GL_CODE_GIFTS, **GL_CODE_GRANTS, **GL_CODE_OTHER}

# Base filter for Individual donors (non-organization, gift records, gift GL codes)
INDIVIDUAL_DONOR_BASE_FILTER = f"""
    d.org_rec = 'N'
    AND g.record_type = 'G'
    AND g.gl_code LIKE '51%'
    AND g.gl_code <> '5130_CAPITALGIFT'
    AND g.solicit_code <> 'SUSTAINING_MEMBER'
    AND g.amount < {DONOR_GIFT_OUTLIER_THRESHOLD}
"""

# Base filter for Organization donors
ORGANIZATION_DONOR_BASE_FILTER = f"""
    d.org_rec = 'Y'
    AND g.record_type = 'G'
    AND g.gl_code LIKE '51%'
    AND g.gl_code <> '5130_CAPITALGIFT'
    AND g.solicit_code <> 'SUSTAINING_MEMBER'
    AND g.amount < {DONOR_GIFT_OUTLIER_THRESHOLD}
"""

# Base filter for ALL donors (Total = Individuals + Organizations)
ALL_DONOR_BASE_FILTER = f"""
    g.record_type = 'G'
    AND g.gl_code LIKE '51%'
    AND g.gl_code <> '5130_CAPITALGIFT'
    AND g.solicit_code <> 'SUSTAINING_MEMBER'
    AND g.amount < {DONOR_GIFT_OUTLIER_THRESHOLD}
"""


@st.cache_data(ttl=86400, show_spinner=False)  # Cache for 24 hours
def load_individual_donor_metrics(
    current_start: str,
    current_end: str,
    prior_start: str,
    prior_end: str
) -> dict:
    """Load Individual donor metrics from DonorPerfect.

    Args:
        current_start: Start date of current period (YYYY-MM-DD)
        current_end: End date of current period (YYYY-MM-DD)
        prior_start: Start date of prior period (YYYY-MM-DD)
        prior_end: End date of prior period (YYYY-MM-DD)

    Returns:
        Dictionary with all Individual donor metrics for both periods
    """
    debug_info = {'queries': []}

    def execute_query(query: str, name: str) -> list:
        """Execute a single query and track debug info."""
        try:
            url = f"{DONORPERFECT_BASE_URL}?apikey={DONORPERFECT_API_KEY}&action={quote(query)}"
            response = requests.get(url, timeout=120)
            response.raise_for_status()

            root = ET.fromstring(response.content)
            records = []
            for rec in root.findall('.//record'):
                record = {}
                for field in rec.findall('field'):
                    record[field.get('name')] = field.get('value')
                records.append(record)

            debug_info['queries'].append({'name': name, 'records': len(records)})
            return records
        except Exception as e:
            debug_info['queries'].append({'name': name, 'error': str(e)})
            return []

    # Helper to safely get float/int from result
    def safe_float(val):
        try:
            return float(val) if val else 0.0
        except:
            return 0.0

    def safe_int(val):
        try:
            return int(val) if val else 0
        except:
            return 0

    # -------------------------------------------------------------------------
    # CURRENT PERIOD METRICS
    # -------------------------------------------------------------------------

    # Query 1: Total Revenue, Gift Count, Largest Gift - Current Period
    q1_current = f"""
        SELECT SUM(g.amount) as total_revenue, COUNT(*) as gift_count, MAX(g.amount) as largest_gift
        FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
        WHERE g.gift_date BETWEEN '{current_start}' AND '{current_end}'
        AND {INDIVIDUAL_DONOR_BASE_FILTER}
    """
    r1_current = execute_query(q1_current, 'current_totals')
    current_totals = r1_current[0] if r1_current else {}

    # Query 2: New Donors - Current Period
    q2_current = f"""
        SELECT COUNT(DISTINCT g.donor_id) as new_donors, SUM(g.amount) as new_donor_amount
        FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
        WHERE g.gift_date BETWEEN '{current_start}' AND '{current_end}'
        AND {INDIVIDUAL_DONOR_BASE_FILTER}
        AND NOT EXISTS (SELECT 1 FROM dpgift g2 WHERE g2.donor_id = g.donor_id AND g2.gift_date < '{current_start}')
    """
    r2_current = execute_query(q2_current, 'current_new_donors')
    current_new = r2_current[0] if r2_current else {}

    # Query 3: Reactivated Donors - Current Period
    q3_current = f"""
        SELECT COUNT(DISTINCT g.donor_id) as reactivated_donors, SUM(g.amount) as reactivated_amount
        FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
        WHERE g.gift_date BETWEEN '{current_start}' AND '{current_end}'
        AND {INDIVIDUAL_DONOR_BASE_FILTER}
        AND NOT EXISTS (SELECT 1 FROM dpgift g2 WHERE g2.donor_id = g.donor_id AND g2.gift_date BETWEEN '{prior_start}' AND '{prior_end}')
        AND EXISTS (SELECT 1 FROM dpgift g3 WHERE g3.donor_id = g.donor_id AND g3.gift_date < '{prior_start}')
    """
    r3_current = execute_query(q3_current, 'current_reactivated')
    current_reactivated = r3_current[0] if r3_current else {}

    # Query 4: Upgraded Donors - Current Period
    q4_current = f"""
        SELECT COUNT(DISTINCT curr.donor_id) as upgraded_donors, SUM(curr.total) as upgrade_revenue
        FROM (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
              WHERE g.gift_date BETWEEN '{current_start}' AND '{current_end}' AND {INDIVIDUAL_DONOR_BASE_FILTER} GROUP BY g.donor_id) curr
        INNER JOIN (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
              WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}' AND {INDIVIDUAL_DONOR_BASE_FILTER} GROUP BY g.donor_id) prev
        ON curr.donor_id = prev.donor_id WHERE curr.total > prev.total
    """
    r4_current = execute_query(q4_current, 'current_upgraded')
    current_upgraded = r4_current[0] if r4_current else {}

    # Query 5: Same Donors - Current Period
    q5_current = f"""
        SELECT COUNT(DISTINCT curr.donor_id) as same_donors, SUM(curr.total) as same_revenue
        FROM (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
              WHERE g.gift_date BETWEEN '{current_start}' AND '{current_end}' AND {INDIVIDUAL_DONOR_BASE_FILTER} GROUP BY g.donor_id) curr
        INNER JOIN (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
              WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}' AND {INDIVIDUAL_DONOR_BASE_FILTER} GROUP BY g.donor_id) prev
        ON curr.donor_id = prev.donor_id WHERE curr.total = prev.total
    """
    r5_current = execute_query(q5_current, 'current_same')
    current_same = r5_current[0] if r5_current else {}

    # Query 6: Downgraded Donors - Current Period
    q6_current = f"""
        SELECT COUNT(DISTINCT curr.donor_id) as downgraded_donors, SUM(curr.total) as downgrade_revenue
        FROM (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
              WHERE g.gift_date BETWEEN '{current_start}' AND '{current_end}' AND {INDIVIDUAL_DONOR_BASE_FILTER} GROUP BY g.donor_id) curr
        INNER JOIN (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
              WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}' AND {INDIVIDUAL_DONOR_BASE_FILTER} GROUP BY g.donor_id) prev
        ON curr.donor_id = prev.donor_id WHERE curr.total < prev.total
    """
    r6_current = execute_query(q6_current, 'current_downgraded')
    current_downgraded = r6_current[0] if r6_current else {}

    # -------------------------------------------------------------------------
    # PRIOR PERIOD METRICS (need prior-prior period for comparison)
    # -------------------------------------------------------------------------

    # Calculate prior-prior period (one year before prior period)
    from datetime import datetime
    prior_start_dt = datetime.strptime(prior_start, '%Y-%m-%d')
    prior_end_dt = datetime.strptime(prior_end, '%Y-%m-%d')
    prior_prior_start = (prior_start_dt - relativedelta(years=1)).strftime('%Y-%m-%d')
    prior_prior_end = (prior_end_dt - relativedelta(years=1)).strftime('%Y-%m-%d')

    # Query 1: Total Revenue, Gift Count, Largest Gift - Prior Period
    q1_prior = f"""
        SELECT SUM(g.amount) as total_revenue, COUNT(*) as gift_count, MAX(g.amount) as largest_gift
        FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
        WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}'
        AND {INDIVIDUAL_DONOR_BASE_FILTER}
    """
    r1_prior = execute_query(q1_prior, 'prior_totals')
    prior_totals = r1_prior[0] if r1_prior else {}

    # Query 2: New Donors - Prior Period
    q2_prior = f"""
        SELECT COUNT(DISTINCT g.donor_id) as new_donors, SUM(g.amount) as new_donor_amount
        FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
        WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}'
        AND {INDIVIDUAL_DONOR_BASE_FILTER}
        AND NOT EXISTS (SELECT 1 FROM dpgift g2 WHERE g2.donor_id = g.donor_id AND g2.gift_date < '{prior_start}')
    """
    r2_prior = execute_query(q2_prior, 'prior_new_donors')
    prior_new = r2_prior[0] if r2_prior else {}

    # Query 3: Reactivated Donors - Prior Period
    q3_prior = f"""
        SELECT COUNT(DISTINCT g.donor_id) as reactivated_donors, SUM(g.amount) as reactivated_amount
        FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
        WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}'
        AND {INDIVIDUAL_DONOR_BASE_FILTER}
        AND NOT EXISTS (SELECT 1 FROM dpgift g2 WHERE g2.donor_id = g.donor_id AND g2.gift_date BETWEEN '{prior_prior_start}' AND '{prior_prior_end}')
        AND EXISTS (SELECT 1 FROM dpgift g3 WHERE g3.donor_id = g.donor_id AND g3.gift_date < '{prior_prior_start}')
    """
    r3_prior = execute_query(q3_prior, 'prior_reactivated')
    prior_reactivated = r3_prior[0] if r3_prior else {}

    # Query 4: Upgraded Donors - Prior Period
    q4_prior = f"""
        SELECT COUNT(DISTINCT curr.donor_id) as upgraded_donors, SUM(curr.total) as upgrade_revenue
        FROM (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
              WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}' AND {INDIVIDUAL_DONOR_BASE_FILTER} GROUP BY g.donor_id) curr
        INNER JOIN (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
              WHERE g.gift_date BETWEEN '{prior_prior_start}' AND '{prior_prior_end}' AND {INDIVIDUAL_DONOR_BASE_FILTER} GROUP BY g.donor_id) prev
        ON curr.donor_id = prev.donor_id WHERE curr.total > prev.total
    """
    r4_prior = execute_query(q4_prior, 'prior_upgraded')
    prior_upgraded = r4_prior[0] if r4_prior else {}

    # Query 5: Same Donors - Prior Period
    q5_prior = f"""
        SELECT COUNT(DISTINCT curr.donor_id) as same_donors, SUM(curr.total) as same_revenue
        FROM (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
              WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}' AND {INDIVIDUAL_DONOR_BASE_FILTER} GROUP BY g.donor_id) curr
        INNER JOIN (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
              WHERE g.gift_date BETWEEN '{prior_prior_start}' AND '{prior_prior_end}' AND {INDIVIDUAL_DONOR_BASE_FILTER} GROUP BY g.donor_id) prev
        ON curr.donor_id = prev.donor_id WHERE curr.total = prev.total
    """
    r5_prior = execute_query(q5_prior, 'prior_same')
    prior_same = r5_prior[0] if r5_prior else {}

    # Query 6: Downgraded Donors - Prior Period
    q6_prior = f"""
        SELECT COUNT(DISTINCT curr.donor_id) as downgraded_donors, SUM(curr.total) as downgrade_revenue
        FROM (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
              WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}' AND {INDIVIDUAL_DONOR_BASE_FILTER} GROUP BY g.donor_id) curr
        INNER JOIN (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id
              WHERE g.gift_date BETWEEN '{prior_prior_start}' AND '{prior_prior_end}' AND {INDIVIDUAL_DONOR_BASE_FILTER} GROUP BY g.donor_id) prev
        ON curr.donor_id = prev.donor_id WHERE curr.total < prev.total
    """
    r6_prior = execute_query(q6_prior, 'prior_downgraded')
    prior_downgraded = r6_prior[0] if r6_prior else {}

    return {
        'current': {
            'total_revenue': safe_float(current_totals.get('total_revenue')),
            'gift_count': safe_int(current_totals.get('gift_count')),
            'largest_gift': safe_float(current_totals.get('largest_gift')),
            'new_donors': safe_int(current_new.get('new_donors')),
            'new_donor_amount': safe_float(current_new.get('new_donor_amount')),
            'reactivated_donors': safe_int(current_reactivated.get('reactivated_donors')),
            'reactivated_amount': safe_float(current_reactivated.get('reactivated_amount')),
            'upgraded_donors': safe_int(current_upgraded.get('upgraded_donors')),
            'upgrade_revenue': safe_float(current_upgraded.get('upgrade_revenue')),
            'same_donors': safe_int(current_same.get('same_donors')),
            'same_revenue': safe_float(current_same.get('same_revenue')),
            'downgraded_donors': safe_int(current_downgraded.get('downgraded_donors')),
            'downgrade_revenue': safe_float(current_downgraded.get('downgrade_revenue')),
        },
        'prior': {
            'total_revenue': safe_float(prior_totals.get('total_revenue')),
            'gift_count': safe_int(prior_totals.get('gift_count')),
            'largest_gift': safe_float(prior_totals.get('largest_gift')),
            'new_donors': safe_int(prior_new.get('new_donors')),
            'new_donor_amount': safe_float(prior_new.get('new_donor_amount')),
            'reactivated_donors': safe_int(prior_reactivated.get('reactivated_donors')),
            'reactivated_amount': safe_float(prior_reactivated.get('reactivated_amount')),
            'upgraded_donors': safe_int(prior_upgraded.get('upgraded_donors')),
            'upgrade_revenue': safe_float(prior_upgraded.get('upgrade_revenue')),
            'same_donors': safe_int(prior_same.get('same_donors')),
            'same_revenue': safe_float(prior_same.get('same_revenue')),
            'downgraded_donors': safe_int(prior_downgraded.get('downgraded_donors')),
            'downgrade_revenue': safe_float(prior_downgraded.get('downgrade_revenue')),
        },
        'debug': debug_info
    }


@st.cache_data(ttl=86400, show_spinner=False)  # Cache for 24 hours
def load_donor_metrics_by_type(
    current_start: str,
    current_end: str,
    prior_start: str,
    prior_end: str,
    base_filter: str,
    type_name: str
) -> dict:
    """Load donor metrics from DonorPerfect for a specific donor type.

    Args:
        current_start: Start date of current period (YYYY-MM-DD)
        current_end: End date of current period (YYYY-MM-DD)
        prior_start: Start date of prior period (YYYY-MM-DD)
        prior_end: End date of prior period (YYYY-MM-DD)
        base_filter: SQL filter for donor type (e.g., INDIVIDUAL_DONOR_BASE_FILTER)
        type_name: Name of donor type for debug logging

    Returns:
        Dictionary with metrics for both periods
    """
    debug_info = {'queries': [], 'type': type_name}

    def execute_query(query: str, name: str) -> list:
        try:
            url = f"{DONORPERFECT_BASE_URL}?apikey={DONORPERFECT_API_KEY}&action={quote(query)}"
            response = requests.get(url, timeout=120)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            records = []
            for rec in root.findall('.//record'):
                record = {}
                for field in rec.findall('field'):
                    record[field.get('name')] = field.get('value')
                records.append(record)
            debug_info['queries'].append({'name': name, 'records': len(records)})
            return records
        except Exception as e:
            debug_info['queries'].append({'name': name, 'error': str(e)})
            return []

    def safe_float(val):
        try:
            return float(val) if val else 0.0
        except:
            return 0.0

    def safe_int(val):
        try:
            return int(val) if val else 0
        except:
            return 0

    # Calculate prior-prior period
    from datetime import datetime
    prior_start_dt = datetime.strptime(prior_start, '%Y-%m-%d')
    prior_end_dt = datetime.strptime(prior_end, '%Y-%m-%d')
    prior_prior_start = (prior_start_dt - relativedelta(years=1)).strftime('%Y-%m-%d')
    prior_prior_end = (prior_end_dt - relativedelta(years=1)).strftime('%Y-%m-%d')

    # CURRENT PERIOD QUERIES
    r1_curr = execute_query(f"SELECT SUM(g.amount) as total_revenue, COUNT(*) as gift_count, MAX(g.amount) as largest_gift FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{current_start}' AND '{current_end}' AND {base_filter}", f'{type_name}_curr_totals')
    r2_curr = execute_query(f"SELECT COUNT(DISTINCT g.donor_id) as new_donors, SUM(g.amount) as new_donor_amount FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{current_start}' AND '{current_end}' AND {base_filter} AND NOT EXISTS (SELECT 1 FROM dpgift g2 WHERE g2.donor_id = g.donor_id AND g2.gift_date < '{current_start}')", f'{type_name}_curr_new')
    r3_curr = execute_query(f"SELECT COUNT(DISTINCT g.donor_id) as reactivated_donors, SUM(g.amount) as reactivated_amount FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{current_start}' AND '{current_end}' AND {base_filter} AND NOT EXISTS (SELECT 1 FROM dpgift g2 WHERE g2.donor_id = g.donor_id AND g2.gift_date BETWEEN '{prior_start}' AND '{prior_end}') AND EXISTS (SELECT 1 FROM dpgift g3 WHERE g3.donor_id = g.donor_id AND g3.gift_date < '{prior_start}')", f'{type_name}_curr_react')
    r4_curr = execute_query(f"SELECT COUNT(DISTINCT curr.donor_id) as upgraded_donors, SUM(curr.total) as upgrade_revenue FROM (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{current_start}' AND '{current_end}' AND {base_filter} GROUP BY g.donor_id) curr INNER JOIN (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}' AND {base_filter} GROUP BY g.donor_id) prev ON curr.donor_id = prev.donor_id WHERE curr.total > prev.total", f'{type_name}_curr_up')
    r5_curr = execute_query(f"SELECT COUNT(DISTINCT curr.donor_id) as same_donors, SUM(curr.total) as same_revenue FROM (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{current_start}' AND '{current_end}' AND {base_filter} GROUP BY g.donor_id) curr INNER JOIN (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}' AND {base_filter} GROUP BY g.donor_id) prev ON curr.donor_id = prev.donor_id WHERE curr.total = prev.total", f'{type_name}_curr_same')
    r6_curr = execute_query(f"SELECT COUNT(DISTINCT curr.donor_id) as downgraded_donors, SUM(curr.total) as downgrade_revenue FROM (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{current_start}' AND '{current_end}' AND {base_filter} GROUP BY g.donor_id) curr INNER JOIN (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}' AND {base_filter} GROUP BY g.donor_id) prev ON curr.donor_id = prev.donor_id WHERE curr.total < prev.total", f'{type_name}_curr_down')

    # PRIOR PERIOD QUERIES
    r1_prior = execute_query(f"SELECT SUM(g.amount) as total_revenue, COUNT(*) as gift_count, MAX(g.amount) as largest_gift FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}' AND {base_filter}", f'{type_name}_prior_totals')
    r2_prior = execute_query(f"SELECT COUNT(DISTINCT g.donor_id) as new_donors, SUM(g.amount) as new_donor_amount FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}' AND {base_filter} AND NOT EXISTS (SELECT 1 FROM dpgift g2 WHERE g2.donor_id = g.donor_id AND g2.gift_date < '{prior_start}')", f'{type_name}_prior_new')
    r3_prior = execute_query(f"SELECT COUNT(DISTINCT g.donor_id) as reactivated_donors, SUM(g.amount) as reactivated_amount FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}' AND {base_filter} AND NOT EXISTS (SELECT 1 FROM dpgift g2 WHERE g2.donor_id = g.donor_id AND g2.gift_date BETWEEN '{prior_prior_start}' AND '{prior_prior_end}') AND EXISTS (SELECT 1 FROM dpgift g3 WHERE g3.donor_id = g.donor_id AND g3.gift_date < '{prior_prior_start}')", f'{type_name}_prior_react')
    r4_prior = execute_query(f"SELECT COUNT(DISTINCT curr.donor_id) as upgraded_donors, SUM(curr.total) as upgrade_revenue FROM (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}' AND {base_filter} GROUP BY g.donor_id) curr INNER JOIN (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{prior_prior_start}' AND '{prior_prior_end}' AND {base_filter} GROUP BY g.donor_id) prev ON curr.donor_id = prev.donor_id WHERE curr.total > prev.total", f'{type_name}_prior_up')
    r5_prior = execute_query(f"SELECT COUNT(DISTINCT curr.donor_id) as same_donors, SUM(curr.total) as same_revenue FROM (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}' AND {base_filter} GROUP BY g.donor_id) curr INNER JOIN (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{prior_prior_start}' AND '{prior_prior_end}' AND {base_filter} GROUP BY g.donor_id) prev ON curr.donor_id = prev.donor_id WHERE curr.total = prev.total", f'{type_name}_prior_same')
    r6_prior = execute_query(f"SELECT COUNT(DISTINCT curr.donor_id) as downgraded_donors, SUM(curr.total) as downgrade_revenue FROM (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{prior_start}' AND '{prior_end}' AND {base_filter} GROUP BY g.donor_id) curr INNER JOIN (SELECT g.donor_id, SUM(g.amount) as total FROM dpgift g INNER JOIN dp d ON g.donor_id = d.donor_id WHERE g.gift_date BETWEEN '{prior_prior_start}' AND '{prior_prior_end}' AND {base_filter} GROUP BY g.donor_id) prev ON curr.donor_id = prev.donor_id WHERE curr.total < prev.total", f'{type_name}_prior_down')

    curr_totals = r1_curr[0] if r1_curr else {}
    curr_new = r2_curr[0] if r2_curr else {}
    curr_react = r3_curr[0] if r3_curr else {}
    curr_up = r4_curr[0] if r4_curr else {}
    curr_same = r5_curr[0] if r5_curr else {}
    curr_down = r6_curr[0] if r6_curr else {}

    prior_totals = r1_prior[0] if r1_prior else {}
    prior_new = r2_prior[0] if r2_prior else {}
    prior_react = r3_prior[0] if r3_prior else {}
    prior_up = r4_prior[0] if r4_prior else {}
    prior_same = r5_prior[0] if r5_prior else {}
    prior_down = r6_prior[0] if r6_prior else {}

    return {
        'current': {
            'total_revenue': safe_float(curr_totals.get('total_revenue')),
            'gift_count': safe_int(curr_totals.get('gift_count')),
            'largest_gift': safe_float(curr_totals.get('largest_gift')),
            'new_donors': safe_int(curr_new.get('new_donors')),
            'new_donor_amount': safe_float(curr_new.get('new_donor_amount')),
            'reactivated_donors': safe_int(curr_react.get('reactivated_donors')),
            'reactivated_amount': safe_float(curr_react.get('reactivated_amount')),
            'upgraded_donors': safe_int(curr_up.get('upgraded_donors')),
            'upgrade_revenue': safe_float(curr_up.get('upgrade_revenue')),
            'same_donors': safe_int(curr_same.get('same_donors')),
            'same_revenue': safe_float(curr_same.get('same_revenue')),
            'downgraded_donors': safe_int(curr_down.get('downgraded_donors')),
            'downgrade_revenue': safe_float(curr_down.get('downgrade_revenue')),
        },
        'prior': {
            'total_revenue': safe_float(prior_totals.get('total_revenue')),
            'gift_count': safe_int(prior_totals.get('gift_count')),
            'largest_gift': safe_float(prior_totals.get('largest_gift')),
            'new_donors': safe_int(prior_new.get('new_donors')),
            'new_donor_amount': safe_float(prior_new.get('new_donor_amount')),
            'reactivated_donors': safe_int(prior_react.get('reactivated_donors')),
            'reactivated_amount': safe_float(prior_react.get('reactivated_amount')),
            'upgraded_donors': safe_int(prior_up.get('upgraded_donors')),
            'upgrade_revenue': safe_float(prior_up.get('upgrade_revenue')),
            'same_donors': safe_int(prior_same.get('same_donors')),
            'same_revenue': safe_float(prior_same.get('same_revenue')),
            'downgraded_donors': safe_int(prior_down.get('downgraded_donors')),
            'downgrade_revenue': safe_float(prior_down.get('downgrade_revenue')),
        },
        'debug': debug_info
    }


def get_donor_comparison_metrics() -> dict:
    """Get donor comparison metrics for Individuals, Organizations, and Total.

    Returns:
        Dictionary with metrics for all three donor types plus labels
    """
    today = date.today()
    fy_info = get_fiscal_year_info(today)

    # Current fiscal year: FY start to today
    current_fy_start = fy_info['current_fy_start'].strftime("%Y-%m-%d")
    current_fy_end = today.strftime("%Y-%m-%d")

    # Prior fiscal year to same date: Prior FY start to same date last year
    prior_fy_start = fy_info['prior_fy_start'].strftime("%Y-%m-%d")
    prior_fy_end = today.replace(year=today.year - 1).strftime("%Y-%m-%d")

    # Labels for display
    current_label = fy_info['current_fy_short']
    prior_label = fy_info['prior_fy_short']

    # Load metrics for each donor type
    individuals = load_donor_metrics_by_type(
        current_fy_start, current_fy_end, prior_fy_start, prior_fy_end,
        INDIVIDUAL_DONOR_BASE_FILTER, 'individual'
    )

    organizations = load_donor_metrics_by_type(
        current_fy_start, current_fy_end, prior_fy_start, prior_fy_end,
        ORGANIZATION_DONOR_BASE_FILTER, 'organization'
    )

    # Total is sum of individuals + organizations (calculated, not queried separately)
    def sum_metrics(ind: dict, org: dict) -> dict:
        return {
            'total_revenue': ind['total_revenue'] + org['total_revenue'],
            'gift_count': ind['gift_count'] + org['gift_count'],
            'largest_gift': max(ind['largest_gift'], org['largest_gift']),
            'new_donors': ind['new_donors'] + org['new_donors'],
            'new_donor_amount': ind['new_donor_amount'] + org['new_donor_amount'],
            'reactivated_donors': ind['reactivated_donors'] + org['reactivated_donors'],
            'reactivated_amount': ind['reactivated_amount'] + org['reactivated_amount'],
            'upgraded_donors': ind['upgraded_donors'] + org['upgraded_donors'],
            'upgrade_revenue': ind['upgrade_revenue'] + org['upgrade_revenue'],
            'same_donors': ind['same_donors'] + org['same_donors'],
            'same_revenue': ind['same_revenue'] + org['same_revenue'],
            'downgraded_donors': ind['downgraded_donors'] + org['downgraded_donors'],
            'downgrade_revenue': ind['downgrade_revenue'] + org['downgrade_revenue'],
        }

    total_current = sum_metrics(individuals['current'], organizations['current'])
    total_prior = sum_metrics(individuals['prior'], organizations['prior'])

    return {
        'individuals': individuals,
        'organizations': organizations,
        'total': {'current': total_current, 'prior': total_prior},
        'current_fy_short': current_label,
        'prior_fy_short': prior_label,
        'current_dates': f"{current_fy_start} to {current_fy_end}",
        'prior_dates': f"{prior_fy_start} to {prior_fy_end}",
    }


def get_individual_metrics_comparison() -> dict:
    """Get Individual donor metrics for current FY vs prior FY to date.

    DEPRECATED: Use get_donor_comparison_metrics() instead for all donor types.

    Returns:
        Dictionary with current and prior FY metrics plus labels
    """
    today = date.today()
    fy_info = get_fiscal_year_info(today)

    # Current fiscal year: FY start to today
    current_fy_start = fy_info['current_fy_start'].strftime("%Y-%m-%d")
    current_fy_end = today.strftime("%Y-%m-%d")

    # Prior fiscal year to same date: Prior FY start to same date last year
    prior_fy_start = fy_info['prior_fy_start'].strftime("%Y-%m-%d")
    prior_fy_end = today.replace(year=today.year - 1).strftime("%Y-%m-%d")

    # Load metrics
    metrics = load_individual_donor_metrics(
        current_fy_start, current_fy_end,
        prior_fy_start, prior_fy_end
    )

    return {
        'current': metrics['current'],
        'prior': metrics['prior'],
        'current_fy_short': fy_info['current_fy_short'],
        'prior_fy_short': fy_info['prior_fy_short'],
        'current_dates': f"{current_fy_start} to {current_fy_end}",
        'prior_dates': f"{prior_fy_start} to {prior_fy_end}",
        'debug': metrics.get('debug', {})
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


def render_hero_header(processor: DataProcessor, activity_records: list = None, partners_data: list = None, start_date: date = None, end_date: date = None):
    """Render the hero header with key stats."""
    stats = processor.get_summary_stats()
    # Use _books_distributed_all for total (includes books to previously served children)
    books = int(stats.get("totals", {}).get("_books_distributed_all", 0) or stats.get("totals", {}).get("_of_books_distributed", 0))
    children = int(stats.get("totals", {}).get("total_children", 0))
    parents = int(stats.get("totals", {}).get("parents_or_caregivers", 0))

    # Calculate average % low income children served from partners in date range
    low_income_pct = 0.0
    if activity_records and partners_data and start_date and end_date:
        # Build partner ID to percentage_lowincome mapping
        partner_low_income = {}
        for partner in partners_data:
            pid = partner.get('id', '')
            pct = partner.get('percentage_lowincome', None)
            if pid and pct is not None:
                try:
                    if isinstance(pct, list):
                        pct = pct[0] if pct else None
                    if pct is not None:
                        partner_low_income[pid] = float(pct)
                except (ValueError, TypeError):
                    pass

        # Filter activity records by date range and collect low income percentages
        low_income_values = []
        for record in activity_records:
            # Check date range
            record_date = record.get('date_of_activity') or record.get('date')
            if record_date:
                try:
                    record_dt = pd.to_datetime(record_date)
                    if not (pd.Timestamp(start_date) <= record_dt <= pd.Timestamp(end_date)):
                        continue
                except:
                    continue
            else:
                continue

            # For legacy records, use percentage_low_income directly from the record
            if record.get('_is_legacy'):
                pct = record.get('percentage_low_income')
                if pct is not None:
                    try:
                        if isinstance(pct, list):
                            pct = pct[0] if pct else None
                        if pct is not None:
                            low_income_values.append(float(pct))
                    except (ValueError, TypeError):
                        pass
                continue

            # For current records, get partner ID and look up low income percentage from partners table
            partner_id = record.get('partners_testing', '')
            if isinstance(partner_id, list):
                partner_id = partner_id[0] if partner_id else ''
            if partner_id and partner_id in partner_low_income:
                low_income_values.append(partner_low_income[partner_id])

        # Calculate average
        if low_income_values:
            low_income_pct = sum(low_income_values) / len(low_income_values)

    # Get current fiscal year for display
    fy_info = get_fiscal_year_info(date.today())
    current_fy = fy_info['current_fy_short']

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
        color: #1e40af;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0.75rem 0 0 0;
        background: linear-gradient(90deg, #fef3c7 0%, #fde68a 50%, #fef3c7 100%);
        padding: 0.35rem 0.75rem;
        border-radius: 6px;
        display: inline-block;
        animation: pulse-highlight 2s ease-in-out infinite;
    }
    @keyframes pulse-highlight {
        0%, 100% { box-shadow: 0 0 0 0 rgba(251, 191, 36, 0.4); }
        50% { box-shadow: 0 0 0 8px rgba(251, 191, 36, 0); }
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="hero-box">
        <div style="display: flex; align-items: center; justify-content: center; gap: 0.75rem;">
            <span style="font-size: 2rem;">📚</span>
            <div style="text-align: left;">
                <h1 class="hero-title">BookSpring Strategic Dashboard</h1>
                <p class="hero-subtitle">Tracking Progress Toward 2025-2030 Strategic Goals</p>
                <p class="hero-date">Currently tracking {current_fy} · See date range in sidebar</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Summary metrics in styled boxes - centered
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 1rem auto 2rem auto; max-width: 1100px;">
        <div class="metric-card" style="text-align: center; padding: 1.25rem;">
            <div style="font-size: 0.85rem; color: #718096; margin-bottom: 0.5rem;">📚 Books Distributed</div>
            <div style="font-size: 1.75rem; font-weight: 700; color: #1a365d;">{books:,}</div>
        </div>
        <div class="metric-card" style="text-align: center; padding: 1.25rem;">
            <div style="font-size: 0.85rem; color: #718096; margin-bottom: 0.5rem;">👶 Children Served</div>
            <div style="font-size: 1.75rem; font-weight: 700; color: #1a365d;">{children:,}</div>
        </div>
        <div class="metric-card" style="text-align: center; padding: 1.25rem;">
            <div style="font-size: 0.85rem; color: #718096; margin-bottom: 0.5rem;">📊 % in Low Income Settings</div>
            <div style="font-size: 1.75rem; font-weight: 700; color: #1a365d;">{low_income_pct:.1f}%</div>
        </div>
        <div class="metric-card" style="text-align: center; padding: 1.25rem;">
            <div style="font-size: 0.85rem; color: #718096; margin-bottom: 0.5rem;">👨‍👩‍👧 Parents/Caregivers</div>
            <div style="font-size: 1.75rem; font-weight: 700; color: #1a365d;">{parents:,}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_print_snapshot(processor: DataProcessor, views_data: list, books_data: list, start_date: date, end_date: date):
    """Render the one-page print snapshot of all four goals."""
    stats = processor.get_summary_stats()
    # Use _books_distributed_all for total (includes books to previously served children)
    books = int(stats.get("totals", {}).get("_books_distributed_all", 0) or stats.get("totals", {}).get("_of_books_distributed", 0))
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

    # Calculate avg books/child: ALL books / unique children
    # Use _books_distributed_all for total books (includes books to previously served children)
    if "_books_distributed_all" in processor.df.columns:
        total_books = processor.df["_books_distributed_all"].sum()
    else:
        total_books = processor.df["_of_books_distributed"].sum() if "_of_books_distributed" in processor.df.columns else 0
    # Use sum of age columns for children count (excludes previously served)
    age_cols = ["children_035_months", "children_03_years", "children_35_years", "children_34_years",
                "children_68_years", "children_512_years", "children_912_years", "teens"]
    available_age_cols = [c for c in age_cols if c in processor.df.columns]
    total_children = processor.df[available_age_cols].fillna(0).sum().sum() if available_age_cols else 0
    avg_overall = total_books / total_children if total_children > 0 else 0
    target = 4.0
    pct = (avg_overall / target * 100) if target > 0 else 0

    # Row 1: Ring + Overall Trend
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("<p style='text-align: center; font-weight: 600; color: #1a365d; font-size: 0.9rem; margin-bottom: -10px;'>Avg Books/Child</p>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.75rem; margin-bottom: -10px;'>(in date range)</p>", unsafe_allow_html=True)

        # Create progress ring
        display_pct = min(pct, 100)
        remaining_pct = max(100 - display_pct, 0)
        fig = go.Figure(data=[go.Pie(
            values=[display_pct, remaining_pct],
            hole=0.7,
            marker=dict(colors=['#667eea', '#e2e8f0']),
            textinfo='none',
            hoverinfo='skip',
            sort=False
        )])
        fig.update_layout(
            showlegend=False,
            margin=dict(t=30, b=30, l=10, r=10),
            height=230,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            annotations=[
                dict(
                    text=f"<b>{avg_overall:.2f}</b>",
                    x=0.5, y=0.55,
                    font=dict(size=24, color='#1a365d', family='system-ui'),
                    showarrow=False
                ),
                dict(
                    text=f"{pct:.0f}% of goal",
                    x=0.5, y=0.38,
                    font=dict(size=12, color='#64748b', family='system-ui'),
                    showarrow=False
                )
            ]
        )
        st.plotly_chart(fig, use_container_width=True, key="goal1_ring")
        st.markdown(f"<p style='text-align: center; margin-top: -20px; color: #1a365d; font-size: 0.9rem; font-weight: 700;'>2030 Target: 4.0 books/child</p>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #718096; font-size: 0.7rem; margin-top: 0.25rem;'>Includes all books given to each unique child this year</p>", unsafe_allow_html=True)

    with col2:
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

    st.markdown("<br>", unsafe_allow_html=True)

    # Row 2: By Age Group trend (full width)
    st.markdown("##### By Age Group <span style='font-weight: normal; font-size: 0.7rem; color: #718096;'>(click legend to toggle)</span>", unsafe_allow_html=True)
    age_metrics = ["books_per_child_0_2", "books_per_child_3_5",
                   "books_per_child_6_8", "books_per_child_9_12", "books_per_child_teens"]
    available_age = [m for m in age_metrics if m in processor.df.columns]

    if available_age:
        trend_df = processor.aggregate_by_time(time_unit, available_age)
        if not trend_df.empty:
            # Shorten legend names for space
            short_names = {
                "books_per_child_0_2": "0-2 yrs",
                "books_per_child_3_5": "3-5 yrs",
                "books_per_child_6_8": "6-8 yrs",
                "books_per_child_9_12": "9-12 yrs",
                "books_per_child_teens": "Teens",
            }
            rename_map = {c: short_names.get(c, c) for c in trend_df.columns if c != "period"}
            trend_df = trend_df.rename(columns=rename_map)

            # Better color palette for age groups
            age_colors = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444"]
            fig = px.line(
                trend_df,
                x="period",
                y=[short_names.get(m, m) for m in available_age],
                markers=True,
                color_discrete_sequence=age_colors
            )
            fig.add_hline(y=4.0, line_dash="dash", line_color="#22c55e",
                         annotation_text="Target", annotation_font_color="#22c55e")
            fig = style_plotly_chart(fig, height=280)
            # Use same Y-axis scale as overall trend (0 to 5)
            numeric_cols = [short_names.get(m, m) for m in available_age]
            y_max = max(5, trend_df[numeric_cols].max().max() + 0.5)
            fig.update_layout(
                yaxis_title="Books/Child",
                xaxis_title="",
                yaxis=dict(range=[0, y_max], dtick=0.5, gridcolor='#e5e7eb'),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="left",
                    x=0,
                    font=dict(size=10)
                )
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("<p style='font-size: 0.85rem; color: #718096; text-decoration: underline; text-align: center;'>Both trends count only first-time visits each period — a conservative measure toward our stretch goal of 4 books/child</p>", unsafe_allow_html=True)


def render_goal2_inspire_engagement(views_data: list, time_unit: str, start_date: date, end_date: date, enrollment_count: int = 0, book_bank_children: int = 0, inperson_events: int = 0, activity_records: list = None, partners_data: list = None, low_income_pct: float = 0.0):
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
        partner_items = [f"<span style='background: #fce7f3; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.65rem; color: #9d174d; white-space: nowrap;'>{name}</span>" for name in sorted(inperson_event_partners)]
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
            <div style="margin-top: 0.6rem; display: flex; flex-wrap: wrap; gap: 0.3rem;">{inperson_partners_html if inperson_partners_html else ''}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Recurring Partners box (below In-Person Events) - show ALL recurring partners
    all_partners_html = ""
    if recurring_partners:
        partner_items = []
        for pid, count in recurring_partners:
            name = partner_names.get(pid, pid[:12] + '...')
            partner_items.append(f"<span style='background: #d1fae5; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.7rem; color: #065f46; white-space: nowrap;'>{name} <strong>({count})</strong></span>")
        all_partners_html = " ".join(partner_items)

    st.markdown(f"""
    <div style="display: flex; align-items: flex-start; gap: 1.5rem; margin-bottom: 1.5rem; padding: 1.5rem 1.75rem; background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); border: 1px solid #bbf7d0; border-radius: 16px; min-height: 140px;">
        <div style="width: 90px; height: 90px; background: linear-gradient(135deg, #4ade80 0%, #22c55e 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 14px rgba(34, 197, 94, 0.4); flex-shrink: 0;">
            <span style="font-size: 2rem; font-weight: 800; color: white;">{recurring_count:,}</span>
        </div>
        <div style="flex: 1; min-width: 0;">
            <p style="font-size: 1.15rem; font-weight: 700; color: #1a202c; margin: 0;">Recurring Partners</p>
            <p style="font-size: 0.85rem; color: #6b7280; margin: 0.25rem 0 0 0;">(2+ activities in date range)</p>
            <div style="margin-top: 0.75rem; display: flex; flex-wrap: wrap; gap: 0.35rem; line-height: 1.6;">{all_partners_html if all_partners_html else '<span style="font-size: 0.75rem; color: #9ca3af;">No recurring partners in date range</span>'}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Process digital views data first
    digital_views = 0
    newsletter_views = 0
    total_views = 0
    target_views = 1_500_000

    if views_data:
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
        if "total_digital_views" in df.columns:
            df["total_digital_views"] = pd.to_numeric(df["total_digital_views"], errors='coerce').fillna(0)
            digital_views = df["total_digital_views"].sum()
        if "total_newsletter_views" in df.columns:
            df["total_newsletter_views"] = pd.to_numeric(df["total_newsletter_views"], errors='coerce').fillna(0)
            newsletter_views = df["total_newsletter_views"].sum()

        total_views = digital_views + newsletter_views

    # Program Reach Section - All three rings in one row
    st.markdown("##### 🏠 Program Reach & Digital Engagement")

    home_target = 25_000
    home_pct = (enrollment_count / home_target * 100) if home_target > 0 else 0

    book_bank_target = 55_000
    book_bank_pct = (book_bank_children / book_bank_target * 100) if book_bank_target > 0 else 0

    digital_pct = (total_views / target_views * 100) if target_views > 0 else 0

    def create_count_ring(count, target, pct, color_fill, is_large_number=False):
        """Create a donut chart showing progress toward target."""
        display_pct = min(pct, 100)
        remaining_pct = max(100 - display_pct, 0)

        fig = go.Figure(data=[go.Pie(
            values=[display_pct, remaining_pct],
            hole=0.7,
            marker=dict(colors=[color_fill, '#e2e8f0']),
            textinfo='none',
            hoverinfo='skip',
            sort=False
        )])

        # Format count
        if is_large_number and count >= 1000000:
            count_str = f"{count/1000000:.1f}M"
        elif count >= 1000:
            count_str = f"{count/1000:.1f}K"
        else:
            count_str = f"{count:,}"

        # Format target
        if target >= 1000000:
            target_str = f"{target/1000000:.1f}M"
        elif target >= 1000:
            target_str = f"{target/1000:.0f}K"
        else:
            target_str = f"{target:,}"

        fig.update_layout(
            showlegend=False,
            margin=dict(t=30, b=30, l=10, r=10),
            height=230,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            annotations=[
                dict(
                    text=f"<b>{count_str}</b>",
                    x=0.5, y=0.55,
                    font=dict(size=22, color='#1a365d', family='system-ui'),
                    showarrow=False
                ),
                dict(
                    text=f"{pct:.0f}% of goal",
                    x=0.5, y=0.38,
                    font=dict(size=12, color='#64748b', family='system-ui'),
                    showarrow=False
                )
            ]
        )
        return fig, target_str

    # All three rings with stats: Home Delivery + Low Income | Book Bank | Digital Engagement | Digital Stats
    col1, col1b, col2, col3, col4 = st.columns([1, 0.5, 1, 1, 0.8])

    with col1:
        st.markdown("<p style='text-align: center; font-weight: 600; color: #1a365d; font-size: 0.85rem; margin-bottom: -10px;'>B3 In-Home Delivery</p>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.7rem; margin-bottom: -10px;'>Active Enrollments</p>", unsafe_allow_html=True)
        fig, target_str = create_count_ring(enrollment_count, home_target, home_pct, '#3182ce')
        st.plotly_chart(fig, use_container_width=True, key="home_delivery_ring")
        st.markdown(f"<p style='text-align: center; margin-top: -20px; color: #1a365d; font-size: 0.85rem; font-weight: 700;'>2030 Target: {target_str} families</p>", unsafe_allow_html=True)

    with col1b:
        # % in Low Income Settings box aligned next to ring
        st.markdown(f"""
            <div style="display: flex; align-items: center; justify-content: center; height: 100%; padding-top: 2rem;">
                <div class="metric-card" style="text-align: center; padding: 0.75rem;">
                    <div style="font-size: 0.7rem; color: #718096; margin-bottom: 0.3rem;">📊 % Enrolled in Low Income Settings</div>
                    <div style="font-size: 1.3rem; font-weight: 700; color: #1a365d;">{low_income_pct:.1f}%</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("<p style='text-align: center; font-weight: 600; color: #1a365d; font-size: 0.85rem; margin-bottom: -10px;'>Book Bank Model</p>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.7rem; margin-bottom: -10px;'>Open Book Distribution</p>", unsafe_allow_html=True)
        fig, target_str = create_count_ring(book_bank_children, book_bank_target, book_bank_pct, '#805ad5')
        st.plotly_chart(fig, use_container_width=True, key="book_bank_ring")
        st.markdown(f"<p style='text-align: center; margin-top: -20px; color: #1a365d; font-size: 0.85rem; font-weight: 700;'>2030 Target: {target_str} children</p>", unsafe_allow_html=True)

    with col3:
        st.markdown("<p style='text-align: center; font-weight: 600; color: #1a365d; font-size: 0.85rem; margin-bottom: -10px;'>Digital Engagement</p>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.7rem; margin-bottom: -10px;'>Total Views</p>", unsafe_allow_html=True)
        fig, target_str = create_count_ring(int(total_views), target_views, digital_pct, '#ed8936', is_large_number=True)
        st.plotly_chart(fig, use_container_width=True, key="digital_engagement_ring")
        st.markdown(f"<p style='text-align: center; margin-top: -20px; color: #1a365d; font-size: 0.85rem; font-weight: 700;'>2030 Target: {target_str} views/year</p>", unsafe_allow_html=True)

    with col4:
        # Format view counts
        digital_str = f"{digital_views/1000000:.2f}M" if digital_views >= 1000000 else f"{digital_views/1000:.0f}K" if digital_views >= 1000 else f"{int(digital_views):,}"
        newsletter_str = f"{newsletter_views/1000000:.2f}M" if newsletter_views >= 1000000 else f"{newsletter_views/1000:.0f}K" if newsletter_views >= 1000 else f"{int(newsletter_views):,}"
        st.markdown(f"""
            <div style='display: grid; grid-template-columns: 1fr; gap: 0.4rem; padding-top: 1.5rem;'>
                <div class="metric-card" style="text-align: center; padding: 0.5rem;">
                    <div style="font-size: 0.7rem; color: #718096; margin-bottom: 0.2rem;">📱 Digital Views</div>
                    <div style="font-size: 1.1rem; font-weight: 700; color: #1a365d;">{digital_str}</div>
                </div>
                <div class="metric-card" style="text-align: center; padding: 0.5rem;">
                    <div style="font-size: 0.7rem; color: #718096; margin-bottom: 0.2rem;">📧 Newsletter Views</div>
                    <div style="font-size: 1.1rem; font-weight: 700; color: #1a365d;">{newsletter_str}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not views_data:
        st.warning("No Content Views data available")
        return

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

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
        <div class="metric-card" style="text-align: center; padding: 1.25rem;">
            <div style="font-size: 0.85rem; color: #718096; margin-bottom: 0.5rem;">📚 Total Books</div>
            <div style="font-size: 1.75rem; font-weight: 700; color: #1a365d;">{total}</div>
        </div>
        <div class="metric-card" style="text-align: center; padding: 1.25rem;">
            <div style="font-size: 0.85rem; color: #718096; margin-bottom: 0.5rem;">✅ Completed</div>
            <div style="font-size: 1.75rem; font-weight: 700; color: #1a365d;">{completed}</div>
        </div>
        <div class="metric-card" style="text-align: center; padding: 1.25rem;">
            <div style="font-size: 0.85rem; color: #718096; margin-bottom: 0.5rem;">🔄 In Progress</div>
            <div style="font-size: 1.75rem; font-weight: 700; color: #1a365d;">{in_progress}</div>
        </div>
        <div class="metric-card" style="text-align: center; padding: 1.25rem;">
            <div style="font-size: 0.85rem; color: #718096; margin-bottom: 0.5rem;">🌎 Spanish/Bilingual</div>
            <div style="font-size: 1.75rem; font-weight: 700; color: #1a365d;">{bilingual}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Production Pipeline")
        if "status" in df.columns:
            # Normalize status values by sorting comma-separated parts
            # So "A, B, C" and "A, C, B" are treated as the same status
            def normalize_status(status):
                if pd.isna(status):
                    return status
                parts = [p.strip() for p in str(status).split(",")]
                return ", ".join(sorted(parts))

            normalized_status = df["status"].apply(normalize_status)
            status_counts = normalized_status.value_counts().reset_index()
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
            fig.update_layout(
                margin=dict(t=20, b=20, r=120),
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.02,
                    font=dict(size=10)
                )
            )
            st.plotly_chart(fig, use_container_width=True)


def render_goal4_sustainability(processor: DataProcessor, financial_df: pd.DataFrame = None):
    """Render Goal 4: Optimize Sustainability."""
    st.markdown("""
    <div class="section-header">
        <div class="section-icon goal4">🌱</div>
        <div class="section-title-group">
            <h2 class="section-title">Goal 4: Optimize Sustainability</h2>
            <p class="section-subtitle">Target: Diversified funding to $3M annually</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Get FY info for header (used by multiple sections)
    today = date.today()
    fy_info = get_fiscal_year_info(today)
    current_fy_label = fy_info['current_fy_short']
    prior_fy_label = fy_info['prior_fy_short']

    # === Donor Comparison Metrics (Individuals / Organizations / Total) ===
    # HIDDEN: Set to True to show this section again
    SHOW_DONOR_GIVING_COMPARISON = False
    if SHOW_DONOR_GIVING_COMPARISON:
        st.markdown(f"##### 💰 Donor Giving Comparison")
        st.caption(f"{current_fy_label} YTD vs {prior_fy_label} YTD (same date last year) · Excludes monthly giving & gifts ≥${DONOR_GIFT_OUTLIER_THRESHOLD/1000:.0f}K")

        try:
            donor_metrics = get_donor_comparison_metrics()
            current_fy = donor_metrics['current_fy_short']
            prior_fy = donor_metrics['prior_fy_short']

            # Helper function to calculate % change
            def pct_change(current, prior):
                if prior == 0:
                    return 100.0 if current > 0 else 0.0
                return ((current - prior) / prior) * 100

            # Helper function to format currency
            def fmt_currency(val):
                if val >= 1000000:
                    return f"${val/1000000:.2f}M"
                elif val >= 1000:
                    return f"${val/1000:.1f}K"
                else:
                    return f"${val:,.0f}"

            # Create tabs for Individuals, Organizations, and Total
            tab1, tab2, tab3 = st.tabs(["👤 Individuals", "🏢 Organizations", "📊 Total"])

            def render_donor_metrics_cards(current: dict, prior: dict, fy_current: str, fy_prior: str):
                """Render donor metrics as styled cards matching dashboard design."""
                # Calculate average gift value
                avg_gift_current = current['total_revenue'] / current['gift_count'] if current['gift_count'] > 0 else 0
                avg_gift_prior = prior['total_revenue'] / prior['gift_count'] if prior['gift_count'] > 0 else 0

                # Define metrics to display - Row 1: money metrics, Row 2: donor counts
                row1_metrics = [
                    ("💵 Total Revenue", fmt_currency(current['total_revenue']), pct_change(current['total_revenue'], prior['total_revenue'])),
                    ("🎁 Largest Gift", fmt_currency(current['largest_gift']), pct_change(current['largest_gift'], prior['largest_gift'])),
                    ("📊 Avg Gift", fmt_currency(avg_gift_current), pct_change(avg_gift_current, avg_gift_prior)),
                    ("🧾 # Gifts", f"{current['gift_count']:,}", pct_change(current['gift_count'], prior['gift_count'])),
                ]
                row2_metrics = [
                    ("🆕 New Donors", f"{current['new_donors']:,}", pct_change(current['new_donors'], prior['new_donors'])),
                    ("🔄 Reactivated", f"{current['reactivated_donors']:,}", pct_change(current['reactivated_donors'], prior['reactivated_donors'])),
                    ("⬆️ Upgraded", f"{current['upgraded_donors']:,}", pct_change(current['upgraded_donors'], prior['upgraded_donors'])),
                    ("⬇️ Downgraded", f"{current['downgraded_donors']:,}", pct_change(current['downgraded_donors'], prior['downgraded_donors'])),
                ]

                # Build metric cards HTML - Row 1: money metrics
                cards_html = '<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1rem;">'
                for label, value, change in row1_metrics:
                    color = '#38a169' if change >= 0 else '#e53e3e'
                    sign = '+' if change >= 0 else ''
                    cards_html += f'''
                    <div class="metric-card" style="text-align: center; padding: 1rem;">
                        <div style="font-size: 0.8rem; color: #718096; margin-bottom: 0.35rem;">{label}</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: #1a365d;">{value}</div>
                        <div style="font-size: 0.75rem; color: {color}; margin-top: 0.2rem;">{sign}{change:.1f}% vs {fy_prior}</div>
                    </div>'''
                cards_html += '</div>'

                # Row 2: donor counts
                cards_html += '<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;">'
                for label, value, change in row2_metrics:
                    color = '#38a169' if change >= 0 else '#e53e3e'
                    sign = '+' if change >= 0 else ''
                    cards_html += f'''
                    <div class="metric-card" style="text-align: center; padding: 1rem;">
                        <div style="font-size: 0.8rem; color: #718096; margin-bottom: 0.35rem;">{label}</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: #1a365d;">{value}</div>
                        <div style="font-size: 0.75rem; color: {color}; margin-top: 0.2rem;">{sign}{change:.1f}% vs {fy_prior}</div>
                    </div>'''
                cards_html += '</div>'

                st.markdown(cards_html, unsafe_allow_html=True)

            with tab1:
                ind = donor_metrics['individuals']
                render_donor_metrics_cards(ind['current'], ind['prior'], current_fy, prior_fy)

            with tab2:
                org = donor_metrics['organizations']
                render_donor_metrics_cards(org['current'], org['prior'], current_fy, prior_fy)

            with tab3:
                total = donor_metrics['total']
                render_donor_metrics_cards(total['current'], total['prior'], current_fy, prior_fy)

        except Exception as e:
            st.warning(f"Unable to load donor comparison metrics: {e}")

        st.markdown("<br><br>", unsafe_allow_html=True)

    # === Grants, Gifts & Donated Books ===
    st.markdown("##### 💰 Grants, Gifts & Donated Books")
    st.caption(f"{current_fy_label} YTD")

    if financial_df is not None and not financial_df.empty:
        latest = financial_df.iloc[-1]
        grants_received = float(latest.get('grants_received', 0) or 0)
        grants_goal = float(latest.get('grants_goal', 0) or 0)
        gifts_received = float(latest.get('gifts_received', 0) or 0)
        gifts_goal = float(latest.get('gifts_goal', 0) or 0)
        donated_books_goal = float(latest.get('donated_books_goal', 0) or 0)

        # Load donated books count from Fusioo (filtered by current FY)
        fy_start = fy_info['current_fy_start'].strftime("%Y-%m-%d")
        fy_end = today.isoformat()
        donated_books_count = load_donated_books_count(fy_start, fy_end)
        donated_books_pct = (donated_books_count / donated_books_goal * 100) if donated_books_goal > 0 else 0

        grants_pct = (grants_received / grants_goal * 100) if grants_goal > 0 else 0
        gifts_pct = (gifts_received / gifts_goal * 100) if gifts_goal > 0 else 0

        def create_progress_ring(received, goal, pct, title, color_fill, color_remaining):
            """Create a donut chart showing progress toward goal."""
            # Cap display percentage at 100 for the ring, but show actual in text
            display_pct = min(pct, 100)
            remaining_pct = max(100 - display_pct, 0)

            fig = go.Figure(data=[go.Pie(
                values=[display_pct, remaining_pct],
                hole=0.7,
                marker=dict(colors=[color_fill, color_remaining]),
                textinfo='none',
                hoverinfo='skip',
                sort=False
            )])

            # Format dollar amounts
            if received >= 1000000:
                received_str = f"${received/1000000:.2f}M"
            elif received >= 1000:
                received_str = f"${received/1000:.0f}K"
            else:
                received_str = f"${received:,.0f}"

            if goal >= 1000000:
                goal_str = f"${goal/1000000:.1f}M"
            elif goal >= 1000:
                goal_str = f"${goal/1000:.0f}K"
            else:
                goal_str = f"${goal:,.0f}"

            fig.update_layout(
                showlegend=False,
                margin=dict(t=30, b=30, l=10, r=10),
                height=200,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                annotations=[
                    dict(
                        text=f"<b>{received_str}</b>",
                        x=0.5, y=0.55,
                        font=dict(size=22, color='#1a365d', family='system-ui'),
                        showarrow=False
                    ),
                    dict(
                        text=f"{pct:.0f}% of goal",
                        x=0.5, y=0.38,
                        font=dict(size=12, color='#64748b', family='system-ui'),
                        showarrow=False
                    )
                ]
            )
            return fig, goal_str

        # Get donor metrics for gifts stats (current and prior for % change)
        try:
            donor_metrics = get_donor_comparison_metrics()
            curr = donor_metrics['total']['current']
            prior = donor_metrics['total']['prior']
            gift_count = curr.get('gift_count', 0)
            gift_count_prior = prior.get('gift_count', 0)
            new_donors = curr.get('new_donors', 0)
            new_donors_prior = prior.get('new_donors', 0)
            reactivated = curr.get('reactivated_donors', 0)
            reactivated_prior = prior.get('reactivated_donors', 0)
            total_revenue = curr.get('total_revenue', 0)
            total_revenue_prior = prior.get('total_revenue', 0)
            avg_gift = total_revenue / gift_count if gift_count > 0 else 0
            avg_gift_prior = total_revenue_prior / gift_count_prior if gift_count_prior > 0 else 0
            has_donor_data = True
        except Exception:
            gift_count = new_donors = reactivated = avg_gift = 0
            gift_count_prior = new_donors_prior = reactivated_prior = avg_gift_prior = 0
            has_donor_data = False

        # Get grants count from DonorPerfect (using grant GL codes)
        try:
            fy_info = get_fiscal_year_info(today)
            curr_start = fy_info['current_fy_start']
            curr_end = today.isoformat()

            # Query grants count for current period
            grant_query = f"SELECT COUNT(*) as grant_count FROM dpgift WHERE gift_date BETWEEN '{curr_start}' AND '{curr_end}' AND gl_code IN ('5120_GRANTS_RES', '5121_GRANTS_UNRES')"
            grant_results, _ = _execute_donorperfect_query(grant_query)
            grant_data = grant_results[0] if grant_results else {}

            grant_count = int(grant_data.get('grant_count', 0) or 0)
            # Use grants_received from Google Sheet divided by count from DonorPerfect
            avg_grant = grants_received / grant_count if grant_count > 0 else 0
            has_grant_data = True
        except Exception:
            grant_count = avg_grant = 0
            has_grant_data = False

        def pct_change(curr_val, prior_val):
            if prior_val == 0:
                return 100.0 if curr_val > 0 else 0.0
            return ((curr_val - prior_val) / prior_val) * 100

        # All three rings and stats in one row: Grants | Grant Stats | Gifts | Gift Stats | Books
        col1, col2, col3, col4, col5 = st.columns([1, 0.8, 1, 1.2, 1])

        with col1:
            st.markdown("<p style='text-align: center; font-weight: 600; color: #1a365d; font-size: 0.9rem; margin-bottom: -10px;'>Grants</p>", unsafe_allow_html=True)
            fig, goal_str = create_progress_ring(
                grants_received, grants_goal, grants_pct,
                "Grants", "#38a169", "#e2e8f0"
            )
            st.plotly_chart(fig, use_container_width=True, key="grants_ring")
            st.markdown(f"<p style='text-align: center; margin-top: -20px; color: #1a365d; font-size: 0.85rem; font-weight: 700;'>Goal: {goal_str}</p>", unsafe_allow_html=True)

        with col2:
            if has_grant_data:
                avg_grant_str = f"${avg_grant/1000:.1f}K" if avg_grant >= 1000 else f"${avg_grant:,.0f}"
                st.markdown(f"""
                    <div style='display: grid; grid-template-columns: 1fr; gap: 0.4rem; padding-top: 1.5rem;'>
                        <div class="metric-card" style="text-align: center; padding: 0.5rem;">
                            <div style="font-size: 0.7rem; color: #718096; margin-bottom: 0.2rem;">📋 # Grants</div>
                            <div style="font-size: 1.1rem; font-weight: 700; color: #1a365d;">{grant_count:,}</div>
                        </div>
                        <div class="metric-card" style="text-align: center; padding: 0.5rem;">
                            <div style="font-size: 0.7rem; color: #718096; margin-bottom: 0.2rem;">📊 Avg Grant</div>
                            <div style="font-size: 1.1rem; font-weight: 700; color: #1a365d;">{avg_grant_str}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        with col3:
            st.markdown("<p style='text-align: center; font-weight: 600; color: #1a365d; font-size: 0.9rem; margin-bottom: -10px;'>Gifts</p>", unsafe_allow_html=True)
            fig, goal_str = create_progress_ring(
                gifts_received, gifts_goal, gifts_pct,
                "Gifts", "#805ad5", "#e2e8f0"
            )
            st.plotly_chart(fig, use_container_width=True, key="gifts_ring")
            st.markdown(f"<p style='text-align: center; margin-top: -20px; color: #1a365d; font-size: 0.85rem; font-weight: 700;'>Goal: {goal_str}</p>", unsafe_allow_html=True)

        with col4:
            if has_donor_data:
                avg_gift_str = f"${avg_gift/1000:.1f}K" if avg_gift >= 1000 else f"${avg_gift:,.0f}"
                gift_chg = pct_change(gift_count, gift_count_prior)
                new_chg = pct_change(new_donors, new_donors_prior)
                ret_chg = pct_change(reactivated, reactivated_prior)
                avg_chg = pct_change(avg_gift, avg_gift_prior)
                st.markdown(f"""
                    <div style='display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.4rem; padding-top: 0.5rem;'>
                        <div class="metric-card" style="text-align: center; padding: 0.5rem;">
                            <div style="font-size: 0.65rem; color: #718096; margin-bottom: 0.15rem;">🎁 Gifts</div>
                            <div style="font-size: 1rem; font-weight: 700; color: #1a365d;">{gift_count:,}</div>
                            <div style="font-size: 0.6rem; color: {'#38a169' if gift_chg >= 0 else '#e53e3e'};">
                                {'+' if gift_chg >= 0 else ''}{gift_chg:.0f}% vs {prior_fy_label}
                            </div>
                        </div>
                        <div class="metric-card" style="text-align: center; padding: 0.5rem;">
                            <div style="font-size: 0.65rem; color: #718096; margin-bottom: 0.15rem;">🆕 New</div>
                            <div style="font-size: 1rem; font-weight: 700; color: #1a365d;">{new_donors:,}</div>
                            <div style="font-size: 0.6rem; color: {'#38a169' if new_chg >= 0 else '#e53e3e'};">
                                {'+' if new_chg >= 0 else ''}{new_chg:.0f}% vs {prior_fy_label}
                            </div>
                        </div>
                        <div class="metric-card" style="text-align: center; padding: 0.5rem;">
                            <div style="font-size: 0.65rem; color: #718096; margin-bottom: 0.15rem;">🔄 Returning</div>
                            <div style="font-size: 1rem; font-weight: 700; color: #1a365d;">{reactivated:,}</div>
                            <div style="font-size: 0.6rem; color: {'#38a169' if ret_chg >= 0 else '#e53e3e'};">
                                {'+' if ret_chg >= 0 else ''}{ret_chg:.0f}% vs {prior_fy_label}
                            </div>
                        </div>
                        <div class="metric-card" style="text-align: center; padding: 0.5rem;">
                            <div style="font-size: 0.65rem; color: #718096; margin-bottom: 0.15rem;">📊 Avg Gift</div>
                            <div style="font-size: 1rem; font-weight: 700; color: #1a365d;">{avg_gift_str}</div>
                            <div style="font-size: 0.6rem; color: {'#38a169' if avg_chg >= 0 else '#e53e3e'};">
                                {'+' if avg_chg >= 0 else ''}{avg_chg:.0f}% vs {prior_fy_label}
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        with col5:
            st.markdown("<p style='text-align: center; font-weight: 600; color: #1a365d; font-size: 0.9rem; margin-bottom: -10px;'>Donated Books</p>", unsafe_allow_html=True)
            # Create progress ring for donated books (use a different format since it's count not currency)
            display_pct = min(donated_books_pct, 100)
            remaining_pct = max(100 - display_pct, 0)
            fig = go.Figure(data=[go.Pie(
                values=[display_pct, remaining_pct],
                hole=0.7,
                marker=dict(colors=['#e53e3e', '#e2e8f0']),
                textinfo='none',
                hoverinfo='skip',
                sort=False
            )])
            fig.update_layout(
                showlegend=False,
                margin=dict(t=30, b=30, l=10, r=10),
                height=200,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                annotations=[
                    dict(
                        text=f"<b>{donated_books_count:,}</b>",
                        x=0.5, y=0.55,
                        font=dict(size=22, color='#1a365d', family='system-ui'),
                        showarrow=False
                    ),
                    dict(
                        text=f"{donated_books_pct:.0f}% of goal",
                        x=0.5, y=0.38,
                        font=dict(size=12, color='#64748b', family='system-ui'),
                        showarrow=False
                    )
                ]
            )
            st.plotly_chart(fig, use_container_width=True, key="donated_books_ring")
            goal_str = f"{donated_books_goal:,.0f}" if donated_books_goal < 1000 else f"{donated_books_goal/1000:.0f}K"
            st.markdown(f"<p style='text-align: center; margin-top: -20px; color: #1a365d; font-size: 0.85rem; font-weight: 700;'>Goal: {goal_str} books</p>", unsafe_allow_html=True)

    else:
        st.info("Financial data not available")

    # === Donor Contacts Year-over-Year Comparison ===
    st.markdown("##### 📧 Donor Contacts")
    st.caption(f"{current_fy_label} YTD vs {prior_fy_label} YTD (same date last year) · Outreach activities from DonorPerfect")

    try:
        contact_data = get_contact_metrics_comparison()
        current_metrics = contact_data['current_fy']
        prior_metrics = contact_data['prior_fy']

        # Dynamic FY labels
        current_fy = contact_data['current_fy_short']
        prior_fy = contact_data['prior_fy_short']
        current_col = f"{current_fy} YTD"
        prior_col = f"{prior_fy} YTD"

        # Type labels for display (from DonorPerfect activity codes)
        type_labels = {
            'ANNUALREPORT': 'Annual Report',
            'APPLICATION': 'Application',
            'APPDUE': 'Application Due Date',
            'BIRTHDAYCARD': 'Birthday Card',
            'CAPITALCAMPAIGNCULTIVATION': 'Capital Campaign Cultivation',
            'CC': 'Constant Contact Campaign',
            'CONTRACT': 'Contract',
            'EI': 'Email In',
            'EO': 'Email Out',
            'EVENT': 'Event',
            'EV_IN': 'Event Invite',
            'FBS': 'FBS Appeal',
            'FIREP': 'Final Report',
            'FOLLOWUP': 'Follow Up with Donor',
            'GENERALINFO': 'General Info',
            'GE': 'Group E-Mail',
            'GFU': 'Grant Follow-Up',
            'GLOI': 'Grant LOI',
            'GP': 'Grant Proposal',
            'GR': 'Grant Report Due',
            'GRANTAWARD': 'Grant Award',
            'GRANTDECLINED': 'Grant Declined',
            'LT': 'Letter',
            'LUNCHEONINVITE': 'Luncheon Invitation',
            'MA': 'Mailing',
            'MAJORGIFTSCULTIVATION': 'Major Gifts Cultivation',
            'ME': 'Meeting',
            'PLEDGE': 'Pledge Follow Up',
            'PROSPECTRESEARCH': 'Prospect Research',
            'RCPTSNT': 'Receipt Sent',
            'SP': 'Sponsorship Proposal',
            'SPONSORSHIPAGREEMENT': 'Sponsorship Agreement',
            'TE': 'Telephone Call',
            'TYNOTE': 'Thank You Note',
            'VI': 'Visit',
            'YEA_MAIL': 'Year End Appeal Mailer',
            'ZOOMCALL': 'Zoom Call',
        }

        # Get all unique contact types from both periods
        all_types = set(current_metrics['by_type'].keys()) | set(prior_metrics['by_type'].keys())
        # Sort: known types first in preferred order, then unknown types alphabetically
        preferred_order = [
            'CC', 'EO', 'EI', 'GE', 'MA', 'LT', 'RCPTSNT', 'TYNOTE',
            'TE', 'ME', 'ZOOMCALL', 'VI', 'EVENT', 'EV_IN', 'LUNCHEONINVITE',
            'GFU', 'GP', 'GLOI', 'GRANTAWARD', 'GRANTDECLINED', 'GR', 'FIREP',
            'APPLICATION', 'APPDUE', 'CONTRACT', 'PLEDGE', 'FOLLOWUP',
            'FBS', 'YEA_MAIL', 'BIRTHDAYCARD', 'ANNUALREPORT',
            'SP', 'SPONSORSHIPAGREEMENT', 'CAPITALCAMPAIGNCULTIVATION', 'MAJORGIFTSCULTIVATION',
            'PROSPECTRESEARCH', 'GENERALINFO'
        ]
        contact_types = [t for t in preferred_order if t in all_types]
        contact_types += sorted([t for t in all_types if t not in preferred_order])

        comparison_data = []
        for ct in contact_types:
            current_count = current_metrics['by_type'].get(ct, 0)
            prior_count = prior_metrics['by_type'].get(ct, 0)
            change = current_count - prior_count
            pct_change = ((current_count - prior_count) / prior_count * 100) if prior_count > 0 else (100 if current_count > 0 else 0)
            comparison_data.append({
                'Contact Type': type_labels.get(ct, ct),
                current_col: current_count,
                prior_col: prior_count,
                'Change': change,
                '% Change': pct_change
            })

        # Calculate totals
        total_current = current_metrics['total']
        total_prior = prior_metrics['total']
        total_change = total_current - total_prior
        total_pct = ((total_change) / total_prior * 100) if total_prior > 0 else 0

        # Calculate % changes for each metric card
        cc_current = current_metrics['by_type'].get('CC', 0)
        cc_prior = prior_metrics['by_type'].get('CC', 0)
        cc_pct = ((cc_current - cc_prior) / cc_prior * 100) if cc_prior > 0 else 0

        lt_current = current_metrics['by_type'].get('LT', 0)
        lt_prior = prior_metrics['by_type'].get('LT', 0)
        lt_pct = ((lt_current - lt_prior) / lt_prior * 100) if lt_prior > 0 else 0

        rcpt_current = current_metrics['by_type'].get('RCPTSNT', 0)
        rcpt_prior = prior_metrics['by_type'].get('RCPTSNT', 0)
        rcpt_pct = ((rcpt_current - rcpt_prior) / rcpt_prior * 100) if rcpt_prior > 0 else 0

        # Create metric cards row for contact totals
        st.markdown(f"""
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
            <div class="metric-card" style="text-align: center; padding: 1.25rem;">
                <div style="font-size: 0.85rem; color: #718096; margin-bottom: 0.5rem;">📬 Total Contacts {current_fy}</div>
                <div style="font-size: 1.75rem; font-weight: 700; color: #1a365d;">{total_current:,}</div>
                <div style="font-size: 0.8rem; color: {'#38a169' if total_change >= 0 else '#e53e3e'}; margin-top: 0.25rem;">
                    {'+' if total_pct >= 0 else ''}{total_pct:.1f}% vs {prior_fy}
                </div>
            </div>
            <div class="metric-card" style="text-align: center; padding: 1.25rem;">
                <div style="font-size: 0.85rem; color: #718096; margin-bottom: 0.5rem;">📧 Constant Contact</div>
                <div style="font-size: 1.75rem; font-weight: 700; color: #1a365d;">{cc_current:,}</div>
                <div style="font-size: 0.8rem; color: {'#38a169' if cc_pct >= 0 else '#e53e3e'}; margin-top: 0.25rem;">
                    {'+' if cc_pct >= 0 else ''}{cc_pct:.1f}% vs {prior_fy}
                </div>
            </div>
            <div class="metric-card" style="text-align: center; padding: 1.25rem;">
                <div style="font-size: 0.85rem; color: #718096; margin-bottom: 0.5rem;">✉️ Letters</div>
                <div style="font-size: 1.75rem; font-weight: 700; color: #1a365d;">{lt_current:,}</div>
                <div style="font-size: 0.8rem; color: {'#38a169' if lt_pct >= 0 else '#e53e3e'}; margin-top: 0.25rem;">
                    {'+' if lt_pct >= 0 else ''}{lt_pct:.1f}% vs {prior_fy}
                </div>
            </div>
            <div class="metric-card" style="text-align: center; padding: 1.25rem;">
                <div style="font-size: 0.85rem; color: #718096; margin-bottom: 0.5rem;">🧾 Receipts Sent</div>
                <div style="font-size: 1.75rem; font-weight: 700; color: #1a365d;">{rcpt_current:,}</div>
                <div style="font-size: 0.8rem; color: {'#38a169' if rcpt_pct >= 0 else '#e53e3e'}; margin-top: 0.25rem;">
                    {'+' if rcpt_pct >= 0 else ''}{rcpt_pct:.1f}% vs {prior_fy}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Two columns: Contact comparison chart + CC Campaign Status chart
        col1, col2 = st.columns(2)

        with col1:
            # Create horizontal grouped bar chart for YoY comparison (matches CC Status chart)
            comparison_df = pd.DataFrame(comparison_data)
            chart_df = comparison_df.copy()

            contact_types = chart_df['Contact Type'].tolist()
            current_vals = chart_df[current_col].tolist()
            prior_vals = chart_df[prior_col].tolist()
            pct_changes = chart_df['% Change'].tolist()

            # Get max value for x-axis range
            max_val = max(max(current_vals), max(prior_vals))

            fig = go.Figure()

            # Prior FY bars (lighter color)
            fig.add_trace(go.Bar(
                name=prior_col,
                y=contact_types,
                x=prior_vals,
                orientation='h',
                marker_color='#a0aec0',
                text=[f'{v:,.0f}' for v in prior_vals],
                textposition='outside',
                textfont=dict(size=9, color='#718096'),
                width=0.35,
                offset=-0.18
            ))

            # Current FY bars (primary color)
            fig.add_trace(go.Bar(
                name=current_col,
                y=contact_types,
                x=current_vals,
                orientation='h',
                marker_color='#667eea',
                text=[f'{v:,.0f}' for v in current_vals],
                textposition='outside',
                textfont=dict(size=10),
                width=0.35,
                offset=0.18
            ))

            fig = style_plotly_chart(fig, height=320)
            fig.update_layout(
                barmode='group',
                bargap=0.25,
                title=dict(text='Contact Volume by Type', font=dict(size=14)),
                xaxis=dict(range=[0, max_val * 1.5]),  # Headroom for labels with % change
                yaxis=dict(autorange='reversed'),  # Largest at top
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=10))
            )

            # Add % change annotations positioned relative to current FY bar text
            for i, (val, pct) in enumerate(zip(current_vals, pct_changes)):
                color = '#38a169' if pct > 0 else '#e53e3e'
                sign = '+' if pct > 0 else ''
                # Position at end of bar value text, aligned with current FY bar
                fig.add_annotation(
                    x=val,
                    y=contact_types[i],
                    text=f'  <b>({sign}{pct:.0f}%)</b>',
                    showarrow=False,
                    font=dict(size=10, color=color),
                    xanchor='left',
                    yanchor='middle',
                    xshift=30,  # Shift right past the number text
                    yshift=-18  # Align with current FY bar
                )

            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # CC Campaign Status - Horizontal Bar Chart with YoY comparison
            if current_metrics['cc_by_status'] or prior_metrics.get('cc_by_status'):
                # Get all unique statuses from both periods
                all_statuses = set(current_metrics.get('cc_by_status', {}).keys()) | set(prior_metrics.get('cc_by_status', {}).keys())

                # Build comparison data sorted by current FY value descending
                cc_compare = []
                for status in all_statuses:
                    curr_val = current_metrics.get('cc_by_status', {}).get(status, 0)
                    prior_val = prior_metrics.get('cc_by_status', {}).get(status, 0)
                    pct_chg = ((curr_val - prior_val) / prior_val * 100) if prior_val > 0 else (100 if curr_val > 0 else 0)
                    cc_compare.append({
                        'status': status,
                        'current': curr_val,
                        'prior': prior_val,
                        'pct_change': pct_chg
                    })
                cc_compare.sort(key=lambda x: x['current'], reverse=True)

                statuses = [d['status'] for d in cc_compare]
                current_vals = [d['current'] for d in cc_compare]
                prior_vals = [d['prior'] for d in cc_compare]
                pct_changes = [d['pct_change'] for d in cc_compare]

                # Create text labels with % change
                current_texts = []
                for val, pct in zip(current_vals, pct_changes):
                    if pct >= 0:
                        current_texts.append(f'{val:,.0f} <span style="color:#38a169">(+{pct:.0f}%)</span>')
                    else:
                        current_texts.append(f'{val:,.0f} <span style="color:#e53e3e">({pct:.0f}%)</span>')

                fig_cc = go.Figure()

                # Prior FY bars (lighter color, behind)
                fig_cc.add_trace(go.Bar(
                    name=prior_fy,
                    y=statuses,
                    x=prior_vals,
                    orientation='h',
                    marker_color='#a0aec0',
                    text=[f'{v:,.0f}' for v in prior_vals],
                    textposition='outside',
                    textfont=dict(size=9, color='#718096'),
                    width=0.35,
                    offset=-0.18
                ))

                # Current FY bars (primary color, in front)
                fig_cc.add_trace(go.Bar(
                    name=current_fy,
                    y=statuses,
                    x=current_vals,
                    orientation='h',
                    marker_color='#667eea',
                    text=[f'{v:,.0f}' for v in current_vals],
                    textposition='outside',
                    textfont=dict(size=10),
                    width=0.35,
                    offset=0.18
                ))

                max_val = max(max(current_vals) if current_vals else 0, max(prior_vals) if prior_vals else 0)
                fig_cc = style_plotly_chart(fig_cc, height=340)
                fig_cc.update_layout(
                    title=dict(text='Constant Contact by Status', font=dict(size=14)),
                    xaxis=dict(range=[0, max_val * 1.5]),  # More headroom for labels with % change
                    yaxis=dict(autorange='reversed'),  # Largest at top
                    barmode='group',
                    bargap=0.25,
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=10))
                )

                # Add % change annotations positioned relative to current FY bar text
                for i, (val, pct) in enumerate(zip(current_vals, pct_changes)):
                    color = '#38a169' if pct > 0 else '#e53e3e'
                    sign = '+' if pct > 0 else ''
                    fig_cc.add_annotation(
                        x=val,
                        y=statuses[i],
                        text=f'  <b>({sign}{pct:.0f}%)</b>',
                        showarrow=False,
                        font=dict(size=10, color=color),
                        xanchor='left',
                        yanchor='middle',
                        xshift=30,  # Shift right past the number text
                        yshift=-18  # Align with current FY bar
                    )

                st.plotly_chart(fig_cc, use_container_width=True)

    except Exception as e:
        st.warning(f"Unable to load donor contacts data: {e}")


def render_financial_metrics(financial_df: pd.DataFrame = None):
    """Render Financial Metrics section with real data from Google Sheets."""
    st.markdown("""
    <div class="section-header">
        <div class="section-icon financial">💰</div>
        <div class="section-title-group">
            <h2 class="section-title">Financial Metrics</h2>
            <p class="section-subtitle">Fiscal year to date (July 1 – present) · Updates daily at noon</p>
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

        if st.button("🔄 Refresh Data from DonorPerfect", use_container_width=True, help="Re-run SQL queries and refresh donor metrics"):
            load_donorperfect_contact_metrics.clear()
            load_individual_donor_metrics.clear()
            load_donor_metrics_by_type.clear()
            st.toast("Refreshing donor data from DonorPerfect...", icon="💝")
            st.rerun()

    # Load data
    with st.spinner("Loading data..."):
        activity_records = load_activity_data()
        legacy_records = load_legacy_data()
        original_books = load_original_books()
        content_views = load_content_views()
        financial_data = load_financial_data()
        enrollment_count, b3_low_income_pct = load_b3_low_income_stats()
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

    # Note: Previously served children exclusion is handled by DataProcessor._exclude_previously_served_children()
    # which zeros out both children counts AND books distributed for those rows

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
    render_hero_header(processor, activity_records, partners_data, start_date, end_date)

    # Dashboard sections
    render_goal1_strengthen_impact(processor, time_unit)
    st.markdown("---")

    render_goal2_inspire_engagement(content_views, time_unit, start_date, end_date, enrollment_count, book_bank_children, inperson_events, activity_records, partners_data, b3_low_income_pct)
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
