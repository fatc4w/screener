# China FX Dashboard

A Streamlit dashboard for analyzing Chinese foreign exchange data from multiple sources.

## Data Sources

1. **SAFE China** - State Administration of Foreign Exchange
   - Foreign Exchange Settlement and Sales by Banks (monthly, USD)
   - Source: https://www.safe.gov.cn/

2. **Polygon.io** - Financial market data
   - USDCNH spot rate data
   - Real-time and historical FX data

## Project Structure

```
macro-dash-streamlit/
├── notebooks/              # Development and exploration notebooks
│   └── safe_china_data.ipynb
├── data/                   # Processed data files (not committed)
├── .streamlit/            # Streamlit configuration
├── Screener.py            # Main Streamlit app
└── requirements.txt       # Python dependencies
```

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your API keys:
   ```
   POLYGON_API_KEY=your_polygon_api_key
   ```

4. Run the Streamlit app:
   ```bash
   streamlit run Screener.py
   ```

## Development Workflow

### Data Pipeline Development
Use Jupyter notebooks in the `notebooks/` directory for:
- Exploring data sources
- Developing data transformation logic
- Testing visualizations
- Iterating on analysis

### Production Deployment
- Data pipelines are converted to Python modules
- Charts and visualizations are integrated into Streamlit app
- Data transformation happens behind the scenes
- Clean, interactive dashboard interface

## Features (In Development)

- [ ] SAFE China FX settlement and sales data scraping
- [ ] Polygon.io USDCNH spot rate integration
- [ ] Time series visualizations
- [ ] Multi-source data comparison charts
- [ ] Interactive filtering and date selection

## License

MIT
