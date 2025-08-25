# AML Interactive Dashboard (Single‑Page)

A fast, single‑page Streamlit app that turns raw transaction CSVs into the core 'anti money laundering' (AML) inspection views that analysts need. It automates the first‑pass checks so you can focus on judgment instead of spreadsheets.

## What it does

- Upload a CSV and pick a date window.
- See key KPIs at a glance:
  - Total deposits and withdrawals (count and value)
  - Transactions per hour (00–23)
  - Domestic vs international split (counts, total value)
  - Largest single deposit and withdrawal
  - Channel mix (EFT, Cash, SmartApp, …)
- Optional: generate a short “analyst note” using an LLM if an API key is provided.

All computation happens in‑memory; nothing is uploaded to external services by default.

## Tech stack

- Streamlit (UI)
- Pandas (data wrangling)
- Plotly Express (charts)
- Optional: OpenAI (brief narrative summary)

## Getting started

1) Create a Python virtual environment (optional but recommended)

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
```

2) Install dependencies

```powershell
pip install -r requirements.txt
```

3) Run the app

```powershell
streamlit run app.py
```

4) In the app sidebar, upload your CSV, then choose the date window to analyze.

## CSV requirements

Your file must include at least these columns:

- tx_datetime: ISO-like timestamp (will be parsed as datetime)
- amount: positive for deposits, negative for withdrawals
- counterparty_country_code: 2‑letter country code (e.g., ZA)
- channel: source channel label (e.g., EFT, Cash, SmartApp)

Example header:

```
tx_datetime,amount,counterparty_country_code,channel
2025-01-03T10:12:00,1500.00,ZA,EFT
2025-01-03T11:47:33,-850.00,GB,SmartApp
```

Notes:
- Domestic vs international uses a default “home” country of ZA in the app logic.
- Deposits are treated as amounts > 0; withdrawals as amounts < 0.

## Optional: LLM “Analyst note”

If you set an OpenAI API key, the app can produce a concise executive summary of the current view. This is off by default and only runs if you explicitly enable it in the UI.

Configure via environment variable:

```powershell
$env:OPENAI_API_KEY = "<your-key>"
```

Tip: Keep secrets out of version control. Use a local `.env` file (already git‑ignored) or set environment variables in your shell/session.

## Project layout

- `app.py` — Streamlit application
- `requirements.txt` — Python dependencies
- `aml_synthetic_transactions.csv` — example/synthetic data
- `session.ipynb`, `new_session.ipynb` — exploratory notebooks

## Why this exists

Analysts shouldn’t have to rebuild the same SUMIFs and pivot tables for every case. This app automates the first‑pass metrics, flags common outliers, and produces charts suitable for quick reviews, reducing time spent on Excel plumbing.

## Troubleshooting

- App won’t start / import errors: ensure your virtual environment is activated and dependencies are installed.
- Blank charts or errors: check that your CSV has the required columns and valid datetimes.
- LLM note disabled: set `OPENAI_API_KEY` if you want the narrative feature. Without a key, the dashboard still works normally.

## Roadmap (ideas)

- Export a compact PDF/HTML case summary
- More spotlight rules (velocity, circular flows, rapid cash‑out)
- Advanced filters (amount thresholds, countries, channels)
- Pluggable model scoring (internal services)

## License

No license file is included. If you plan to share or reuse, add a LICENSE of your choice (e.g., MIT/Apache‑2.0).
