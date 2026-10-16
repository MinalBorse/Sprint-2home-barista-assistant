# ==========================================================
# src/vector_store.py
# ==========================================================
# LEARNING NOTES (Module 1, Lesson 5)
#
# What is inside the chroma_db/ folder:
#   - chroma.sqlite3: the collection NAMES, the chunk texts, metadata and ids
#   - folders with long random names (UUIDs): the search index for the
#     embeddings. Chroma keeps track of which folder belongs to which collection.
#   You won't find "coffee_knowledge" as a file name. Never edit these files by
#   hand; always go through Chroma. If the folder breaks, delete it and rebuild.
#
# Where data goes in and out:
#   - build_knowledge_base.py: vector_store.add_documents(documents=chunks, ids=...)
#     -> Chroma embeds each chunk and stores text + numbers + metadata + id
#   - app.py: searches the same collection for every question
#   - The app opens the database ONCE (st.cache_resource): after a rebuild,
#     restart the app so it uses the fresh data.
# Purpose: open the vector database (ChromaDB).
#
# What is a vector database?
#   A database that stores, for every piece of text:
#     - the text itself
#     - its embedding (the list of numbers)
#     - metadata (for example, which document it came from)
#   and can quickly find the texts closest in MEANING to a question.
#
# Why one shared function?
#   The script that BUILDS the database and the scripts that SEARCH it
#   must use exactly the same folder, embedding model and settings.
#   If they didn't, the search could open an empty database
#   without any error message. One function = same settings everywhere.
# ==========================================================

from langchain_chroma import Chroma

from src.embeddings import get_embeddings

# The folder where Chroma saves everything on disk.
# (It's in .gitignore, because it can always be rebuilt.)
CHROMA_FOLDER = "chroma_db"

# The collection for our REAL knowledge base.
# (The 5 practice notes live in a separate "sample_notes" collection.)
# Every file that needs the knowledge base uses this constant,
# so the name can never be mistyped in one place.
KNOWLEDGE_BASE_COLLECTION = "coffee_knowledge"
# LEARNING NOTE: a COLLECTION is like a TABLE. chroma_db/ holds two:
# "coffee_knowledge" (160 chunks) and "sample_notes" (5 practice notes).
# A typo like "coffee_knowledg" would silently open a NEW, EMPTY collection
# with no error, which is why everyone imports this constant instead.


def get_vector_store(collection_name):
    """
    Open (or create) a Chroma collection.

    collection_name: like a table name in a normal database,
                     for example "sample_notes" or KNOWLEDGE_BASE_COLLECTION
    """

    vector_store = Chroma(
        # Which "table" to use
        collection_name=collection_name,
        # The embedding model. Chroma uses it automatically:
        #   - when we ADD texts (to embed them once)
        #   - when we SEARCH (to embed the question)
        # Same model for both = Rule #1 from the embeddings lesson.
        embedding_function=get_embeddings(),
        # Save to disk, so the data survives after the script ends
        persist_directory=CHROMA_FOLDER,
        # Measure similarity with cosine (the angle between vectors)
        # LEARNING NOTE: HNSW is the index that finds close neighbours quickly, without
        # comparing the question with every chunk (like motorway -> main road -> side
        # street, instead of walking every street). "hnsw:space" chooses HOW closeness
        # is measured: "l2" (Chroma's default, straight-line distance), "ip" (inner
        # product) or "cosine" (the ANGLE between two embeddings: direction = meaning).
        # Cosine is what we calculated by hand in learning/step07_embeddings.py.
        # Chroma works with cosine DISTANCE = 1 - cosine similarity (0 = same direction).
        # This setting is fixed when the collection is created; a rebuild applies it.
        collection_metadata={"hnsw:space": "cosine"},
    )

    return vector_store
