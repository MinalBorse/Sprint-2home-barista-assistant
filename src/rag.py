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
#
# LEARNING NOTES (Module 5, Lessons 1-6)
#
# When does this file run?
#   PHASE 2: every time someone asks a coffee KNOWLEDGE question.
#   Not for greetings, calculator-only questions or off-topic requests:
#   the agent decides, and calls its search tool, which uses this file.
#
# Who uses what:
#   - the app (through the agent's search tool): plan_search() + retrieve()
#     + build_context(). In the app, the AGENT writes the answer.
#   - evaluate_rag.py (RAGAs): answer_with_rag(), the whole chain, including
#     generate_answer(). So the evaluation scores THIS file's answers, while
#     users see the agent's answers (AI review #4).
#
# The whole flow, in one line:
#   question -> plan_search() -> build_filter() -> retrieve() -> build_context() -> an LLM answers
#               (4-box slip)     (the switches)    (4 cards)     (labelled notes)
# ==========================================================

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.brew_methods import ANY, BREW_METHODS, GENERAL
from src.chunk_tags import HISTORY, NONE, TASTE_PROBLEMS, TOPICS

# LEARNING NOTE: all allowed values come from their single source of truth
# (src/brew_methods.py and src/chunk_tags.py), so the planner, the checks and
# the filters can never disagree with the chunk labels.

# ----------------------------------------------------------
# Settings
# ----------------------------------------------------------
TRUSTED_SOURCE_TYPE = "own guide"  # our own, checked guides (not Wikipedia)
TOP_K = 4  # how many chunks to retrieve
MAX_SEARCH_QUERY_LENGTH = 200  # a longer rewrite is suspicious, so we don't use it
# LEARNING NOTE: the settings
#   - TRUSTED_SOURCE_TYPE: the label used by "Trusted guides only".
#   - TOP_K = 4: a balance. Fewer cards risk missing advice; many cards are slower,
#     costlier, and distract the model. 4 cards of up to 1,000 characters each
#     is plenty for a short, practical answer.
#   - MAX_SEARCH_QUERY_LENGTH: a rewrite longer than 200 characters probably means
#     the planner started ANSWERING instead of planning, so we ignore it.


# ==========================================================
# PART 1: PLANNING THE SEARCH
#         (query translation + structured retrieval)
# ==========================================================


# The SHAPE of the answer we want from the planner LLM.
# Instead of free text, the LLM must fill in these two fields.
# This is called "structured output". Pydantic describes the fields,
# and the descriptions tell the LLM what to put in each one.
# LEARNING NOTE: the 4-box ORDER SLIP (the comment above still says "two fields";
# it was written before taste_problem and topic were added).
#   box              -> controls                        e.g. "my stovetop thing tastes bitter"
#   search_query     -> the meaning search (query translation)  "moka pot coffee tastes bitter"
#   brew_method      -> the brew filter                         "moka pot"
#   taste_problem    -> the taste boost (the VIP card)          "bitter"
#   topic            -> whether to lift "Hide history"          "troubleshooting"
# The Field descriptions are READ BY THE MODEL. This is one of our 3 Pydantic
# forms (with TopicTag in src/chunk_tags.py and GuardDecision in src/security.py).
class SearchPlan(BaseModel):
    search_query: str = Field(description="A short search query using standard coffee terms.")
    brew_method: str = Field(description="The brew method the question is about, or 'any' if none is mentioned.")
    taste_problem: str = Field(description="The taste problem described (bitter, sour, weak, strong, flat), or 'none'.")
    topic: str = Field(description="The main topic of the question, or 'any' if unclear.")


# LEARNING NOTE: the planner's instruction sheet (one numbered part per box).
#   - It's an f-string: {", ".join(BREW_METHODS)} is replaced by the real list.
#     So when we added 5 brew methods to BREW_METHODS, the planner learned them
#     automatically, with no prompt edit. The same for taste problems and topics.
#   - The FIRM rule ("Always replace ... 'puckery' becomes sour") replaced an
#     earlier "for example" hint, which the model treated as optional: "puckery"
#     was left unchanged and the sour section was missed. Explicit, imperative
#     rules are followed more reliably (the puckery lesson). The rule also
#     generalises: "so-so" and "blah" become flat without being listed.
#   - The translation hints ("V60" means pour-over, "harsh" means bitter) are why
#     user words like "Turkish" or "so-so" need no keyword list: the LLM understands.
#   - "Do NOT answer the question": the planner only PLANS the search.
#   - "Return four things" was "two things" before (AI review #16, fixed).
#   - Known edge case (AI review #6): '"drip" and "filter" mean pour-over' could
#     misroute "Vietnamese drip" or "South Indian filter"; tested twice, the
#     planner routed both correctly, so it was not reproduced.
PLANNER_SYSTEM_PROMPT = f"""You plan searches in a coffee knowledge base.

Return four things:
1. search_query: the user's question rewritten as a short search query.
   - Use standard coffee terms. Taste problems should use words like: bitter, sour, weak, watery, strong, flat, stale, over-extracted, under-extracted.
   - Always replace slang or vague taste words with standard coffee terms: "meh" becomes flat, "puckery" becomes sour, "thin" becomes weak. "Stovetop thing" becomes moka pot.
   - Do NOT answer the question.
2. brew_method: exactly one of: {", ".join(BREW_METHODS)}, any.
   - Use "any" if the question doesn't mention a specific brew method.
   - "V60", "Chemex", "Kalita", "Melitta", "Origami", "drip" and "filter" mean pour-over. "Cafetiere" and "plunger" mean french press. "Stovetop", "Brikka" and "Bialetti" mean moka pot. A "lever" machine means espresso.
3. taste_problem: exactly one of: {", ".join(TASTE_PROBLEMS)}, none.
   - "harsh", "burnt" and "astringent" mean bitter. "sharp", "acidic", "tangy" and "puckery" mean sour.
   - "watery" and "thin" mean weak. "meh" and "dull" mean flat. Use "none" if no taste problem is described.
4. topic: exactly one of: {", ".join(TOPICS)}, any.
   - Use "history" only when the user asks about inventors, dates or how something developed."""

# LEARNING NOTE: a template with a gap ({question}). The RULES go in the system
# message and the user's QUESTION fills the human message at run time, so user
# words can never be mixed into the rules.
planner_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", PLANNER_SYSTEM_PROMPT),
        ("human", "{question}"),
    ]
)


def plan_search(question, llm):
    """
    Turn the user's question into a search plan:
        {"search_query": "...", "brew_method": "moka pot" or "any"}

    If anything goes wrong, fall back to the original question
    with no filter, so the app still works (error handling).
    """
    # LEARNING NOTE (the cafe order): the planner is a Python FUNCTION that makes ONE
    # LLM call; it is not an agent (fixed steps, no tools). Three steps:
    #   1. a BACKUP slip first: the user's own words, no filters
    #   2. the LLM (the waiter) fills the real 4-box slip
    #   3. Python (the manager) tidies and checks every box against the menu
    # The docstring above shows only 2 keys; the plan really has 4.
    # The llm is PASSED IN (the same gpt-4o-mini as the agent, temperature 0.2).
    fallback_plan = {
        "search_query": question,
        "brew_method": ANY,
        "taste_problem": NONE,
        "topic": ANY,
    }

    try:
        # with_structured_output makes the LLM fill in our SearchPlan fields
        # LEARNING NOTE: "|" connects the template and the LLM into a CHAIN. The LLM is
        # told to answer by filling in the SearchPlan form (structured output), and
        # .invoke() runs it, putting the question into the {question} gap.
        planner = planner_prompt | llm.with_structured_output(SearchPlan)
        plan = planner.invoke({"question": question})

        # LEARNING NOTE: tidy the handwriting: .strip() removes spaces at the ends,
        # .strip('"') removes quote marks, .lower() makes "Moka Pot" -> "moka pot".
        search_query = plan.search_query.strip().strip('"').strip()
        brew_method = plan.brew_method.strip().lower()
        taste_problem = plan.taste_problem.strip().lower()
        topic = plan.topic.strip().lower()

        # Validation: the search query must look reasonable
        # LEARNING NOTE: check every box against the menu. Anything not allowed is
        # replaced by a SAFE choice:
        #   empty or too-long query -> the user's own question
        #   unknown brew method ("kettle") -> any (no brew filter)
        #   unknown taste problem ("salty") -> none (no boost)
        #   unknown topic ("recipes") -> any
        # Pydantic guarantees the SHAPE; these checks guarantee the VALUES.
        if len(search_query) == 0 or len(search_query) > MAX_SEARCH_QUERY_LENGTH:
            search_query = question

        # Validation: the brew method must be one we actually have.
        # Anything else (a typo, an invented method) means: no filter.
        if brew_method not in BREW_METHODS:
            brew_method = ANY
        if taste_problem not in TASTE_PROBLEMS:
            taste_problem = NONE
        if topic not in TOPICS:
            topic = ANY

        return {
            "search_query": search_query,
            "brew_method": brew_method,
            "taste_problem": taste_problem,
            "topic": topic,
        }

    # LEARNING NOTE: three layers of safety, like topic tagging:
    #   1. the FORM (4 boxes)   2. the CHECKS (allowed values)   3. the FALLBACK
    # If the LLM call fails (no internet, an API error), the error is printed and
    # the backup plan is returned: the search is less focused, but never broken.
    except Exception as error:
        print("Search planning failed, using the original question:", error)
        return fallback_plan


# LEARNING NOTE: kept only for the older step15 test script (AI review #21).
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
# LEARNING NOTE (Module 5, Lesson 3): three SWITCHES become a Chroma filter.
#   switch         comes from                     if ON, keep only cards that...
#   brew_method    the planner (or "My brewer")   are that brewer's OR "general"
#   trusted_only   the sidebar                    come from our own guides
#   hide_history   the sidebar                    are not about history
# "general" is ALWAYS kept with a brewer: our troubleshooting sections are
# "general", and a moka pot question still needs the bitter fix.
# Chroma's filter words: $in = "is one of", $ne = "is not equal to",
# $and = "all of these must be true".
def build_filter(brew_method, trusted_only=False, hide_history=False):
    """
    The Chroma filter for a search. It can combine three conditions:
      - brew_method:  only that method's chunks, plus "general" chunks
                      (like the troubleshooting guide), which apply to every method
      - trusted_only: only our own guides, no Wikipedia
      - hide_history: leave out chunks about history and trivia
    Returns None when there is nothing to filter.
    """
    conditions = []

    if brew_method != ANY:
        conditions.append({"brew_method": {"$in": [brew_method, GENERAL]}})

    if trusted_only:
        conditions.append({"source_type": TRUSTED_SOURCE_TYPE})

    if hide_history:
        # "$ne" means "not equal": every topic except history
        conditions.append({"topic": {"$ne": HISTORY}})

    # LEARNING NOTE: no rules -> None (search ALL cards); one rule -> just that rule;
    # several rules -> {"$and": [...]}: a card must pass all of them.
    if len(conditions) == 0:
        return None
    if len(conditions) == 1:
        return conditions[0]
    # Several conditions: ALL of them must be true
    return {"$and": conditions}


# LEARNING NOTE: one "source" package per found card. Every field comes from the
# DATABASE, not from the AI, which is why the Sources panel is always accurate,
# even when the model's own "(Sources: ...)" line invents a title (review #33).
# The packages go two ways: their title + text become the notes for the model
# (build_context), and the full packages go to the app's Sources panel.
# "pinned" marks the taste-boost card; the app doesn't show it yet (review #21).
def to_source(document, distance, pinned=False):
    """Turn one Chroma result into a source dictionary for the app."""
    return {
        "title": document.metadata.get("title", "unknown"),
        "section": document.metadata.get("section", ""),
        "source": document.metadata.get("source", ""),
        "brew_method": document.metadata.get("brew_method", ""),
        "topic": document.metadata.get("topic", ""),
        "similarity": 1 - distance,  # Chroma gives distance; convert it
        "pinned": pinned,  # True = added because of the taste problem
        "text": document.page_content,
    }


# LEARNING NOTE (Module 5, Lesson 4): filling 4 SEATS with the best cards.
#   1. the VIP seat (the taste boost): if there is a taste problem, its ONE
#      troubleshooting card gets seat 1, guaranteed (k=1, because our guide has
#      exactly one section per taste problem)
#   2. the normal search: the 4 cards closest in MEANING, inside the filter
#      (these can come from our guides or Wikipedia, unless "Trusted guides only")
#   3. fill the remaining seats in order, skipping duplicates, until 4 are full
# Why both searches? The normal search USUALLY ranks the right fix first, but
# not always (before rewriting, "meh" didn't even put the flat section in the top
# 3). The VIP seat GUARANTEES it, and the normal search adds variety, like
# brewer-specific tips ("cool the moka pot base").
# Why a BOOST and not a FILTER? A taste filter would find only the fix card and
# lose the brewer tips. No taste problem -> no VIP seat: all 4 come from search.
def retrieve(
    search_query, vector_store, k=TOP_K, brew_method=ANY, trusted_only=False, hide_history=False, taste_problem=NONE
):
    """
    Search Chroma and return a list of sources.
    The details come from the DATABASE, not from the AI,
    so they are always accurate.

    taste_problem: if the question describes one (like "bitter"), the matching
    troubleshooting section is ALWAYS included, as the first source.
    This is a "boost", not a filter: the other chunks are still searched
    normally, so useful method-specific advice is not lost.
    """
    sources = []

    # 1. The boost: the troubleshooting section for this taste problem
    if taste_problem in TASTE_PROBLEMS:
        # LEARNING NOTE: the pinned search uses ONLY the taste filter, not the brew,
        # trusted or history filters. That's safe: the troubleshooting cards are "own
        # guide", "general" and not "history", so they would pass those filters anyway.
        pinned_results = vector_store.similarity_search_with_score(
            search_query, k=1, filter={"taste_problem": taste_problem}
        )
        for document, distance in pinned_results:
            sources.append(to_source(document, distance, pinned=True))

    # 2. The normal search, with the filters
    results = vector_store.similarity_search_with_score(
        search_query,
        k=k,
        filter=build_filter(brew_method, trusted_only, hide_history),
    )

    # 3. Add the normal results, skipping duplicates, up to k sources in total
    # LEARNING NOTE: fill the seats without duplicates. The VIP card usually comes
    # back in the normal search too (it is close in meaning), so:
    #   - all 4 seats full? -> break (leave the loop)
    #   - compare this card's text with every seated card's text
    #   - only seat it if it's NEW
    for document, distance in results:
        if len(sources) >= k:
            break
        already_included = False
        for source in sources:
            if source["text"] == document.page_content:
                already_included = True
        if not already_included:
            sources.append(to_source(document, distance))

    return sources


# LEARNING NOTE (Module 5, Lesson 5): turn the 4 cards into ONE page of notes for
# the model, each card labelled [title] and followed by a blank line ("\n\n"),
# so the model can see where each note ends and cite the right source.
# It uses only each source's title and text. It does NOT write the answer.
# The notes always travel as DATA (in the human message or the tool result),
# never in the system prompt (security: agent rule 8).
# Used by generate_answer() below (the evaluation) and by the agent's search tool.
def build_context(sources):
    """Join the chunks into one text, each labeled with its title."""
    context = ""
    for source in sources:
        context = context + f"[{source['title']}] {source['text']}\n\n"
    return context


# ==========================================================
# PART 3: ANSWERING (augmented generation)
# ==========================================================
# LEARNING NOTE (Module 5, Lesson 6): the answer rules, used by the EVALUATION.
# In the app, the agent answers with its own prompt (AGENT_SYSTEM_PROMPT).
#   1. only the notes             -> grounding: no invented facts
#   2. connect similar words      -> "harsh" matches the bitter notes
#   3. the exact fallback sentence -> honest "I don't know" (e.g. latte art)
#   4. short and practical
#   5. list sources, but NOT after a fallback -> no fake sources
ANSWER_SYSTEM_PROMPT = """You are a friendly home barista assistant.

Rules:
1. Answer the question using ONLY the coffee notes provided.
2. You may connect words with similar meaning. For example, "harsh" can mean "bitter", and "sharp" can mean "sour".
3. If the notes do not cover the topic at all, say exactly: "I don't have information about that in my coffee notes." Do not use outside knowledge.
4. Keep the answer short and practical.
5. End with the sources you used, like: (Sources: troubleshooting guide). If you said you don't have information, do NOT list any sources."""

answer_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", ANSWER_SYSTEM_PROMPT),
        ("human", "Coffee notes:\n{context}\n\nQuestion: {question}"),
    ]
)


# LEARNING NOTE: a simple CHAIN (prompt | llm). It answers the user's ORIGINAL
# question: the rewritten query is only for searching. response.content is the
# text of the LLM's reply.
def generate_answer(question, sources, llm):
    """
    Write the answer to the ORIGINAL question, using the retrieved chunks.
    """
    answer_chain = answer_prompt | llm
    response = answer_chain.invoke(
        {
            "context": build_context(sources),
            "question": question,
        }
    )
    return response.content


# LEARNING NOTE: the whole RAG flow in one function: plan -> find -> answer.
# Used by evaluate_rag.py for the A/B test (use_rewrite True vs False).
# Honest note (AI review #5): with use_rewrite=False, the plan ALSO has no brew
# filter and no taste boost, so the A/B test compares the WHOLE planner
# (rewriting + filters + boost) against plain search, not rewriting alone.
# Like removing sugar, milk and cinnamon at once: you can't tell which mattered.
# A fair test changes one thing at a time (e.g. a mode with filters but no rewrite).
# use_filter is never passed by the evaluation (AI review #21).
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
        plan = {"search_query": question, "brew_method": ANY, "taste_problem": NONE, "topic": ANY}

    if not use_filter:
        plan["brew_method"] = ANY
        plan["taste_problem"] = NONE

    # 2. Retrieve with the SEARCH QUERY and the FILTERS
    sources = retrieve(
        plan["search_query"],
        vector_store,
        brew_method=plan["brew_method"],
        taste_problem=plan["taste_problem"],
    )

    # 3. Answer the ORIGINAL QUESTION, using the retrieved chunks
    answer = generate_answer(question, sources, llm)

    return {
        "answer": answer,
        "search_query": plan["search_query"],
        "brew_method": plan["brew_method"],
        "sources": sources,
    }
