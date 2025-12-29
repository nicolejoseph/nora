import json
import os
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def chrome_time_to_datetime(chrome_us):
    # Chrome timestamps: microseconds since 1601-01-01 UTC
    chrome_epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
    return chrome_epoch + timedelta(microseconds=chrome_us)


def extract_domain(url):
    try:
        no_scheme = url.split("://", 1)[-1]
        return no_scheme.split("/", 1)[0].lower()
    except Exception:
        return ""


def get_chrome_history_path_windows():
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        raise RuntimeError("LOCALAPPDATA not found")
    return (
        Path(local_appdata)
        / "Google"
        / "Chrome"
        / "User Data"
        / "Default"
        / "History"
    )


def export_history_last_n_days(
    history_db_path,
    output_jsonl_path,
    days=30,
    limit=5000,
):
    output_jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    # Chrome locks the DB → copy it first
    temp_db = output_jsonl_path.parent / "History_copy.sqlite"
    if temp_db.exists():
        temp_db.unlink()
    shutil.copy2(history_db_path, temp_db)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    results = []

    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    query = """
    SELECT urls.url, urls.title, visits.visit_time
    FROM urls
    JOIN visits ON urls.id = visits.url
    ORDER BY visits.visit_time DESC
    LIMIT ?
    """

    cursor.execute(query, (limit,))
    rows = cursor.fetchall()

    for url, title, visit_time in rows:
        if not url:
            continue

        visited_dt = chrome_time_to_datetime(visit_time)
        if visited_dt < cutoff:
            break

        record = {
            "url": url,
            "title": title or "",
            "visited_at": visited_dt.isoformat(),
            "domain": extract_domain(url),
        }
        results.append(record)

    conn.close()
    temp_db.unlink(missing_ok=True)

    # Write JSON Lines
    with open(output_jsonl_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    return results
