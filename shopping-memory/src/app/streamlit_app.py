# Run with:
# python -m streamlit run src/app/streamlit_app.py

import os

import chromadb
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from src.llm.answer_from_memory import answer_from_memory
from src.llm.recommender import recommend

AVATARS = {
    "assistant": "🤖",  
    "user": "👤",       
}

# Use this simple helper function to route to correct chroma db collection
def is_reco_query(q: str) -> bool:
    q = (q or "").lower()
    triggers = ["recommend", "recommendation", "alternatives", "alternative", "similar", "find me", "find alternatives", "find other"]
    return any(t in q for t in triggers)

def embed_query(client, text, model="text-embedding-3-small"):
    resp = client.embeddings.create(model=model, input=[text])
    return resp.data[0].embedding


def get_sources(question, k=5):
    """Fetch top-k sources from Chroma for display (evidence panel)."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []

    client = OpenAI(api_key=api_key)
    q_emb = embed_query(client, question)

    chroma = chromadb.PersistentClient(path="chroma_db")
    col = chroma.get_or_create_collection("browsing_memory")

    results = col.query(
        query_embeddings=[q_emb],
        n_results=k,
        include=["metadatas", "distances"],
    )

    metas = results["metadatas"][0]
    dists = results["distances"][0]
    out = []
    for m, d in zip(metas, dists):
        out.append({
            "title": (m or {}).get("title", ""),
            "url": (m or {}).get("url", ""),
            "domain": (m or {}).get("domain", ""),
            "distance": d,
        })
    return out


def set_styles():
    st.markdown(
        """
        <style>
          .stApp { background: #fbf7ff; } /* light purple theme */
          [data-testid="stHeader"] { background: rgba(251,247,255,0.0); }
          .chat-title {
            font-size: 1.6rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
          }
          .chat-subtitle {
            color: rgba(0,0,0,0.6);
            margin-top: 0;
          }
          .pill {
            display:inline-block;
            padding: 0.15rem 0.55rem;
            border-radius: 999px;
            background: rgba(170, 120, 255, 0.15);
            border: 1px solid rgba(170, 120, 255, 0.35);
            font-size: 0.85rem;
            margin-right: 0.35rem;
          }
          /* FIX: wrap long source text */
          div[data-testid="stExpander"] * {
            word-break: break-word;
            overflow-wrap: anywhere;
            white-space: normal;
          }

          div[data-testid="stExpander"] {
            font-size: 0.9rem;
          }

        /* Chat input (st.chat_input) focus ring / border */
        div[data-testid="stChatInput"] > div:focus-within {
        border-color: #7b4dff !important;
        box-shadow: 0 0 0 2px rgba(123, 77, 255, 0.35) !important;
        }
        div[data-testid="stChatInput"] textarea:focus {
        outline: none !important;
        box-shadow: none !important;
        }

        /* User message bubble (targets the bubble container inside the chat message) */
        div[data-testid="stChatMessage"][data-role="user"] div {
        background: rgba(190, 160, 255, 0.18) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(page_title="Shopping Memory Chat", page_icon="🪻", layout="centered")
    set_styles()

    st.markdown('<div class="chat-title">🪻 Shopping Memory Chat</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="chat-subtitle">Ask questions about your browsing history and get grounded answers ✨</p>',
        unsafe_allow_html=True
    )

    # Session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! 👋 Ask me about what you’ve been shopping for (e.g., “What turtlenecks do I like?”)."}
        ]

    # Render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar=AVATARS.get(msg["role"])):
            st.markdown(msg["content"])

    # Input
    user_q = st.chat_input("Try: “What shoes do I like?” or “Summarize my shopping habits.”")
    if user_q:
        st.session_state.messages.append({"role": "user", "content": user_q})
        with st.chat_message("user", avatar=AVATARS["user"]):
            st.markdown(user_q)

        with st.chat_message("assistant", avatar=AVATARS["assistant"]):
            with st.spinner("Thinking… 🧠"):
                try:
                    if is_reco_query(user_q):
                        out = recommend(user_q, n_recs=8)
                        recs = out["recommendations"]

                        lines = ["Here are some picks based on your browsing 🛍️:"]
                        for r in recs:
                            price = r.get("price")
                            price_str = f"${price:.2f}" if isinstance(price, (int, float)) else ""
                            title = r.get("title") or "(no title)"
                            url = r.get("url") or ""
                            lines.append(f"- **{title}** {price_str}\n  {url}")

                        answer = "\n".join(lines)
                        sources = []  # don't show browsing sources for recommender replies by default
                    else:
                        answer = answer_from_memory(user_q, k=6)
                        sources = get_sources(user_q, k=6)

                except Exception as e:
                    st.error(f"Error: {e}")
                    return

            st.markdown(answer)

            # Evidence (optional, but great for demos)
            sources = []
            try:
                sources = get_sources(user_q, k=6)
            except Exception:
                sources = []

            if sources:
                with st.expander("🔎 Sources used"):
                    for s in sources:
                        title = s["title"] or "(no title)"
                        url = s["url"] or ""
                        domain = s["domain"] or ""
                        st.markdown(f"- **{title}**  \n  {domain}  \n  {url}")

        st.session_state.messages.append({"role": "assistant", "content": answer})

    st.markdown("---")
    st.markdown(
        """
        <span class="pill">Part 1</span>
        <span class="pill">Chroma</span>
        <span class="pill">OpenAI</span>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
