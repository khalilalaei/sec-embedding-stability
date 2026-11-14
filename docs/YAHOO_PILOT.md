# Yahoo adjusted-price pilot while WRDS is pending

This is an alternative data-collection path for the 12 selected companies. It supports a local exploratory risk/sensitivity study. It is not a CRSP replacement or proof of historical forecasting validity. WRDS/CRSP remains the preferred larger-study route for permanent identifiers, historical security links and active/inactive coverage.

## Scope

Default observations are frozen through **2026-11-02**, matching the original pilot as-of period. Request start is 2024-01-01, end is 2026-11-03 **exclusive**. The first price session is used only to calculate the next session's return. No return is invented for the first price row.

`yfinance.Ticker.history` is called with daily data, actions=True, auto_adjust=False, back_adjust=False, repair=False, keepna=True and rounding=False. Returns are computed explicitly as AdjClose[t]/AdjClose[t-1]-1. These are Yahoo adjusted-price return **proxies**, not independently reconstructed CRSP total returns. Dividends are not added a second time. Repair is disabled so the downloader does not silently introduce model-based price corrections.

The original yfinance-parsed price table and its metadata representation are saved for every security with hashes. They are not described as raw HTTP responses: the library has already parsed the provider response. The collector records its package versions and exact query window/options. Data remain under ignored `data/market/`, not on GitHub.

An explicit XNYS daily calendar from exchange_calendars is checked against every company's price dates. Missing prices, missing expected sessions, extra dates, duplicate dates and nonpositive adjusted closes fail the collection rather than silently becoming zero returns or multi-day returns. This calendar is a pilot choice for these US listings and must be reviewed before extending to other exchanges. The library/calendar version is retained.

## Install and collect

From your project PowerShell, run each line separately:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e ".[market]"
.\.venv\Scripts\python.exe -m secstab.yahoo_pilot
```

The collector requests 12 histories sequentially with a pause. No API key is required by this path, but provider service access and limits can change. Do not bypass access controls or respond to rate limits with aggressive retries. Failed/partial collections retain their manifest and fetched tables. An existing output folder is never overwritten; inspect the error and use a new versioned output only after resolving the cause.

Output: `data/market/yahoo_pilot_v1/`.

- `provider_tables/`: library-parsed history CSV and metadata JSON for each ticker.
- `returns.csv`: canonical date, security_id, total_return proxy.
- `trading_calendar.csv`: explicit dates for the calculated return panel.
- `security_links.csv`: filing CIK/document to **YF:TICKER** vendor alias, with review pending.
- `identity_review.json`: provider symbol/name (when supplied), currency, instrument type, exchange and coverage.
- `corpus_snapshot.json`: the input document register.
- `manifest.json`: source/output hashes, query settings, versions, completion or failure status.

The collector checks symbol, USD currency, equity type and exchange timezone. These checks do not independently establish issuer/share-class identity over history. `YF:MSFT` is deliberately a vendor-scoped alias, never a fabricated PERMNO. Links remain pending until reviewed; no filing-availability dates are automatically marked approved.

A successful status is `complete_data_collection_pending_review`. Before financial evaluation, review source identity, corporate-action/adjustment behavior, calendar coverage, window timing and filing eligibility. Later we can swap CRSP into the same canonical return interface and compare results, preserving the Yahoo collection separately.

## Research limits

The 12 companies were deliberately selected from current names. Yahoo aliases/adjusted histories do not resolve survivorship, permanent historical identifiers, delisting returns or historical-vintage data. Do not claim a historical S&P 500 backtest from this sample. Model training cutoffs remain unknown; current embeddings applied to earlier market outcomes form a retrospective diagnostic. Changing the market-data provider does not fix that issue.

The downloader's synthetic numerical tests do not demonstrate live network access or correct real-market observations. This version has been tested offline; the user's first collection is the live integration check. No alternative-provider market data or financial performance is reported yet.

## Primary documentation consulted

- yfinance overview and data-use scope: https://ranaroussi.github.io/yfinance/
- Explicit history options and exclusive end date: https://ranaroussi.github.io/yfinance/reference/yfinance.price_history.html
- Yahoo adjusted-close explanation: https://in.help.yahoo.com/kb/adjusted-close-sln28256.html
- Calendar sessions: https://github.com/gerrymanoim/exchange_calendars
- CRSP historical active/inactive coverage: https://www.crsp.org/research/crsp-us-stock-databases-2025-layout/

The yfinance project directs users to Yahoo's terms for data-use rights and describes the API as intended for personal use. This collector does not redistribute provider data. Confirm institutional/publication rights before sharing a dataset; code and aggregate experimental reports can be kept separate from licensed/raw observations.

## Metadata compatibility repair — 2026-11-13

The first live collection exposed a serialization bug: recent yfinance returns a lazy HistoryMetadata object implementing Mapping rather than a built-in dict. The initial default=str JSON conversion flattened that object into text, causing the identity check to fail. The repaired code recursively preserves mappings, numerical scalars and timestamps, validates the resulting dictionary, and deliberately omits the lazy tradingPeriods field because it can trigger an unrelated intraday request. This omission is recorded in the collection manifest. Symbol/currency/type/timezone checks remain mandatory.

The history request now uses config.debug.hide_exceptions=False where available and restores its previous value afterward, including on failure. Older versions use the legacy raise_errors=True path. This removes the deprecated flag on current yfinance without hiding fetch errors.

Keep the failed yahoo_pilot_v1 folder as evidence. After git pull, retry with a new directory:

```powershell
.\.venv\Scripts\python.exe -m secstab.yahoo_pilot --output data/market/yahoo_pilot_v2
```

Tests include a non-dict lazy Mapping, prevention of an intraday-key fetch, strict metadata parsing, modern/legacy error policies, configuration restoration on errors, and a complete mocked 12-security collection plus existing-output preservation. Live network behavior still requires verification on the user's next run.

Upstream implementation checked: https://github.com/ranaroussi/yfinance/blob/main/yfinance/scrapers/history.py
