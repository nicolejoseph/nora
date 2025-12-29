"""
Common Windows gotchas: 

Chrome must be closed or the History DB copy can fail / be inconsistent.

If you use multiple Chrome profiles, Default might not be yours. If results look wrong, your history may be in:

User Data/Profile 1/History, etc.

If that happens, adjust get_default_history_path_windows() to look across profiles.

"""

from pathlib import Path
from src.ingest.chrome_history import (
    export_history_last_n_days,
    get_chrome_history_path_windows,
)
from src.ingest.url_filter import load_history_jsonl, filter_urls, save_urls_json


def main():
    data_dir = Path("data")
    history_path = data_dir / "history.jsonl"
    urls_path = data_dir / "urls_to_scrape.json"

    chrome_db = get_chrome_history_path_windows()

    visits = export_history_last_n_days(
        chrome_db,
        history_path,
        days=30,
        limit=30000,
    )
    print(f"Exported {len(visits)} visits")

    rows = load_history_jsonl(history_path)
    urls = filter_urls(rows, max_urls=80)
    save_urls_json(urls_path, urls)
    print(f"Selected {len(urls)} URLs to scrape")


if __name__ == "__main__":
    main()
