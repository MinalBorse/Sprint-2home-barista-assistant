# ==========================================================
# step16_structured_retrieval.py
# ==========================================================
# Goal: does STRUCTURED RETRIEVAL (the brew-method filter) help?
#
# For each question we:
#   1. let the planner make a search plan (query + brew_method)
#   2. search WITHOUT the filter, then WITH the filter
#   3. show the top results, tagged with each chunk's brew_method
#
# Only planning + searching: no answers, so it costs almost nothing.
# ==========================================================

from src.llm import get_llm
from src.vector_store import get_vector_store, KNOWLEDGE_BASE_COLLECTION
from src.rag import plan_search, retrieve
from src.brew_methods import ANY


SHOW_TOP = 4

llm = get_llm()
vector_store = get_vector_store(KNOWLEDGE_BASE_COLLECTION)
print("Chunks in the knowledge base:", vector_store._collection.count())
print()


def show_results(label, search_query, brew_method):
    """Search and print the top results with their brew_method tag."""
    sources = retrieve(search_query, vector_store, k=SHOW_TOP, brew_method=brew_method)

    print(f"   {label}")
    rank = 1
    for source in sources:
        name = source["title"]
        if source["section"]:
            name = name + " | " + source["section"]
        print(f"      {rank}. {source['similarity']:.3f}  [{source['brew_method']:<12}] {name[:50]}")
        rank = rank + 1


QUESTIONS = [
    "Why does my moka pot coffee taste burnt?",
    "How long should my cafetiere steep?",
    "What grind should I use for my V60?",
    "My espresso shot runs really fast and tastes sour",
    "why's my cup so meh?",      # no brew method -> should be "any" (no filter)
]

for question in QUESTIONS:
    plan = plan_search(question, llm)

    print("==================================================")
    print("QUESTION:", question)
    print(f"PLAN:     search \"{plan['search_query']}\"  |  brew_method = {plan['brew_method']}")

    show_results("WITHOUT filter:", plan["search_query"], ANY)
    if plan["brew_method"] != ANY:
        show_results(f"WITH filter ({plan['brew_method']} + general):", plan["search_query"], plan["brew_method"])
    else:
        print("   (no brew method mentioned, so no filter is used)")
    print()
