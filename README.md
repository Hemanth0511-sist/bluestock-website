\# N100 Financial Intelligence Platform



\## Project Overview



The N100 Financial Intelligence Platform is a data engineering and financial analytics project that processes financial data of Nifty 100 companies.



\## Sprint 1 Goal



\- Build ETL Pipeline

\- Create SQLite Database

\- Validate Data Quality

\- Load 12 Excel datasets

\- Generate Audit Reports



\## Tech Stack



\- Python

\- Pandas

\- SQLite

\- SQLAlchemy

\- Pytest



\## Project Structure



\- data/

\- src/

\- database/

\- output/

\- tests/

\- docs/



## Sprint 4 — Streamlit Dashboard & Valuation

Sprint 4 delivers an 8-screen Streamlit dashboard and a valuation module for the Nifty 100 financial intelligence platform.

### Dashboard Run Instructions

Activate the virtual environment:

```powershell
.venv\Scripts\Activate.ps1
```

Run the dashboard:

```powershell
streamlit run src/dashboard/app.py
```

The dashboard runs locally at:

```text
http://localhost:8501
```

### Dashboard Screens

1. **Home** — KPI summary, sector distribution, top quality companies, and year selection.
2. **Company Profile** — company search, company information, financial KPIs, revenue/profit trends, ROE/ROCE trends, and pros/cons.
3. **Screener** — financial metric filters, preset strategies, live results, and CSV export.
4. **Peer Comparison** — peer-group selection, benchmark comparison, KPI comparison, and radar chart.
5. **Trend Analysis** — company search, multi-metric selection, and 10-year financial trends.
6. **Sector Analysis** — sector selection, revenue/ROE bubble chart, and sector median KPIs.
7. **Capital Allocation Map** — treemap of capital-allocation patterns and company lists.
8. **Annual Reports** — company search, available report years, and BSE annual-report links.

### Valuation Module

Run the valuation module with:

```powershell
python src/analytics/valuation.py
```

Generated outputs:

```text
output/
├── valuation_summary.xlsx
└── valuation_flags.csv
```

The valuation summary contains:

- company_id
- company_name
- sector
- P/E
- P/B
- EV/EBITDA
- FCF_yield_pct
- 5yr_median_PE
- PE_vs_sector_median_pct
- flag

Valuation flags:

```text
P/E > sector median × 1.5  → Caution
P/E < sector median × 0.7  → Discount
Otherwise                  → Fair
```

FCF yield:

```text
FCF Yield (%) = Free Cash Flow / Market Capitalization × 100
```

### Sprint 4 QA

The dashboard was tested for:

- All 8 dashboard screens
- 10 different company tickers
- Multiple sectors
- Partial historical data
- Missing financial data
- Extreme screener values
- Dashboard compilation
- Chart rendering
- Screener filtering
- CSV export
- Valuation output generation

### Sprint 4 Deliverables

```text
src/dashboard/app.py

src/dashboard/pages/
├── 01_home.py
├── 02_profile.py
├── 03_screener.py
├── 04_peers.py
├── 05_trends.py
├── 06_sectors.py
├── 07_capital.py
└── 08_reports.py

src/dashboard/utils/db.py
src/analytics/valuation.py

output/
├── valuation_summary.xlsx
└── valuation_flags.csv
```

### Sprint 4 Retrospective

#### Completed

The Streamlit dashboard, valuation module, and integration QA were completed during Sprint 4.

#### UX Decisions

- Wide dashboard layout for financial tables and charts.
- Sidebar navigation for the eight screens.
- Company search for company-specific analysis.
- Interactive Plotly charts for financial visualization.
- Missing values handled without crashing the dashboard.
- Live screener filtering with CSV export.

#### Data Edge Cases

The dashboard was tested with:

- Partial historical company data
- Missing financial metrics
- Missing FCF values
- Different historical periods
- Missing valuation values
- Extreme screener filter combinations

#### Final Status

Sprint 4 implementation and QA are complete and ready for final review.
