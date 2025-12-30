import os
from dotenv import load_dotenv

import chromadb
from openai import OpenAI


def embed_query(client, text, model="text-embedding-3-small"):
    resp = client.embeddings.create(model=model, input=[text])
    return resp.data[0].embedding


def get_browsing_signals(openai_client, question, k=6):
    """Retrieve top-k browsing items related to the user question."""
    chroma = chromadb.PersistentClient(path="chroma_db")
    col = chroma.get_or_create_collection("browsing_memory")

    q_emb = embed_query(openai_client, question)
    res = col.query(
        query_embeddings=[q_emb],
        n_results=k,
        include=["metadatas"],
    )

    metas = res["metadatas"][0]
    titles = [m.get("title", "") for m in metas if m.get("title")]
    domains = [m.get("domain", "") for m in metas if m.get("domain")]
    return titles, domains, metas


def recommend_from_shopify(openai_client, preference_text, k=8):
    """Query shopify_products with an embedding built from preference_text."""
    chroma = chromadb.PersistentClient(path="chroma_db")
    col = chroma.get_or_create_collection("shopify_products")

    q_emb = embed_query(openai_client, preference_text)
    res = col.query(
        query_embeddings=[q_emb],
        n_results=k,
        include=["metadatas", "distances"],
    )

    metas = res["metadatas"][0]
    dists = res["distances"][0]
    recs = []
    for m, d in zip(metas, dists):
        recs.append({
            "title": m.get("title", ""),
            "url": m.get("url", ""),
            "domain": m.get("domain", ""),
            "vendor": m.get("vendor", ""),
            "product_type": m.get("product_type", ""),
            "price": m.get("price", None),
            "currency": m.get("currency", "USD"),
            "score": d,
        })
    return recs


def recommend(question, n_recs=8):
    """
    Minimal recommender:
    - Use browsing memory to infer preference terms
    - Query Shopify index for similar products
    """
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Step 1: Pull signals from browsing
    titles, domains, _ = get_browsing_signals(client, question, k=6)

    # Step 2: Build a preference query (simple + effective)
    # Use question + top titles (keeps it grounded in what you browsed)
    preference_text = question + "\n" + "\n".join(titles[:6])

    # Step 3: Query Shopify products
    recs = recommend_from_shopify(client, preference_text, k=n_recs)
    return {
        "preference_text": preference_text,
        "browsing_titles": titles,
        "browsing_domains": domains,
        "recommendations": recs,
    }


if __name__ == "__main__":
    q = input("Recommend based on: ").strip()
    out = recommend(q, n_recs=8)

    print("\nPreference text used:\n", out["preference_text"][:500], "...\n")

    print("Top recommendations:")
    for r in out["recommendations"]:
        price = r["price"]
        price_str = f"${price:.2f}" if isinstance(price, (int, float)) else ""
        print(f"- {r['title']} {price_str} | {r['url']}")
