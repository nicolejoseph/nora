import os
from dotenv import load_dotenv

import chromadb
from openai import OpenAI


def embed_query(client, text, model="text-embedding-3-small"):
    resp = client.embeddings.create(model=model, input=[text])
    return resp.data[0].embedding


def answer_from_memory(question, k=5):
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    chroma = chromadb.PersistentClient(path="chroma_db")
    col = chroma.get_or_create_collection("browsing_memory")

    q_emb = embed_query(client, question)

    results = col.query(
        query_embeddings=[q_emb],
        n_results=k,
        include=["documents", "metadatas"],
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]

    context = ""
    for i, (d, m) in enumerate(zip(docs, metas)):
        context += f"\nSource {i+1}:\nTitle: {m.get('title')}\nURL: {m.get('url')}\nContent:\n{d}\n"

    prompt = f"""
You are a personal shopping assistant.

Answer the user's question using ONLY the sources below.
If the sources don’t clearly support a claim, say it's a best guess and point to what you do see in the sources.
Cite sources using the provided URLs.

User question:
{question}

Sources:
{context}
"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return resp.choices[0].message.content


if __name__ == "__main__":
    while True:
        q = input("\nAsk a question (or 'q'): ").strip()
        if q.lower() in {"q", "quit"}:
            break
        print("\n" + answer_from_memory(q))
