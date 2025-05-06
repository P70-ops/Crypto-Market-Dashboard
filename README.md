# Crypto-Market-Dashboard
Thought for a few seconds


Below is a concise **feature summary** of your Dash‑based Crypto Market Dashboard, organized by functional area:

| Feature Area                | Key Capabilities                                                                                                                                        |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Data Fetching & Caching** | • `ccxt` + Binance spot API with rate‑limit support<br>• Retry logic (`fetch_with_retry`) for resilience<br>• Flask‑Caching (`SimpleCache`) for symbols |
| **Symbol Selection**        | • Loads all active USDT markets<br>• Filters by 24 h volume (> 2 500 000)<br>• Caps to top 100 symbols                                                  |
| **Indicator Calculations**  | • Vectorized RSI (14‑period)<br>• 24 h & 7 day % price change<br>• Annualized volatility<br>• VWAP, support & resistance levels<br>• 24 h volume        |
| **Concurrency**             | • `ThreadPoolExecutor` (max 12 workers) for parallel symbol analysis                                                                                    |
| **Dashboard Layout**        | • Dark theme via CSS variables & Plotly’s `plotly_dark` template<br>• Responsive grid for stats cards<br>• Custom Google Font (Inter)                   |
| **Visualizations**          | • **RSI Overview** scatter with size ∝ log(volume)<br>• Combined 24 h/7 d change histograms<br>• Volatility vs. price‑change scatter                    |
| **Interactive Table**       | • `dash_table.DataTable` with native sort & filter<br>• Conditional cell styling for RSI overbought/oversold<br>• Formats (currency, % with signs)      |
| **Live Refresh**            | • `dcc.Interval` triggers every 10 s<br>• Callback rebuilds dashboard & updates “Last Update” timestamp                                                 |

---

This structure ensures high performance (through caching and threading), rich technical analysis (RSI, volatility, VWAP, etc.), and an engaging, real‑time UI with both charts and a fully interactive data table.

## 🚀 Roadmap

| Phase     | Focus Areas                             | Milestones & Deliverables                                                                 | Timeline      |
|-----------|-----------------------------------------|-------------------------------------------------------------------------------------------|---------------|
| **Phase 1** | Project Initialization & UI            | • Create `templates/`, `uploads/`, `downloads/` dirs<br>• Scaffold `app.py` & basic layout | Week 1         |
| **Phase 2** | Authentication & Agent Management     | • Flask‑Login + WTForms auth<br>• CSRF protection<br>• Agent listing & detail views       | Weeks 2–3      |
| **Phase 3** | Command Execution & Scheduling        | • File upload/download endpoints<br>• Command send UI/API<br>• One‑time/recurring jobs     | Weeks 4–5      |
| **Phase 4** | Results, Files & Statistics           | • Render command output<br>• Download manager UI<br>• Timeline & charts (Chart.js/Plotly) | Weeks 6–7      |
| **Phase 5** | Admin Panel & Polishing               | • User management UI<br>• Theme toggle persistence<br>• Session timeout settings<br>• Final tests & docs | Weeks 8–9      |

---

## 🛠️ Setup & Installation

| Step | Command                                                                                       | Description                                            |
|------|-----------------------------------------------------------------------------------------------|--------------------------------------------------------|
| 1    | `mkdir -p templates uploads downloads`                                                        | Create required directories                            |
| 2    | *(Place your `.html` files in the `templates/` folder)*                                       | HTML Jinja2 templates                                  |
| 3    | *(Save your Flask app as `app.py` in project root)*                                           | Main application entry                                 |
| 4    | `pip install flask dash plotly ccxt flask-caching python-dateutil humanize pytz`               | Install Python dependencies                            |
| 5    | `python app.py`                                                                               | Run the server on `http://0.0.0.0:8080` (or adjust host/port) |
| 6    | 🔑 **Default admin:** `admin` / `admin`                                                        | First-time login credentials                           |

---

### 📦 Dependencies

| Package             | Purpose                                | Version Constraint      |
|---------------------|----------------------------------------|-------------------------|
| `flask`             | Web framework                          | `>=2.0`                 |
| `dash`              | Interactive dashboard                  | `>=2.0`                 |
| `plotly`            | Charts & figures                       | `>=5.0`                 |
| `ccxt`              | Crypto exchange data                   | `>=2.0`                 |
| `flask-caching`     | Caching layer for symbol lookups       | `>=1.0`                 |
| `python-dateutil`   | Flexible date parsing                  | `>=2.8`                 |
| `humanize`          | Friendly number formatting             | `>=4.0`                 |
| `pytz`              | Timezone handling                      | `>=2021.0`              |


![marketdashboard002](https://github.com/user-attachments/assets/8f5830c7-6da8-4c10-8074-a7da5f5d438e)
![marketdashboard001](https://github.com/user-attachments/assets/b399eb67-7832-4abf-99a2-302857e78dd9)
