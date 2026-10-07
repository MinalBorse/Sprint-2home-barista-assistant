# ==========================================================
# app.py
# ==========================================================
# The Home Barista Assistant - web app (version 2).
#
# What it does now:
#   - a chat window (Streamlit)
#   - QUERY TRANSLATION: rewrites the question into a better search query
#   - STRUCTURED RETRIEVAL: filters the search by brew method
#   - answers coffee questions using RAG on our knowledge base
#   - shows live progress steps while it works
#   - shows the sources and the search query it used
#   - checks the user's input
#
# Coming later (Part 4): the agent with 3 tools and memory.
#
# Run it with:   streamlit run app.py
#
# REQUIREMENTS covered:
#   - "Create an intuitive interface using Streamlit"
#   - "Implement advanced RAG with query translation and structured retrieval"
#   - "Show relevant context and sources"
#   - "Include progress indicators for long operations"
#   - "Include user input validation"
#   - "Implement proper error handling"
# ==========================================================

import streamlit as st
from src.llm import get_llm
from src.vector_store import get_vector_store, KNOWLEDGE_BASE_COLLECTION
from src.rag import plan_search, retrieve, generate_answer
from src.brew_methods import ANY


# ----------------------------------------------------------
# Settings
# ----------------------------------------------------------
MAX_QUESTION_LENGTH = 500    # longer questions are rejected (input validation)


# ==========================================================
# Load the model and database ONCE
# ==========================================================
# Streamlit re-runs this whole file every time the user does something.
# @st.cache_resource means: run this function only the FIRST time,
# then reuse the result.
@st.cache_resource
def load_resources():
    vector_store = get_vector_store(KNOWLEDGE_BASE_COLLECTION)
    llm = get_llm()
    return vector_store, llm


# ==========================================================
# Helper functions
# ==========================================================
def validate_question(question):
    """
    REQUIREMENT: "Include user input validation"
    Returns an error message, or None if the question is fine.
    """
    if len(question) == 0:
        return "Type a question first."
    if len(question) > MAX_QUESTION_LENGTH:
        return f"That question is too long. Keep it under {MAX_QUESTION_LENGTH} characters."
    return None


def show_search_query(search_query, question, brew_method=ANY):
    """Show what we searched for, and the brew-method filter (if any)."""
    parts = []
    if search_query and search_query != question:
        parts.append(f"Searched for: {search_query}")
    if brew_method and brew_method != ANY:
        parts.append(f"Filter: {brew_method} + general")
    if parts:
        st.caption("  ·  ".join(parts))


def show_sources(sources):
    """
    REQUIREMENT: "Show relevant context and sources"
    A fold-out panel listing the chunks the answer was based on.
    """
    if not sources:
        return

    with st.expander(f"Sources ({len(sources)} chunks used)"):
        for source in sources:
            heading = f"**{source['title']}**"
            if source["section"]:
                heading = heading + f" - {source['section']}"
            st.markdown(heading)
            st.caption(
                f"Similarity {source['similarity']:.2f} - "
                f"{source.get('brew_method', '')} - {source['source']}"
            )
            st.text(source["text"][:300] + "...")
            st.divider()


# ==========================================================
# The page
# ==========================================================
st.set_page_config(page_title="Home Barista Assistant", page_icon="☕")
st.title("☕ Home Barista Assistant")
st.caption("Ask about brewing methods, roasting, and fixing coffee that tastes wrong.")

# ----------------------------------------------------------
# Sidebar: settings
# ----------------------------------------------------------
with st.sidebar:
    st.header("Settings")
    # A switch to turn query translation on or off.
    # Useful to compare the two, and for demos.
    use_rewrite = st.toggle("Rewrite my question before searching", value=True)
    st.caption("Turns vague or slang questions into clear search queries.")
    use_filter = st.toggle("Filter by brew method", value=True)
    st.caption("If you mention a brewer (V60, moka pot...), search its content first.")

# Connect to the database and the model
vector_store, llm = load_resources()

# Error handling: stop with a clear message if the knowledge base is empty
if vector_store._collection.count() == 0:
    st.warning("The knowledge base is empty. Run `python build_knowledge_base.py` first, then refresh this page.")
    st.stop()


# ----------------------------------------------------------
# Chat history (for DISPLAY only - the AI doesn't remember yet)
# ----------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            show_search_query(
                message.get("search_query"),
                message.get("question"),
                message.get("brew_method", ANY),
            )
            show_sources(message.get("sources", []))


# ----------------------------------------------------------
# A new question
# ----------------------------------------------------------
question = st.chat_input("Ask a coffee question...")

if question is not None:
    question = question.strip()

    error_message = validate_question(question)
    if error_message:
        st.error(error_message)
        st.stop()

    with st.chat_message("user"):
        st.markdown(question)
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("assistant"):
        answer = ""
        search_query = question
        brew_method = ANY
        sources = []
        step_count = 2

        # REQUIREMENT: "Include progress indicators for long operations"
        # st.status is a box that shows each step as it happens.
        with st.status("Working on it...", expanded=False) as status:
            # REQUIREMENT: "Implement proper error handling"
            try:
                # STEP 1: plan the search
                # (query translation + structured retrieval, in one LLM call)
                if use_rewrite or use_filter:
                    st.write("Planning the search...")
                    plan = plan_search(question, llm)
                    step_count = 3

                    if use_rewrite:
                        search_query = plan["search_query"]
                        st.write(f"Rewrote search: {search_query}")
                    if use_filter:
                        brew_method = plan["brew_method"]
                        if brew_method == ANY:
                            st.write("No brew method mentioned, searching everything")
                        else:
                            st.write(f"Filter: {brew_method} + general")
                else:
                    st.write("Searching with your exact words")

                # STEP 2: retrieval
                sources = retrieve(search_query, vector_store, brew_method=brew_method)
                st.write(f"Found {len(sources)} relevant chunks")

                # STEP 3: answer
                st.write("Writing the answer...")
                answer = generate_answer(question, sources, llm)

                status.update(label=f"Done in {step_count} steps", state="complete")

            except Exception as error:
                answer = "Sorry, something went wrong while answering. Try again in a moment."
                sources = []
                print("ERROR while answering:", error)
                status.update(label="Something went wrong", state="error")

        st.markdown(answer)
        show_search_query(search_query, question, brew_method)
        show_sources(sources)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "question": question,
        "search_query": search_query,
        "brew_method": brew_method,
        "sources": sources,
    })
