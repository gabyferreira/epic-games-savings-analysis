# 🎮 Epic Games Store: Automated Savings Tracker

[![Data Update](https://github.com/gabyferreira/epic-games-savings-analysis/actions/workflows/update_data.yml/badge.svg)](https://github.com/gabyferreira/epic-games-savings-analysis/actions/workflows/update_data.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

An automated data pipeline that monitors the Epic Games Store for free game giveaways, fetches their historical retail prices, and maintains a clean dataset for savings analysis.

---

### 📊 Live Project Statistics
<a name="stats_start"></a>
| Metric | Statistics |
| :--- | :--- |
| 💰 **Total Market Value** | **$14,490.04** |
| 📦 **Total Games Collected** | 647 |
| 📉 **Average Game Price** | $22.40 |
| 🏆 **Most Valuable Game** | Civilization 6 Platinum Edition ($79.99) |
| 🏢 **Top 3 Contributors** | 2K ($639.88), Bethesda Softworks ($544.80), Paradox Interactive ($409.89) |
| 👑 **MVP Publisher** | Bethesda Softworks (20 games) |
| 📈 **Inflation-Adjusted Value** | $16,489.35 |
| 💸 **Purchasing Power Gained** | $1,999.31 |
| 🗓️ **Peak Saving Month** | 🎄 **Seasonality Peak:** December is historically the best month, offering $3,318.17 in savings. |
| 🏆 **Generosity Leaderboard** | 2K (Score: 92.9), Bethesda Softworks (Score: 71.3), Paradox Interactive (Score: 60.8) |

<a name="stats_end"></a>
---

## 🚀 How it Works (The Pipeline)
This project is built as a modular **ETL (Extract, Transform, Load)** pipeline:

1.  **Extraction:** A Python scraper queries the Epic Games Store API daily to identify active free promotions.
2.  **Enrichment (Transformation):** * The script cross-references titles with the **CheapShark API** to find original retail prices.
    * **Fuzzy Matching:** Uses Levenshtein distance to ensure accurate price mapping even when titles vary slightly.
    * **Caching:** Implements a local JSON cache to minimize API calls and respect rate limits.
3.  **Validation (Data Quality):** * **Deduplication:** Prevents redundant entries using a composite key of `game` + `start_date`.
    * **Schema Enforcement:** Ensures data types and date logic remain consistent.
4.  **Automation:** Powered by **GitHub Actions**, running every 24 hours.



## 🛠️ Tech Stack & Architecture
* **Language:** Python 3.x
* **Data Handling:** Pandas (CSV-based persistence)
* **Automation:** GitHub Actions (CI/CD)
* **Observability:** Integrated logging system (Daily health reports)
* **APIs:** Epic Games Store, CheapShark

## 📂 Project Structure
```text
├── .github/workflows/
│   └── update_data.yml        # Automation configuration
├── data/
│   └── epic_games_data_edited_active.csv    # The primary dataset
├── logs/                      # Daily health and error reports
├── src/
│   ├── scraper.py             # Orchestrator & API logic
│   └── processor.py           # Data validation & cleaning engine
├── game_prices.json           # Local price cache
└── requirements.txt           # Dependency list