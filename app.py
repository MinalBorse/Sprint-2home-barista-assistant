# ==========================================================
# app.py
# ==========================================================
# The Home Barista Assistant - FIRST VERSION of the web app.
#
# What it does now:
#   - a chat window (Streamlit)
#   - answers coffee questions using RAG on our knowledge base
#   - shows the sources it used
#   - shows a spinner while it works
#   - checks the user's input
#
# Coming later (Part 4): the agent with 3 tools and memory.
#
# Run it with:   streamlit run app.py
#
# REQUIREMENTS covered:
#   - "Create an intuitive interface using Streamlit"
#   - "Show relevant context and sources"
#   - "Include progress indicators for long operations"
#   - "Include user input validation"
#   - "Implement proper error handling"
# ==========================================================

import streamlit as st
from langchain_core.prompts import ChatPromptTemplate
from src.llm import get_llm
from src.vector_store import get_vector_store, KNOWLEDGE_BASE_COLLECTION


# ----------------------------------------------------------
# Settings
# ----------------------------------------------------------
TOP_K = 4                    # how many chunks to retrieve per question
MAX_QUESTION_LENGTH = 500    # longer questions are rejected (input validation)


# ----------------------------------------------------------
# The RAG prompt (the balanced version from step10)
# ----------------------------------------------------------
SYSTEM_PROMPT = """You are a friendly home barista assistant.

Rules:
1. Answer the question using ONLY the coffee notes provided.
2. You may connect words with similar meaning. For example, "harsh" can mean "bitter", and "sharp" can mean "sour".
3. If the notes do not cover the topic at all, say exactly: "I don't have information about that in my coffee notes." Do not use outside knowledge.
4. Keep the answer short and practical.
5. End with the sources you used, like: (Sources: troubleshooting guide). If you said you don't have information, do NOT list any sources."""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "Coffee notes:\n{context}\n\nQuestion: {question}"),
])


# ==========================================================
# Load the model and database ONCE
# ==========================================================
# Streamlit re-runs this whole file every time the user does something.
# @st.cache_resource means: run this function only the FIRST time,
# then reuse the result. Without it, we would reconnect on every message.
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
        return "Please type a question."
    if len(question) > MAX_QUESTION_LENGTH:
        return f"Your question is too long. Please keep it under {MAX_QUESTION_LENGTH} characters."
    return None


def answer_question(question, vector_store, llm):
    """
    Run RAG for one question.
    Returns (answer_text, list_of_sources).
    """
    # --- RETRIEVE ---
    results = vector_store.similarity_search_with_score(question, k=TOP_K)

    sources = []
    context = ""
    for document, distance in results:
        title = document.metadata.get("title", "unknown")
        section = document.metadata.get("section", "")

        # Label each chunk with its title, so the AI can cite it
        context = context + f"[{title}] {document.page_content}\n\n"

        # Keep the details to show in the Sources panel.
        # These come from the DATABASE, not from the AI,
        # so they are always accurate.
        sources.append({
            "title": title,
            "section": section,
            "source": document.metadata.get("source", ""),
            "similarity": 1 - distance,
            "text": document.page_content,
        })

    # --- AUGMENT + GENERATE ---
    rag_chain = prompt_template | llm
    response = rag_chain.invoke({"context": context, "question": question})

    return response.content, sources


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
            st.caption(f"Similarity {source['similarity']:.2f} - {source['source']}")
            st.text(source["text"][:300] + "...")
            st.divider()


# ==========================================================
# The page
# ==========================================================
st.set_page_config(page_title="Home Barista Assistant", page_icon="☕")
st.title("☕ Home Barista Assistant")
st.caption("Ask me about brewing methods, roasting, and fixing coffee that tastes wrong.")

# Connect to the database and the model
vector_store, llm = load_resources()

# Error handling: stop with a clear message if the knowledge base is empty
if vector_store._collection.count() == 0:
    st.warning("The knowledge base is empty. Run `python build_knowledge_base.py` first, then refresh this page.")
    st.stop()


# ----------------------------------------------------------
# Chat history
# ----------------------------------------------------------
# st.session_state keeps values between re-runs of this file.
# We store every message here, so the chat stays on screen.
# (This is only for DISPLAY. The AI itself doesn't remember yet:
#  conversation memory comes with the agent in Part 4.)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Show all previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
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

    # Show and save the user's message
    with st.chat_message("user"):
        st.markdown(question)
    st.session_state.messages.append({"role": "user", "content": question})

    # Create and show the assistant's answer
    with st.chat_message("assistant"):
        # REQUIREMENT: "Include progress indicators for long operations"
        with st.spinner("Searching the coffee knowledge base..."):
            # REQUIREMENT: "Implement proper error handling"
            try:
                answer, sources = answer_question(question, vector_store, llm)
            except Exception as error:
                answer = "Sorry, something went wrong while answering. Please try again."
                sources = []
                print("ERROR while answering:", error)

        st.markdown(answer)
        show_sources(sources)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
    })
