# ==========================================================
# src/vector_store.py
# ==========================================================
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
        collection_metadata={"hnsw:space": "cosine"},
    )

    return vector_store
