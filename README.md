# Chat With Your Shopping History 🛍️

Chat with your browsing history and get grounded answers and recommendations.

This prototype indexes your Chrome browsing history (e.g. shopping sites), scrapes page content, and stores it in a local vector database. You can then ask questions like *"What turtlenecks do I like?"* or *"Summarize my shopping habits"* and get answers backed by the pages you’ve visited. For recommendation-style queries (*"recommend similar ..."*, *"find alternatives to ..."*), it combines your browsing signals with a product catalog (e.g. Shopify) to suggest items.

---

## Features

- **Browsing memory**: Export Chrome history → filter shopping-related URLs → scrape with Playwright → embed and index in [ChromaDB](https://www.trychroma.com/).
- **Q&A over your history**: Ask natural-language questions; answers are grounded in the scraped content with source citations.
- **Recommendations**: For phrases like "recommend similar" or "find alternatives", the app uses your browsing preferences plus a product index (e.g. Shopify) to suggest items.
- **Streamlit chat UI**: Simple chat interface with a light purple theme and an optional "Sources used" expander.

---

## Tech Stack

- **Python 3** — app and pipelines
- **Streamlit** — chat UI
- **ChromaDB** — vector store (browsing memory + optional product catalog)
- **OpenAI** — embeddings (`text-embedding-3-small`) and chat (`gpt-4o-mini`)
- **Playwright** — scraping product pages
- **Chrome History** — SQLite export on Windows (configurable for other profiles)

---

## Prerequisites

- Python 3.10+
- [Chrome](https://www.google.com/chrome/) (for history export; Note that you must close Chrome before running the history export step)
- [OpenAI API key](https://platform.openai.com/api-keys) (for embeddings and chat)

---

## Setup

### 1. Clone and enter the app directory

```bash
cd shopping-memory
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

Install Playwright browsers (needed for the scrape step):

```bash
playwright install
```

### 3. Environment variables

Create a `.env` file in `shopping-memory/` (or project root as needed):

```env
OPENAI_API_KEY=sk-your-key-here
```

The app loads this via `python-dotenv`.

---

## Data pipeline

### Part 1: Export history → filter URLs → scrape → index (browsing memory)

From `shopping-memory/` (with `shopping-memory` as the current directory so imports resolve):

1. **Export Chrome history** (Windows):  
   Exports the last 30 days of visits to `data/history.jsonl`, then filters to shopping-related URLs and writes `data/urls_to_scrape.json`.

   ```bash
   python -m src.ingest.run_part1
   ```

   **Note:** Close Chrome before running, or the History DB copy may fail. If you use multiple Chrome profiles, you may need to point to `User Data/Profile 1/History` (see `src/ingest/chrome_history.py` and `run_part1.py`).

2. **Scrape and build Chroma index**:  
   Run the Playwright scraper and the Chroma indexing script (see `src/ingest/playwright_fetch.py` and `src/index/build_browsing_chroma.py`) so that `chroma_db` contains a `browsing_memory` collection.

After this, the chat app can answer questions from your browsing memory.

### Optional: Shopify product index

To enable recommendations, you need a `shopify_products` collection in Chroma. Use the Shopify fetch and index scripts (e.g. `src/ingest/shopify_fetch.py`, `src/index/build_shopify_chroma.py`) as configured for your store/API. Without this, only browsing-memory Q&A is available; recommendation-style queries may fall back or error depending on the code path.

---

## Run the app

From `shopping-memory/`:

```bash
python -m streamlit run src/app/streamlit_app.py
```

Open the URL shown in the terminal (e.g. `http://localhost:8501`). You can ask:

- **Q&A:** *"What shoes do I like?"*, *"Summarize my shopping habits."*
- **Recommendations:** *"Recommend similar items"*, *"Find alternatives to X."*

The UI shows an optional **Sources used** expander with titles, domains, and URLs for the retrieved chunks.

---

## Project structure

```
<project-root>/
├── README.md
├── .gitignore
└── shopping-memory/
    ├── requirements.txt
    ├── data/                    # history.jsonl, urls_to_scrape.json (gitignored)
    ├── chroma_db/               # ChromaDB data (gitignored)
    ├── src/
    │   ├── app/
    │   │   └── streamlit_app.py  # Chat UI
    │   ├── ingest/
    │   │   ├── chrome_history.py # Chrome History export (Windows)
    │   │   ├── run_part1.py      # Export + filter URLs
    │   │   ├── url_filter.py     # Filter shopping URLs
    │   │   ├── playwright_fetch.py
    │   │   └── shopify_fetch.py
    │   ├── index/
    │   │   ├── build_browsing_chroma.py
    │   │   ├── build_shopify_chroma.py
    │   │   └── query_browsing_chroma.py
    │   └── llm/
    │       ├── answer_from_memory.py  # Q&A over browsing_memory
    │       └── recommender.py         # Recommendations (browsing + shopify_products)
    └── tests/
        └── test_url_filter.py
```

---
