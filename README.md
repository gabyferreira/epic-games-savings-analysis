# 🎮 Epic Games Store: Automated Savings Tracker

[![Data Update](https://github.com/gabyferreira/epic-games-savings-analysis/actions/workflows/update_data.yml/badge.svg)](https://github.com/gabyferreira/epic-games-savings-analysis/actions/workflows/update_data.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

An automated data pipeline that monitors the Epic Games Store for free game giveaways, fetches their historical retail prices, and maintains a clean dataset for savings analysis.

---

### 📊 Live Project Statistics
<a name="stats_start"></a>
| Metric | Statistics |
| :--- | :--- |
| 💰 **Total Market Value** | **$14,595.04** |
| 📦 **Total Games Collected** | 647 |
| 📉 **Average Game Price** | $22.56 |
| 🏆 **Most Valuable Game** | Civilization 6 Platinum Edition ($79.99) |
| 🏢 **Top 3 Contributors** | 2K ($639.88), Bethesda Softworks ($544.80), Paradox Interactive ($409.89) |
| 👑 **MVP Publisher** | Bethesda Softworks (20 games) |
| 📈 **Inflation-Adjusted Value** | $16,611.15 |
| 💸 **Purchasing Power Gained** | $2,016.11 |
| 🗓️ **Peak Saving Month** | 🎄 **Seasonality Peak:** December is historically the best month, offering $3,388.17 in savings. |
| 🏆 **Generosity Leaderboard** | 2K (Score: 92.9), Bethesda Softworks (Score: 71.3), Paradox Interactive (Score: 60.8) |
| ⭐ **Average User/Critic Score** | 76.7/100 |
| 💎 **Highest Rated Title** | Cassette Beasts (100.0/100) |
| 💳 **Subscription Equivalent** | **$171.71 / month** |
| 📅 **Tracking Since** | December 2018 (85 months) |

<a name="stats_end"></a>
---

## 🚀 How it Works (The Pipeline)
This project is built as a modular **ETL (Extract, Transform, Load)** pipeline:

1. **Extraction** 🛰️
**Source:** Direct polling of the Epic Games Store GraphQL API.

**Logic:** Identifies active "free-to-keep" promotions.

2. **Enrichment & Data Fusion (Transformation)** 🧪
This stage performs Data Reconciliation to build a comprehensive metadata profile for every title:

* **Economic Indexing:** Calculates Real Value by applying historical CPI-based multipliers to adjust 2018–2025 prices into 2026 purchasing power.

* **Cross-Platform Mapping:** Looks up prices from CheapShark, publisher info from Steam, and ratings and release dates from IGDB/Twitch.

* **Fuzzy Matching:** Uses a Levenshtein Distance algorithm to resolve naming inconsistencies (e.g., matching "STAR WARS™: Squadrons" to "Star Wars: Squadrons").

* **State Persistence:** Saves data in JSON files so it doesn’t have to download the same information over and over.

3. **Analytics & Visualisation**  📈
The program takes the raw CSV data and turns it into useful insights.

* **Quality Pulse:** It looks for trends, like whether the free games are getting better or worse over time.

* **Subscription Benchmarking:** Calculates a Monthly Subscription Equivalent to compare giveaway value against industry standards like Xbox Game Pass.

4. **Validation & Automation** 🤖
* **Data Checks:** Makes sure there are no duplicate games and that the data is in the correct format.

* **CI/CD Orchestration:** Everything runs automatically each day using GitHub Actions, including updating the data and rebuilding the charts.



## 🛠️ Tech Stack & Architecture
* **Language:** Python 3.x
* **Data Handling:** Pandas (CSV-based persistence)
* **Automation:** GitHub Actions (CI/CD)
* **Observability:** Integrated logging system (Daily health reports)
* **APIs:** Epic Games Store, CheapShark, Steam, IGDB

## 📂 Project Structure
```text
├── .github/workflows/
│   └── update_data.yml        # CI/CD: Automated daily execution via GitHub Actions
├── assets/                    # Generated charts (Inflation, Quality Pulse, etc.)
├── data/
│   └── epic_games_data.csv    # Primary Dataset: Persistent CSV storage
├── logs/                      # Observability: Daily execution and API health logs
├── src/
│   ├── analytics.py           # Business Logic: CAC and subscription value modeling
│   ├── constants.py           # Configuration: Inflation rates and STEAM Sales
│   ├── processor.py           # ETL Engine: Data cleaning and normalization
│   ├── scraper.py             # Extraction: API orchestrator for Epic, Steam, and IGDB
│   └── visualiser.py          # Data Science: Matplotlib logic and trendline generation
├── game_prices.json           # State Persistence: Local metadata and price cache
└── requirements.txt           # Environment: Project dependencies
