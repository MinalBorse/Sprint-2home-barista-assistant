# ==========================================================
# src/rag.py
# ==========================================================
# Purpose: all the RAG logic in one reusable place.
#
#   1. PLAN the search: rewrite the question into a better search query
#      (query translation) AND pick a brew-method filter
#      (structured retrieval) - both in ONE LLM call
#   2. RETRIEVE the most relevant chunks from Chroma, using that filter
#   3. ANSWER using only those chunks, with sources
#
# Why a separate file?
#   - app.py stays focused on the user interface
#   - in Part 4, the agent's search tool will reuse these functions
#   - the RAGAs evaluation can test RAG without the web app
#
# REQUIREMENTS covered:
#   - "Implement advanced RAG with query translation and structured retrieval"
#   - "Implement standard document retrieval with embeddings"
#   - "Implement domain-specific prompts"
#   - "Show relevant context and sources"
# ==========================================================

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.brew_methods import ANY, BREW_METHODS, GENERAL


# ----------------------------------------------------------
# Settings
# ----------------------------------------------------------
TRUSTED_SOURCE_TYPE = "own guide"   # our own, checked guides (not Wikipedia)
TOP_K = 4                       # how many chunks to retrieve
MAX_SEARCH_QUERY_LENGTH = 200   # a longer rewrite is suspicious, so we don't use it


# ==========================================================
# PART 1: PLANNING THE SEARCH
#         (query translation + structured retrieval)
# ==========================================================

# The SHAPE of the answer we want from the planner LLM.
# Instead of free text, the LLM must fill in these two fields.
# This is called "structured output". Pydantic describes the fields,
# and the descriptions tell the LLM what to put in each one.
class SearchPlan(BaseModel):
    search_query: str = Field(
        description="A short search query using standard coffee terms."
    )
    brew_method: str = Field(
        description="The brew method the question is about, or 'any' if none is mentioned."
    )


PLANNER_SYSTEM_PROMPT = f"""You plan searches in a coffee knowledge base.

Return two things:
1. search_query: the user's question rewritten as a short search query.
   - Use standard coffee terms. Taste problems should use words like: bitter, sour, weak, watery, strong, flat, stale, over-extracted, under-extracted.
   - Translate slang or vague words. For example "meh" means flat or dull, and "stovetop thing" means moka pot.
   - Do NOT answer the question.
2. brew_method: exactly one of: {", ".join(BREW_METHODS)}, any.
   - Use "any" if the question doesn't mention a specific brew method.
   - "V60", "drip" and "filter" mean pour-over. "Cafetiere" and "plunger" mean french press. "Stovetop" means moka pot."""

planner_prompt = ChatPromptTemplate.from_messages([
    ("system", PLANNER_SYSTEM_PROMPT),
    ("human", "{question}"),
])


def plan_search(question, llm):
    """
    Turn the user's question into a search plan:
        {"search_query": "...", "brew_method": "moka pot" or "any"}

    If anything goes wrong, fall back to the original question
    with no filter, so the app still works (error handling).
    """
    fallback_plan = {"search_query": question, "brew_method": ANY}

    try:
        # with_structured_output makes the LLM fill in our SearchPlan fields
        planner = planner_prompt | llm.with_structured_output(SearchPlan)
        plan = planner.invoke({"question": question})

        search_query = plan.search_query.strip().strip('"').strip()
        brew_method = plan.brew_method.strip().lower()

        # Validation: the search query must look reasonable
        if len(search_query) == 0 or len(search_query) > MAX_SEARCH_QUERY_LENGTH:
            search_query = question

        # Validation: the brew method must be one we actually have.
        # Anything else (a typo, an invented method) means: no filter.
        if brew_method not in BREW_METHODS:
            brew_method = ANY

        return {"search_query": search_query, "brew_method": brew_method}

    except Exception as error:
        print("Search planning failed, using the original question:", error)
        return fallback_plan


def rewrite_query(question, llm):
    """
    Only the rewritten search query (no filter).
    Kept so older scripts like step15 still work.
    """
    plan = plan_search(question, llm)
    return plan["search_query"]


# ==========================================================
# PART 2: RETRIEVAL (with an optional brew-method filter)
# ==========================================================
def build_filter(brew_method, trusted_only=False):
    """
    The Chroma filter for a search. It can combine two conditions:
      - brew_method: only that method's chunks, plus "general" chunks
        (like the troubleshooting guide), which apply to every method
      - trusted_only: only our own guides, no Wikipedia
    Returns None when there is nothing to filter.
    """
    conditions = []

    if brew_method != ANY:
        conditions.append({"brew_method": {"$in": [brew_method, GENERAL]}})

    if trusted_only:
        conditions.append({"source_type": TRUSTED_SOURCE_TYPE})

    if len(conditions) == 0:
        return None
    if len(conditions) == 1:
        return conditions[0]
    # Several conditions: ALL of them must be true
    return {"$and": conditions}


def retrieve(search_query, vector_store, k=TOP_K, brew_method=ANY, trusted_only=False):
    """
    Search Chroma and return a list of sources.
    Each source is a dictionary with the chunk text and its details.
    The details come from the DATABASE, not from the AI,
    so they are always accurate.
    """
    results = vector_store.similarity_search_with_score(
        search_query,
        k=k,
        filter=build_filter(brew_method, trusted_only),
    )

    sources = []
    for document, distance in results:
        sources.append({
            "title": document.metadata.get("title", "unknown"),
            "section": document.metadata.get("section", ""),
            "source": document.metadata.get("source", ""),
            "brew_method": document.metadata.get("brew_method", ""),
            "similarity": 1 - distance,     # Chroma gives distance; convert it
            "text": document.page_content,
        })
    return sources


def build_context(sources):
    """Join the chunks into one text, each labeled with its title."""
    context = ""
    for source in sources:
        context = context + f"[{source['title']}] {source['text']}\n\n"
    return context


# ==========================================================
# PART 3: ANSWERING (augmented generation)
# ==========================================================
ANSWER_SYSTEM_PROMPT = """You are a friendly home barista assistant.

Rules:
1. Answer the question using ONLY the coffee notes provided.
2. You may connect words with similar meaning. For example, "harsh" can mean "bitter", and "sharp" can mean "sour".
3. If the notes do not cover the topic at all, say exactly: "I don't have information about that in my coffee notes." Do not use outside knowledge.
4. Keep the answer short and practical.
5. End with the sources you used, like: (Sources: troubleshooting guide). If you said you don't have information, do NOT list any sources."""

answer_prompt = ChatPromptTemplate.from_messages([
    ("system", ANSWER_SYSTEM_PROMPT),
    ("human", "Coffee notes:\n{context}\n\nQuestion: {question}"),
])


def generate_answer(question, sources, llm):
    """
    Write the answer to the ORIGINAL question, using the retrieved chunks.
    """
    answer_chain = answer_prompt | llm
    response = answer_chain.invoke({
        "context": build_context(sources),
        "question": question,
    })
    return response.content


def answer_with_rag(question, vector_store, llm, use_rewrite=True, use_filter=True):
    """
    The full RAG flow for one question, built from the steps above.

    use_rewrite -> query translation on/off
    use_filter  -> structured retrieval (brew-method filter) on/off

    Returns a dictionary:
      "answer"       -> the AI's answer
      "search_query" -> what we actually searched for
      "brew_method"  -> the filter we used ("any" = no filter)
      "sources"      -> the chunks the answer was based on
    """
    # 1. Plan the search (or keep the question as it is)
    if use_rewrite:
        plan = plan_search(question, llm)
    else:
        plan = {"search_query": question, "brew_method": ANY}

    if not use_filter:
        plan["brew_method"] = ANY

    # 2. Retrieve with the SEARCH QUERY and the FILTER
    sources = retrieve(plan["search_query"], vector_store, brew_method=plan["brew_method"])

    # 3. Answer the ORIGINAL QUESTION, using the retrieved chunks
    answer = generate_answer(question, sources, llm)

    return {
        "answer": answer,
        "search_query": plan["search_query"],
        "brew_method": plan["brew_method"],
        "sources": sources,
    }
