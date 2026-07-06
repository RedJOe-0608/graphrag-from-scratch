"""Streamlit chat frontend for the GraphRAG API.

A thin HTTP client: it posts questions to the FastAPI /query endpoint and
renders the answer plus its sources (retrieved chunks + graph facts) as proof
of where the answer came from.
"""

import requests
import streamlit as st

API_URL = "http://localhost:8000/query"

st.set_page_config(page_title="GraphRAG Chat", page_icon="🔎")
st.title("🔎 GraphRAG Chat")

# Streamlit re-runs this whole script on every interaction, so the conversation
# must live in session_state to survive re-runs.
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {role, content, sources?}


def render_sources(sources: dict) -> None:
    # We only surface the retrieved passages as proof. Graph facts still reach
    # the LLM and can be what surfaced a chunk in the first place, but they're
    # an internal signal, not something we show the user.
    chunks = sources.get("chunks", [])
    with st.expander(f"📎 Sources — {len(chunks)} chunks"):
        if chunks:
            for i, c in enumerate(chunks, 1):
                st.markdown(f"**[{i}] doc `{c['document_id']}` · chunk `{c['id']}`**")
                st.write(c["text"])
                st.divider()
        else:
            st.caption("No sources returned for this answer.")


# Replay the conversation so far.
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            render_sources(msg["sources"])

# New question.
if prompt := st.chat_input("Ask a question about your documents..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Retrieving and generating..."):
                resp = requests.post(API_URL, json={"query": prompt}, timeout=180)
                resp.raise_for_status()
                data = resp.json()
        except requests.RequestException as exc:
            error = f"⚠️ Could not reach the API: {exc}"
            st.error(error)
            st.session_state.messages.append(
                {"role": "assistant", "content": error}
            )
        else:
            st.markdown(data["answer"])
            sources = {"chunks": data["chunks"], "facts": data["facts"]}
            render_sources(sources)
            st.session_state.messages.append(
                {"role": "assistant", "content": data["answer"], "sources": sources}
            )
