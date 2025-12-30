import json
from pathlib import Path

import requests


def fetch_products_json(store_domain, timeout=20):
    url = f"https://{store_domain}/products.json?limit=250"
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.json()


def product_to_record(store_domain, p):
    # keep it simple: pick first variant for price
    variants = p.get("variants", []) or []
    price = None
    if variants and variants[0].get("price"):
        try:
            price = float(variants[0]["price"])
        except Exception:
            price = None

    title = p.get("title", "")
    handle = p.get("handle", "")
    url = f"https://{store_domain}/products/{handle}" if handle else f"https://{store_domain}"

    text = f"{title}\n{p.get('vendor','')}\n{p.get('product_type','')}\n{p.get('body_html','')}"
    # crude html strip not required yet; embeddings can handle it

    return {
        "id": f"{store_domain}::{p.get('id')}",
        "source": "shopify_product",
        "url": url,
        "title": title,
        "text": text,
        "metadata": {
            "domain": store_domain,
            "vendor": p.get("vendor", ""),
            "product_type": p.get("product_type", ""),
            "price": price,
            "currency": "USD",  # Shopify json often lacks currency; ok for prototype
            "tags": p.get("tags", ""),
        },
    }


def main():
    stores_path = Path("data/shopify_stores.txt")  # one domain per line
    out_path = Path("data/shopify_products.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    stores = [s.strip() for s in stores_path.read_text(encoding="utf-8").splitlines() if s.strip()]
    print("stores:", len(stores))

    written = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for store in stores:
            try:
                data = fetch_products_json(store)
                products = data.get("products", []) or []
                for p in products:
                    rec = product_to_record(store, p)
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    written += 1
                print(f"[OK] {store}: {len(products)} products")
            except Exception as e:
                print(f"[FAIL] {store}: {e}")

    print("Wrote:", out_path, "records:", written)


if __name__ == "__main__":
    main()
