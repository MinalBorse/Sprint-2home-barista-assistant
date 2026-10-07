# ==========================================================
# src/rag.py
# ==========================================================
# Purpose: all the RAG logic in one reusable place.
#
#   1. REWRITE the question into a better search query  (query translation)
#   2. RETRIEVE the most relevant chunks from Chroma
#   3. ANSWER using only those chunks, with sources
#
# Why a separate file?
#   - app.py stays focused on the user interface
#   - in Part 4, the agent's search tool will reuse these functions
#   - the RAGAs evaluation can test RAG without the web app
#
# REQUIREMENTS covered:
#   - "Implement advanced RAG with query translation"
#   - "Implement standard document retrieval with embeddings"
#   - "Implement domain-specific prompts"
#   - "Show relevant context and sources"
# ==========================================================

from langchain_core.prompts import ChatPromptTemplate


# ----------------------------------------------------------
# Settings
# ----------------------------------------------------------
TOP_K = 4                       # how many chunks to retrieve
MAX_SEARCH_QUERY_LENGTH = 200   # a longer rewrite is suspicious, so we don't use it


# ==========================================================
# PART 1: QUERY TRANSLATION (rewriting the question)
# ==========================================================
# A domain-specific prompt: it knows the words our knowledge base uses.
REWRITE_SYSTEM_PROMPT = """You rewrite coffee questions into short search queries for a coffee knowledge base.

Rules:
1. Output ONLY the search query, on one line. No explanation, no quotes.
2. Use standard coffee terms. Taste problems should use words like: bitter, sour, weak, watery, strong, flat, stale, over-extracted, under-extracted.
3. Keep any brewer or drink names: V60, pour-over, French press, moka pot, AeroPress, espresso.
4. Translate slang or vague words. For example "meh" means flat or dull, and "stovetop thing" means moka pot.
5. Do NOT answer the question. Only rewrite it."""

rewrite_prompt = ChatPromptTemplate.from_messages([
    ("system", REWRITE_SYSTEM_PROMPT),
    ("human", "{question}"),
])


def rewrite_query(question, llm):
    """
    Turn the user's question into a better search query.
    If anything goes wrong, fall back to the original question,
    so the app still works (error handling).
    """
    try:
        rewrite_chain = rewrite_prompt | llm
        response = rewrite_chain.invoke({"question": question})

        # Clean the result: remove spaces, quotes and extra lines
        search_query = response.content.strip().strip('"').strip()
        search_query = search_query.split("\n")[0]

        # Safety checks: an empty or very long rewrite is not trustworthy
        if len(search_query) == 0 or len(search_query) > MAX_SEARCH_QUERY_LENGTH:
            return question

        return search_query

    except Exception as error:
        print("Query rewrite failed, using the original question:", error)
        return question


# ==========================================================
# PART 2: RETRIEVAL
# ==========================================================
def retrieve(search_query, vector_store, k=TOP_K):
    """
    Search Chroma and return a list of sources.
    Each source is a dictionary with the chunk text and its details.
    The details come from the DATABASE, not from the AI,
    so they are always accurate.
    """
    results = vector_store.similarity_search_with_score(search_query, k=k)

    sources = []
    for document, distance in results:
        sources.append({
            "title": document.metadata.get("title", "unknown"),
            "section": document.metadata.get("section", ""),
            "source": document.metadata.get("source", ""),
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


def answer_with_rag(question, vector_store, llm, use_rewrite=True):
    """
    The full RAG flow for one question, built from the 3 steps above.

    Returns a dictionary:
      "answer"       -> the AI's answer
      "search_query" -> what we actually searched for
      "sources"      -> the chunks the answer was based on
    """
    # 1. Rewrite the question into a search query (or keep it as it is)
    if use_rewrite:
        search_query = rewrite_query(question, llm)
    else:
        search_query = question

    # 2. Retrieve with the SEARCH QUERY
    sources = retrieve(search_query, vector_store)

    # 3. Answer the ORIGINAL QUESTION, using the retrieved chunks
    answer = generate_answer(question, sources, llm)

    return {
        "answer": answer,
        "search_query": search_query,
        "sources": sources,
    }
