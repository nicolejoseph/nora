import os
from dotenv import load_dotenv

import chromadb
from openai import OpenAI

# COLLECTION_TO_QUERY = "browsing_memory"
COLLECTION_TO_QUERY = "shopify_products"

def embed_query(openai_client, text, model="text-embedding-3-small"):
    resp = openai_client.embeddings.create(model=model, input=[text])
    return resp.data[0].embedding


def pretty_print(results):
    ids = results.get("ids", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    print("\n=== RESULTS ===")
    for i in range(len(ids)):
        md = metas[i] or {}
        print(f"\n[{i+1}] distance={dists[i]:.4f}")
        print(f"    title:  {md.get('title','')}")
        print(f"    url:    {md.get('url','')}")
        print(f"    domain: {md.get('domain','')}")
        print(f"    price:  {md.get('price', None)} {md.get('currency','')}")


def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not found in environment/.env")

    openai_client = OpenAI(api_key=api_key)

    client = chromadb.PersistentClient(path="chroma_db")
    collection = client.get_or_create_collection(name=COLLECTION_TO_QUERY)

    print(f"Collection count: {collection.count()}")

    while True:
        q = input("\nEnter a query (or 'q' to quit): ").strip()
        if q.lower() in {"q", "quit", "exit"}:
            break

        q_emb = embed_query(openai_client, q, model="text-embedding-3-small")

        results = collection.query(
            query_embeddings=[q_emb],
            n_results=5,
            include=["metadatas", "distances"],
        )
        pretty_print(results)


if __name__ == "__main__":
    main()
