# Run with:
# pytest -q

from pathlib import Path
from src.ingest.url_filter import normalize_url, filter_urls


def test_normalize_url_removes_tracking():
    url = "https://example.com/products/abc?utm_source=x&gclid=123&color=red"
    norm = normalize_url(url)
    assert "utm_source" not in norm
    assert "gclid" not in norm
    assert "color=red" in norm


def test_filter_urls_dedupes_and_limits():
    rows = [
        {"url": "https://shop.com/products/a?utm_source=1", "title": "Running Shoe", "domain": "shop.com", "visited_at": "2025-12-01T00:00:00+00:00"},
        {"url": "https://shop.com/products/a?utm_source=2", "title": "Running Shoe", "domain": "shop.com", "visited_at": "2025-12-02T00:00:00+00:00"},
        {"url": "https://mail.google.com/mail/u/0/#inbox", "title": "Inbox", "domain": "mail.google.com", "visited_at": "2025-12-02T00:00:00+00:00"},
    ]
    urls = filter_urls(rows, max_urls=10)
    assert len(urls) == 1
    assert urls[0]["norm_url"].startswith("https://shop.com/products/a")
