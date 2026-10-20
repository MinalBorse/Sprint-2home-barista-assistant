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

import os
import uuid
from collections import Counter

import streamlit as st

from src.agent import AGENT_SYSTEM_PROMPT, UserPreferences, ask_agent, build_agent, make_search_tool, style_instructions
from src.brew_methods import ANY, BREW_METHODS
from src.document_splitter import CHUNK_OVERLAP, CHUNK_SIZE, MIN_CHUNK_CHARACTERS
from src.llm import get_llm
from src.rag import PLANNER_SYSTEM_PROMPT, TOP_K, build_filter
from src.security import (
    BLOCKED_REPLY,
    GUARD_CATEGORIES,
    GUARD_SYSTEM_PROMPT,
    INJECTION_PATTERNS,
    check_message,
    llm_check_message,
)
from src.theme import AVATAR_IMAGE, apply_cafe_theme, show_sidebar_brand, show_welcome_banner
from src.tools import CALCULATOR_TOOLS
from src.vector_store import KNOWLEDGE_BASE_COLLECTION, get_vector_store

# ----------------------------------------------------------
# Settings
# ----------------------------------------------------------
MAX_QUESTION_LENGTH = 500  # longer questions are rejected (input validation)

# Starter questions shown in the barista's greeting.
# Tapping one asks it straight away.
# OPTIONAL TASK (easy): "Add an interactive help feature or chatbot guide"
STARTER_QUESTIONS = [
    "Why does my coffee taste bitter?",
    "How much water for 18 g of coffee?",
    "How much caffeine is in a 350 ml cold brew?",
    "How do I brew with a moka pot?",
]

# The barista's avatar: the gold coffee-bean emblem (assets/barista_avatar.png)
ASSISTANT_AVATAR = AVATAR_IMAGE

# "My brewer" choices: the label shown in the sidebar -> the brew_method
# stored on our chunks (see src/brew_methods.py)
BREWER_CHOICES = {
    "Not set": ANY,
    "Pour-over / V60 / Chemex": "pour-over",
    "French press": "french press",
    "AeroPress": "aeropress",
    "Moka pot": "moka pot",
    "Espresso machine": "espresso",
    "Cold brew": "cold brew",
    "Turkish coffee (cezve)": "turkish coffee",
    "Siphon (vacuum pot)": "siphon",
    "Vietnamese phin": "vietnamese phin",
    "Percolator": "percolator",
    "South Indian filter": "south indian filter",
}
# Safety check: every dropdown value must be a real brew method.
# A typo here would otherwise make the filter silently find nothing,
# so we stop the app immediately with a clear message instead.
for brewer_value in BREWER_CHOICES.values():
    if brewer_value != ANY and brewer_value not in BREW_METHODS:
        raise ValueError(f"Unknown brew method in BREWER_CHOICES: {brewer_value}")
# Friendly names and icons for each tool, shown in the UI
# (":material/...:" are Streamlit's built-in, clean line icons)
TOOL_LABELS = {
    "search_coffee_knowledge": (":material/menu_book:", "Searched the coffee knowledge base"),
    "brew_ratio_calculator": (":material/water_drop:", "Brew ratio calculator"),
    "caffeine_estimator": (":material/bolt:", "Caffeine estimator"),
    "cost_per_cup": (":material/payments:", "Cost per cup"),
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

    # A separate model for the LLM security guard.
    # temperature=0 makes its decisions as consistent as possible:
    # the same message should always get the same answer.
    guard_llm = get_llm(temperature=0)

    return vector_store, agent, guard_llm


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
        icon, label = TOOL_LABELS.get(call["name"], (":material/build:", call["name"]))
        st.success(
            f"**{label}**  \nInputs: {format_inputs(call['args'])}  \nResult: {call['result']}",
            icon=icon,
        )


def show_search_plans(plans):
    """Show what the knowledge search looked for, and which filters it used."""
    for plan in plans:
        text = f"Searched for: {plan.get('search_query', '')}"

        brew_method = plan.get("brew_method", ANY)
        if brew_method != ANY:
            text = text + f"  ·  Filter: {brew_method} + general"
            if plan.get("used_my_brewer"):
                text = text + " (your brewer)"

        if plan.get("trusted_only"):
            text = text + "  ·  Trusted guides only"

        if plan.get("hide_history"):
            text = text + "  ·  History hidden"

        taste_problem = plan.get("taste_problem", "none")
        if taste_problem != "none":
            text = text + f"  ·  Taste problem: {taste_problem}"

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
            st.caption(f"Similarity {source['similarity']:.2f} - {source.get('brew_method', '')} - {source['source']}")
            st.text(source["text"][:300] + "...")
            st.divider()

def show_request_trace(message):
    """Developer view: the plan, the Chroma filters and how each card was found."""
    if os.getenv("DEV_MODE", "false").lower() != "true" or not message.get("plans"):
        return
    with st.expander("Developer: request trace"):
        for plan in message["plans"]:
            st.markdown("**1. The plan (4 boxes)**")
            st.json({key: plan.get(key) for key in ["search_query", "brew_method", "taste_problem", "topic"]})
            if plan.get("used_my_brewer"):
                st.caption("The brew method came from My brewer, because the question named none.")
            st.markdown("**2. The Chroma filters**")
            if plan.get("taste_problem", "none") != "none":
                st.write("Taste boost:", {"taste_problem": plan["taste_problem"]})
            normal_filter = build_filter(plan.get("brew_method", "any"), plan.get("trusted_only", False),
                                         plan.get("hide_history", False))
            st.write("Normal search:", normal_filter or "no filter: all chunks searched")
        st.markdown("**3. The cards**")
        for source in message.get("sources", []):
            how = "📌 pinned by the taste boost" if source.get("pinned") else "🔎 normal search"
            st.write(f"{how} · {source['similarity']:.3f} · {source['title']} · {source.get('section', '')}")

def show_assistant_extras(result):
    """Everything shown under an answer: tool cards, search plan, sources."""
    show_tool_results(result.get("tool_calls", []))
    show_search_plans(result.get("plans", []))
    show_sources(result.get("sources", []))
    show_request_trace(result)

def ask_starter_question(question):
    """Called when a starter button is tapped: ask that question next."""
    st.session_state.pending_question = question


def show_barista_greeting(show_buttons):
    """
    The first message in every conversation: a friendly greeting.
    While the conversation is empty, it also offers starter questions.
    OPTIONAL TASK (easy): "Add an interactive help feature or chatbot guide"
    """
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        st.markdown(
            "Good evening, and welcome to your **Home Barista Assistant**. What shall we brew today? "
            "Ask me anything about coffee, or choose one of these to begin:"
        )
        if not show_buttons:
            return
        columns = st.columns(2)
        for index in range(len(STARTER_QUESTIONS)):
            starter = STARTER_QUESTIONS[index]
            with columns[index % 2]:
                st.button(
                    starter,
                    key=f"starter_{index}",
                    on_click=ask_starter_question,
                    args=(starter,),
                    use_container_width=True,
                )


def start_new_conversation():
    """Clear the screen and give the agent a fresh memory (new thread)."""
    st.session_state.messages = []
    st.session_state.thread_id = str(uuid.uuid4())


# ==========================================================
# The page
# ==========================================================
st.set_page_config(page_title="Home Barista Assistant", page_icon=AVATAR_IMAGE)

# The app's look (pure CSS and SVG, no images) - see src/theme.py (pure CSS and SVG, no images) - see src/theme.py
apply_cafe_theme()
show_welcome_banner()

vector_store, agent, guard_llm = load_resources()

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
    show_sidebar_brand()
    st.header("Conversation")
    st.button("New conversation", on_click=start_new_conversation)
    st.caption("The assistant remembers this conversation, so follow-up questions work.")

    st.header("Your preferences")
    # STRUCTURED RETRIEVAL, chosen by the user:
    # these become filters on the knowledge search
    brewer_label = st.selectbox("My brewer", list(BREWER_CHOICES.keys()))
    st.caption("Questions that don't name a brewer will focus on yours.")
    trusted_only = st.toggle("Trusted guides only", value=False)
    st.caption("Use only the assistant's own checked guides, not Wikipedia.")
    hide_history = st.toggle("Hide history and trivia", value=True)
    st.caption("Practical tips only. Ask about history and it's shown anyway.")

    st.header("Answer style")
    # These change HOW answers are written, not which notes are searched
    experience = st.radio("Experience", ["Beginner", "Enthusiast"], horizontal=True)
    units = st.radio("Units", ["Metric", "Imperial"], horizontal=True)
    length = st.radio("Answer length", ["Short", "Detailed"], horizontal=True)


    if os.getenv("DEV_MODE", "false").lower() == "true":
        st.header("Developer settings")
        with st.expander("Agent system prompt"):
            current_style = style_instructions(UserPreferences(
                experience=experience.lower(), units=units.lower(), length=length.lower()))
            st.code(AGENT_SYSTEM_PROMPT + "\n\nAnswer style for this user:\n" + current_style,
                    language=None, wrap_lines=True)
        with st.expander("Search planner prompt"):
            st.code(PLANNER_SYSTEM_PROMPT, language=None, wrap_lines=True)
        with st.expander("What the AI sees: the tools"):
            for dev_tool in [make_search_tool(load_resources()[0], None)] + CALCULATOR_TOOLS:
                st.markdown(f"**{dev_tool.name}**: inputs {list(dev_tool.args.keys())}")
                st.caption(dev_tool.description)
        with st.expander("Model and RAG settings"):
            st.code(f"chat model:      {os.getenv('MODEL_NAME', 'openai/gpt-4o-mini')}\n"
                    f"embedding model: {os.getenv('EMBEDDING_MODEL_NAME', 'openai/text-embedding-3-small')}\n"
                    f"temperature:     0.2 (agent, planner)  ·  0 (guard, topic tagging)\n"
                    f"chunks:          {CHUNK_SIZE} characters, {CHUNK_OVERLAP} overlap, min {MIN_CHUNK_CHARACTERS}\n"
                    f"top-k:           {TOP_K} chunks per search", language=None)
        with st.expander("Knowledge base and memory"):
            dev_meta = load_resources()[0]._collection.get(include=["metadatas"])["metadatas"]
            st.write(f"**{len(dev_meta)} chunks** · conversation id: `{st.session_state.get('thread_id', '-')}`")
            st.write("By topic:", dict(Counter(m.get("topic", "?") for m in dev_meta).most_common()))
            st.write("By brewer:", dict(Counter(m.get("brew_method", "?") for m in dev_meta).most_common()))
        with st.expander("Security guards"):
            st.markdown(f"**Pattern guard**: {len(INJECTION_PATTERNS)} patterns, checked first (free, instant)")
            for _, dev_reason in INJECTION_PATTERNS:
                st.caption(f"• {dev_reason}")
            st.markdown(f"**LLM guard**: categories {GUARD_CATEGORIES}, only prompt_injection is blocked")
            st.code(GUARD_SYSTEM_PROMPT, language=None, wrap_lines=True)
    st.header("On the menu tonight")
    st.markdown(
        "- Answer brewing and taste questions from my coffee guides\n"
        "- Calculate water for your coffee dose\n"
        "- Estimate caffeine in a drink\n"
        "- Work out the cost per cup"
    )

# ----------------------------------------------------------
# Show the conversation so far
# ----------------------------------------------------------
# Every conversation starts with the barista's greeting.
# The starter buttons only appear while nothing has been asked yet.
conversation_is_empty = len(st.session_state.messages) == 0
no_question_waiting = not st.session_state.get("pending_question")
show_barista_greeting(show_buttons=conversation_is_empty and no_question_waiting)

for message in st.session_state.messages:
    if message["role"] == "assistant":
        avatar = ASSISTANT_AVATAR
    else:
        avatar = None
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            show_assistant_extras(message)

# ----------------------------------------------------------
# A new question
# ----------------------------------------------------------
question = st.chat_input("Ask your barista...")

# A tapped starter question counts as if the guest had typed it
if question is None and st.session_state.get("pending_question"):
    question = st.session_state.pending_question
    st.session_state.pending_question = None

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
    # Check 1: the pattern guard (free and instant)
    is_safe, reason = check_message(question)

    # Check 2: the LLM guard (smarter, about a second).
    # It only runs if the pattern guard found nothing, so obvious
    # attacks are blocked for free, without calling the LLM.
    if is_safe:
        with st.spinner("Checking your message..."):
            is_safe, reason = llm_check_message(question, guard_llm)
    if not is_safe:
        with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
            st.markdown(BLOCKED_REPLY)
            st.caption(f"Blocked by the safety filter: {reason}")
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": BLOCKED_REPLY,
                "tool_calls": [],
                "sources": [],
                "plans": [],
            }
        )
        st.stop()

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        result = {"answer": "", "tool_calls": [], "sources": [], "plans": []}

        # REQUIREMENT: "Include progress indicators for long operations"
        with st.status("Thinking...", expanded=False) as status:
            # REQUIREMENT: "Implement proper error handling"
            try:
                preferences = UserPreferences(
                    brewer=BREWER_CHOICES[brewer_label],
                    trusted_only=trusted_only,
                    hide_history=hide_history,
                    experience=experience.lower(),
                    units=units.lower(),
                    length=length.lower(),
                )
                result = ask_agent(agent, question, st.session_state.thread_id, preferences)

                # List each tool the agent used, inside the status box
                for call in result["tool_calls"]:
                    icon, label = TOOL_LABELS.get(call["name"], (":material/build:", call["name"]))
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

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "tool_calls": result["tool_calls"],
            "sources": result["sources"],
            "plans": result["plans"],
        }
    )
