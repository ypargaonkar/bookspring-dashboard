# BookSpring Strategic Dashboard

A Streamlit dashboard for tracking BookSpring's 2025-2030 strategic goals, including book distribution, children served, engagement metrics, and more.

## Features

- **Goal 1: Strengthen Impact** - Track books per child metrics and age group distributions
- **Goal 2: Inspire Engagement** - Monitor digital and newsletter views
- **Goal 3: Advance Innovation** - Track original book production pipeline
- **Goal 4: Optimize Sustainability** - Monitor distribution capacity and operational metrics
- **Trends & Comparisons** - Analyze metrics over time and compare periods
- **Excel Export** - Generate comprehensive reports

## Setup

### Prerequisites
- Python 3.9+
- Fusioo API access token

### Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/bookspring-dashboard.git
cd bookspring-dashboard
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your credentials:
```
FUSIOO_ACCESS_TOKEN=your_token_here
```

4. Run the dashboard:
```bash
streamlit run src/dashboard/app.py
```

## Deployment

This dashboard is designed to be deployed on [Streamlit Community Cloud](https://share.streamlit.io/).

### Streamlit Cloud Setup
1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Add secrets in the Streamlit Cloud dashboard:
   - `FUSIOO_ACCESS_TOKEN`: Your Fusioo API token
5. Deploy!

## Data Sources

The dashboard pulls data from Fusioo:
- Activity Reports (current data from July 2025+)
- Legacy Program Partners data (historical data pre-July 2025)
- Content Views (digital engagement metrics)
- Original Books (book production tracking)

## License

Private - BookSpring Internal Use
