import json
from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit


TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign",
    "utm_term", "utm_content", "gclid", "fbclid"
}

SHOPPING_KEYWORDS = [
    "/product", "/products/", "/p/", "/dp/", "shop", "sale"
]

EXCLUDED_DOMAINS = [
    "mail.google.com",
    "calendar.google.com",
    "github.com",
    "youtube.com",
    "docs.google.com/document",
    "linkedin.com",
    "chatgpt.com",
    "accounts.google.com",
    "shopwithaira.com",
    "calendly.com",
    "localhost"
]


def normalize_url(url):
    parts = urlsplit(url)
    query = [
        (k, v)
        for (k, v) in parse_qsl(parts.query)
        if k not in TRACKING_PARAMS
    ]
    query.sort()
    clean_query = urlencode(query)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, clean_query, ""))


def looks_like_shopping(url, title, domain):
    url = url.lower()
    title = (title or "").lower()
    domain = (domain or "").lower()

    if any(bad in domain for bad in EXCLUDED_DOMAINS):
        return False

    if any(k in url for k in SHOPPING_KEYWORDS):
        return True

    if any(k in title for k in ["shoe", "dress", "jacket", "bag", "watch"]):
        return True

    return False


def load_history_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def filter_urls(history_rows, max_urls=80):
    deduped = {}

    for r in history_rows:
        url = r.get("url", "")
        if not url.startswith("http"):
            continue

        if not looks_like_shopping(url, r.get("title"), r.get("domain")):
            continue

        norm = normalize_url(url)

        if norm not in deduped or r["visited_at"] > deduped[norm]["visited_at"]:
            deduped[norm] = {
                "url": url,
                "norm_url": norm,
                "title": r.get("title"),
                "domain": r.get("domain"),
                "visited_at": r.get("visited_at"),
            }

    # sort by most recent
    urls = sorted(
        deduped.values(),
        key=lambda x: x["visited_at"],
        reverse=True
    )

    return urls[:max_urls]


def save_urls_json(path, urls):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(urls, f, indent=2)
