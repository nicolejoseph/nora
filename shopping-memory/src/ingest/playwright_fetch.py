import json
import re
from datetime import datetime, timezone
from pathlib import Path
import hashlib
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import sync_playwright


PRICE_RE = re.compile(r"\$ ?\d{1,3}(?:,\d{3})*(?:\.\d{2})?")

def stable_id_from_url(url):
    # Create a stable ID from the URL so small differences in query params don't cause mismatches.
    return hashlib.sha1(url.encode("utf-8")).hexdigest()

def drop_query_and_fragment(url):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def load_urls(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_text(page):
    # Try main content first, then fallback
    try:
        main = page.locator("main")
        if main.count() > 0:
            txt = main.first.inner_text(timeout=2000)
            if txt and len(txt.strip()) > 200:
                return txt
    except Exception:
        pass

    try:
        return page.locator("body").inner_text(timeout=2000)
    except Exception:
        return ""


def guess_price(text):
    if not text:
        return None
    m = PRICE_RE.search(text)
    if not m:
        return None
    # Convert "$129.99" -> 129.99 (best-effort)
    raw = m.group(0).replace("$", "").replace(",", "").strip()
    try:
        return float(raw)
    except Exception:
        return None

def build_record(url_row, title, text, price):
    # Unified schema (works for Part 1 + Part 2)
    norm = url_row.get("norm_url") or url_row.get("url") or ""
    canonical = drop_query_and_fragment(norm)  # stable across runs

    record = {
        "id": stable_id_from_url(canonical),   # stable ID
        "source": "history_page",
        "url": url_row.get("url", ""),
        "title": title or url_row.get("title", ""),
        "text": text,
        "metadata": {
            "domain": url_row.get("domain", ""),
            "timestamp": url_row.get("visited_at", ""),
            "price": price,
            "currency": "USD",
            "brand": None,
            "category": None,
            "tags": [],
            "norm_url": norm,                  # keep for debugging
            "canonical_url": canonical,        # keep for debugging
        },
    }

    record["text_for_embedding"] = clean_for_embedding(record["title"], record["text"])
    return record


def fetch_pages(url_records, out_jsonl_path, limit=10, headless=True):
    out_jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        written = 0
        with open(out_jsonl_path, "w", encoding="utf-8") as f:
            for r in url_records[:limit]:
                url = r.get("url", "")
                if not url:
                    continue

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(1000)

                    # title
                    try:
                        page_title = page.title()
                    except Exception:
                        page_title = r.get("title", "")

                    # text
                    text = extract_text(page).strip()
                    if len(text) > 15000:
                        text = text[:15000]

                    # price (best-effort)
                    price = guess_price(text)

                    record = build_record(r, page_title, text, price)

                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    written += 1
                    print(f"[OK] {written}/{limit} {r.get('domain','')}")

                except Exception as e:
                    print(f"[FAIL] {url} -> {e}")

        browser.close()

    return written

def clean_for_embedding(title, text, max_chars=3000):
    # Remove lines that are usually navigation / boilerplate
    bad_line_starts = (
        "skip to", "search", "cart", "account", "returns", "orders",
        "deliver", "sign in", "customer reviews", "privacy", "terms"
    )

    lines = [ln.strip() for ln in (text or "").splitlines()]
    kept = []
    for ln in lines:
        if not ln:
            continue
        low = ln.lower()
        if any(low.startswith(s) for s in bad_line_starts):
            continue
        # drop super-short nav-like tokens
        if len(ln) <= 2:
            continue
        kept.append(ln)

    cleaned = " ".join(kept)
    cleaned = cleaned[:max_chars]
    return (title or "") + "\n" + cleaned


# Note: important for testing single links (i.e. Amazon)
def test_single_url(url):
    out_path = Path("data/single_url_test.jsonl")
    test_row = {
        "url": url,
        "norm_url": url,
        "title": "",
        "domain": "www.amazon.com",
        "visited_at": "",
    }
    fetch_pages([test_row], out_path, limit=1, headless=True)



if __name__ == "__main__":
    # Test a single url
    # from src.config_local import single_url
    # print(single_url)
    # test_single_url(single_url)

    urls_path = Path("data/urls_to_scrape.json")
    out_path = Path("data/page_docs.jsonl")

    url_records = load_urls(urls_path)
    # Note to self: Use limit as needed, when testing the code
    fetch_pages(url_records, out_path, limit=30, headless=True)
    print(f"Wrote: {out_path}")
