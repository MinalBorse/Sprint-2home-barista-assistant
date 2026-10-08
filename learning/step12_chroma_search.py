# ==========================================================
# step12_chroma_search.py
# ==========================================================
# Goal: search the notes we SAVED in Chroma (step11).
#
# Notice what is NOT in this file:
#   - no SAMPLE_NOTES import
#   - no embed_documents()
# The notes and their embeddings come from the chroma_db folder.
# Only the QUESTION is embedded here.
#
# This is RAG Step 3: "retrieve the most relevant chunks".
# ==========================================================

from src.vector_store import get_vector_store


COLLECTION_NAME = "sample_notes"
TOP_K = 2


# ----------------------------------------------------------
# Open the saved collection (nothing is embedded here)
# ----------------------------------------------------------
vector_store = get_vector_store(COLLECTION_NAME)
print("Records found in Chroma:", vector_store._collection.count())
print()


# ----------------------------------------------------------
# A helper to search and print the results
# ----------------------------------------------------------
def search(question, source_filter=None):
    """
    Find the TOP_K notes most similar to the question.

    source_filter: if given, only search notes from this source,
                   for example "v60_guide" (metadata filtering)
    """
    print("==================================================")
    print("QUESTION:", question)
    if source_filter:
        print("FILTER:   only source =", source_filter)
    print()

    # Build the filter (or no filter)
    if source_filter:
        metadata_filter = {"source": source_filter}
    else:
        metadata_filter = None

    # Chroma embeds the question and finds the nearest notes.
    # It returns a list of (document, distance) pairs.
    results = vector_store.similarity_search_with_score(
        query=question,
        k=TOP_K,
        filter=metadata_filter,
    )

    rank = 1
    for document, distance in results:
        # Chroma gives DISTANCE (lower = closer).
        # For cosine: similarity = 1 - distance (higher = closer)
        similarity = 1 - distance

        source = document.metadata["source"]
        note_id = document.metadata["note_id"]
        short_text = document.page_content[:55]

        print(f"{rank}. similarity {similarity:.3f}  [{note_id} | {source}]")
        print(f"   {short_text}...")
        rank = rank + 1

    print()


# ----------------------------------------------------------
# The tests
# ----------------------------------------------------------

# 1. Same questions as step07 - the scores should be (almost) the same
search("My coffee tastes harsh and burnt, how can I fix it?")
search("Why does my brew taste too acidic and tangy?")

# 2. Metadata filtering: only look inside the V60 guide.
#    Even a general question now returns V60 information only.
search("What grind size should I use?", source_filter="v60_guide")

# 3. The same question WITHOUT the filter, for comparison
search("What grind size should I use?")