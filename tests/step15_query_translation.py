# ==========================================================
# step15_query_translation.py
# ==========================================================
# Goal: does query rewriting really improve retrieval?
#
# For each vague question we compare:
#   A) searching with the ORIGINAL question
#   B) searching with the REWRITTEN query
# and show the top 3 chunks for both.
#
# Only searching + small rewrite calls: no answers are generated,
# so this costs almost nothing.
# ==========================================================

from src.llm import get_llm
from src.vector_store import get_vector_store, KNOWLEDGE_BASE_COLLECTION
from src.rag import rewrite_query, retrieve


SHOW_TOP = 3

llm = get_llm()
vector_store = get_vector_store(KNOWLEDGE_BASE_COLLECTION)
print("Chunks in the knowledge base:", vector_store._collection.count())
print()


def show_results(label, search_query):
    """Search and print the top results on short lines."""
    sources = retrieve(search_query, vector_store, k=SHOW_TOP)

    print(f"   {label}: \"{search_query}\"")
    rank = 1
    for source in sources:
        name = source["title"]
        if source["section"]:
            name = name + " | " + source["section"]
        print(f"      {rank}. {source['similarity']:.3f}  {name[:65]}")
        rank = rank + 1


# Vague, slang or casual questions - the kind real users type
VAGUE_QUESTIONS = [
    "why's my cup so meh?",
    "it's kinda puckery and thin, help",
    "my stovetop thing makes bitter stuff",
    "how hot should the water be for pour over?",
    "what makes beans taste chocolatey?",
]

for question in VAGUE_QUESTIONS:
    print("==================================================")
    print("QUESTION:", question)

    # A) without rewriting
    show_results("ORIGINAL ", question)

    # B) with rewriting
    rewritten = rewrite_query(question, llm)
    show_results("REWRITTEN", rewritten)
    print()
