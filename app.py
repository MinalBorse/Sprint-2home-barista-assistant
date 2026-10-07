# ==========================================================
# app.py
# ==========================================================
# The Home Barista Assistant - web app (version 3: the AGENT).
#
# What it does now:
#   - a chat window (Streamlit)
#   - an AGENT that decides which tools to use:
#       search_coffee_knowledge (RAG with query translation and
#       structured retrieval), brew_ratio_calculator,
#       caffeine_estimator, cost_per_cup
#   - conversation MEMORY: follow-up questions work
#   - shows every tool call and its result
#   - shows the search plan and the sources
#   - progress indicator while the agent works
#   - input validation and error handling
#   - a SECURITY GUARD that blocks prompt-injection attempts
#     before they reach the AI
#
# Run it with:   streamlit run app.py
#
# REQUIREMENTS covered:
#   - "Create an intuitive interface using Streamlit"
#   - "Show relevant context and sources"
#   - "Display tool call results"
#   - "Include progress indicators for long operations"
#   - "Include user input validation"
#   - "Implement proper error handling"
#   - "Provide detailed, context-aware responses" (memory)
#   - "Add relevant security measures for your domain" (input guard)
# ==========================================================

import uuid

import streamlit as st

from src.agent import ask_agent, build_agent
from src.brew_methods import ANY
from src.llm import get_llm
from src.security import BLOCKED_REPLY, check_message
from src.vector_store import KNOWLEDGE_BASE_COLLECTION, get_vector_store


# ----------------------------------------------------------
# Settings
# ----------------------------------------------------------
MAX_QUESTION_LENGTH = 500    # longer questions are rejected (input validation)

# Friendly names and icons for each tool, shown in the UI
TOOL_LABELS = {
    "search_coffee_knowledge": ("🔎", "Searched the coffee knowledge base"),
    "brew_ratio_calculator": ("💧", "Brew ratio calculator"),
    "caffeine_estimator": ("⚡", "Caffeine estimator"),
    "cost_per_cup": ("💶", "Cost per cup"),
}


# ==========================================================
# Load the database, model and agent ONCE
# ==========================================================
# The agent keeps its memory (the checkpointer) inside it,
# so it must be created once and reused, not re-created on every message.
@st.cache_resource
def load_resources():
    vector_store = get_vector_store(KNOWLEDGE_BASE_COLLECTION)
    llm = get_llm()
    agent = build_agent(vector_store, llm)
    return vector_store, agent


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


def format_inputs(args):
    """{'coffee_grams': 18, 'ratio': 16} -> 'coffee_grams = 18, ratio = 16'"""
    parts = []
    for name, value in args.items():
        parts.append(f"{name} = {value}")
    return ", ".join(parts)


def show_tool_results(tool_calls):
    """
    REQUIREMENT: "Display tool call results"
    One card per calculator tool: what it was asked, and what it returned.
    (The knowledge search is shown separately, with its sources.)
    """
    for call in tool_calls:
        if call["name"] == "search_coffee_knowledge":
            continue
        icon, label = TOOL_LABELS.get(call["name"], ("🛠️", call["name"]))
        st.success(
            f"**{label}**  \n"
            f"Inputs: {format_inputs(call['args'])}  \n"
            f"Result: {call['result']}",
            icon=icon,
        )


def show_search_plans(plans):
    """Show what the knowledge search looked for, and the brew-method filter."""
    for plan in plans:
        text = f"Searched for: {plan.get('search_query', '')}"
        brew_method = plan.get("brew_method", ANY)
        if brew_method != ANY:
            text = text + f"  ·  Filter: {brew_method} + general"
        st.caption(text)


def show_sources(sources):
    """
    REQUIREMENT: "Show relevant context and sources"
    A fold-out panel listing the chunks the answer was based on.
    These details come from the DATABASE, not from the AI.
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


def show_assistant_extras(result):
    """Everything shown under an answer: tool cards, search plan, sources."""
    show_tool_results(result.get("tool_calls", []))
    show_search_plans(result.get("plans", []))
    show_sources(result.get("sources", []))


def start_new_conversation():
    """Clear the screen and give the agent a fresh memory (new thread)."""
    st.session_state.messages = []
    st.session_state.thread_id = str(uuid.uuid4())


# ==========================================================
# The page
# ==========================================================
st.set_page_config(page_title="Home Barista Assistant", page_icon="☕")
st.title("☕ Home Barista Assistant")
st.caption("Ask about brewing, fixing coffee that tastes wrong, caffeine, or what your coffee costs.")

# Connect to the database, model and agent
vector_store, agent = load_resources()

# Error handling: stop with a clear message if the knowledge base is empty
if vector_store._collection.count() == 0:
    st.warning("The knowledge base is empty. Run `python build_knowledge_base.py` first, then refresh this page.")
    st.stop()

# ----------------------------------------------------------
# Conversation state
# ----------------------------------------------------------
# messages  -> what we SHOW on screen
# thread_id -> which memory the AGENT uses (one per conversation)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# ----------------------------------------------------------
# Sidebar
# ----------------------------------------------------------
with st.sidebar:
    st.header("Conversation")
    st.button("New conversation", on_click=start_new_conversation)
    st.caption("The assistant remembers this conversation, so follow-up questions work.")

    st.header("What I can do")
    st.markdown(
        "- Answer brewing and taste questions from my coffee guides\n"
        "- Calculate water for your coffee dose\n"
        "- Estimate caffeine in a drink\n"
        "- Work out the cost per cup"
    )

# ----------------------------------------------------------
# Show the conversation so far
# ----------------------------------------------------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            show_assistant_extras(message)

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

    # REQUIREMENT: "Add relevant security measures for your domain"
    # The guard runs BEFORE the AI. A blocked message never reaches the AI.
    is_safe, reason = check_message(question)
    if not is_safe:
        with st.chat_message("assistant"):
            st.markdown(BLOCKED_REPLY)
            st.caption(f"Blocked by the safety filter: {reason}")
        st.session_state.messages.append({
            "role": "assistant",
            "content": BLOCKED_REPLY,
            "tool_calls": [],
            "sources": [],
            "plans": [],
        })
        st.stop()

    with st.chat_message("assistant"):
        result = {"answer": "", "tool_calls": [], "sources": [], "plans": []}

        # REQUIREMENT: "Include progress indicators for long operations"
        with st.status("Thinking...", expanded=False) as status:
            # REQUIREMENT: "Implement proper error handling"
            try:
                result = ask_agent(agent, question, st.session_state.thread_id)

                # List each tool the agent used, inside the status box
                for call in result["tool_calls"]:
                    icon, label = TOOL_LABELS.get(call["name"], ("🛠️", call["name"]))
                    st.write(f"{icon} {label}")

                number_of_tools = len(result["tool_calls"])
                if number_of_tools == 0:
                    status.update(label="Answered directly", state="complete")
                elif number_of_tools == 1:
                    status.update(label="Done · used 1 tool", state="complete")
                else:
                    status.update(label=f"Done · used {number_of_tools} tools", state="complete")

            except Exception as error:
                result["answer"] = "Sorry, something went wrong while answering. Try again in a moment."
                print("ERROR while answering:", error)
                status.update(label="Something went wrong", state="error")

        st.markdown(result["answer"])
        show_assistant_extras(result)

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "tool_calls": result["tool_calls"],
        "sources": result["sources"],
        "plans": result["plans"],
    })
