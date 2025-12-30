import json, os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import OpenAI


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def chunk_list(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i+size]


def embed_texts(client, texts, model="text-embedding-3-small"):
    resp = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in resp.data]


def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not found")

    openai_client = OpenAI(api_key=api_key)

    rows = load_jsonl(Path("data/shopify_products.jsonl"))
    rows = [r for r in rows if r.get("text") and r.get("title")]
    print("Loaded:", len(rows), "products")

    chroma_client = chromadb.PersistentClient(path="chroma_db")
    try:
        chroma_client.delete_collection(name="shopify_products")
    except Exception:
        pass
    collection = chroma_client.create_collection(name="shopify_products")

    ids = [r["id"] for r in rows]
    documents = [r["text"][:4000] for r in rows]  # cap for cost



    metadatas = []
    for r in rows:
        md = r.get("metadata", {}) or {}
        tags = md.get("tags", "")
        if isinstance(tags, list):
            tags = ", ".join(str(t) for t in tags)
        metadatas.append({
            "source": r.get("source", "shopify_product"),
            "url": r.get("url", ""),
            "title": r.get("title", ""),
            "domain": md.get("domain", ""),
            "vendor": md.get("vendor", ""),
            "product_type": md.get("product_type", ""),
            "price": md.get("price", None),
            "currency": md.get("currency", "USD"),
            "tags": tags,
        })

    BATCH_SIZE = 50
    total = 0
    for id_b, doc_b, meta_b in zip(chunk_list(ids, BATCH_SIZE),
                                   chunk_list(documents, BATCH_SIZE),
                                   chunk_list(metadatas, BATCH_SIZE)):
        emb = embed_texts(openai_client, doc_b)
        collection.upsert(ids=id_b, documents=doc_b, metadatas=meta_b, embeddings=emb)
        total += len(id_b)
        print(f"Upserted {total}/{len(ids)}")

    print("Done. Chroma collection: shopify_products")


if __name__ == "__main__":
    main()
