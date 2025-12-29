import json
import os
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
        yield lst[i : i + size]


def embed_texts(client, texts, model="text-embedding-3-small"):
    # OpenAI embeddings API: returns one vector per input string
    resp = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in resp.data]


def main():
    load_dotenv()  # loads OPENAI_API_KEY from .env
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not found. Put it in your .env or environment variables.")

    openai_client = OpenAI(api_key=api_key)

    data_path = Path("data/page_docs.jsonl")
    rows = load_jsonl(data_path)

    rows = [
        r for r in rows
        if r.get("text_for_embedding")
        and len(r["text_for_embedding"].strip()) > 40
        and "block response" not in r["text_for_embedding"].lower()
    ]
    print(f"Loaded {len(rows)} page docs with usable text_for_embedding")

    # Dedupe by id (keep the first occurrence)
    unique = {}
    for r in rows:
        unique[r["id"]] = r
    rows = list(unique.values())
    print(f"After dedupe: {len(rows)} unique docs")

    # Persistent Chroma on disk
    chroma_client = chromadb.PersistentClient(path="chroma_db")
    try:
        chroma_client.delete_collection(name="browsing_memory")
    except Exception:
        pass
    collection = chroma_client.create_collection(name="browsing_memory")

    # Prepare fields
    ids = [r["id"] for r in rows]
    documents = [r.get("text_for_embedding", r["text"]) for r in rows]

    # Flatten metadata for easier filtering later
    metadatas = []
    for r in rows:
        md = r.get("metadata", {}) or {}
        metadatas.append({
            "source": r.get("source", "history_page"),
            "url": r.get("url", ""),
            "title": r.get("title", ""),
            "domain": md.get("domain", ""),
            "timestamp": md.get("timestamp", ""),
            "price": md.get("price", None),
            "currency": md.get("currency", "USD"),
            "canonical_url": md.get("canonical_url", ""),  
            "norm_url": md.get("norm_url", ""),            
        })


    # Batch embeddings to avoid huge requests
    BATCH_SIZE = 25
    total_added = 0

    for idx_batch, doc_batch, meta_batch in zip(
        chunk_list(ids, BATCH_SIZE),
        chunk_list(documents, BATCH_SIZE),
        chunk_list(metadatas, BATCH_SIZE),
    ):
        embeddings = embed_texts(openai_client, doc_batch, model="text-embedding-3-small")
        collection.upsert(
            ids=idx_batch,
            documents=doc_batch,
            metadatas=meta_batch,
            embeddings=embeddings,
        )
        total_added += len(idx_batch)
        print(f"Upserted {total_added}/{len(ids)}")

    print("Done. Chroma collection: browsing_memory (persisted in ./chroma_db)")


if __name__ == "__main__":
    main()
