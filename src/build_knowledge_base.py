# ==========================================================
# build_knowledge_base.py
# ==========================================================
# Builds our REAL coffee knowledge base in Chroma.
#
# RAG Step 1, all four parts:
#   LOAD -> SPLIT -> EMBED -> STORE
#
# When to run this script:
#   - once, before using the chatbot
#   - again whenever you add, remove or change a source
#     (in data/ or in src/knowledge_sources.py)
#
# REQUIREMENT: "Create a knowledge base relevant to your domain"
# REQUIREMENT: "Implement standard document retrieval with embeddings"
# REQUIREMENT: "Use chunking strategies"
# ==========================================================

from src.chunk_tags import tag_topics
from src.document_loader import load_all_documents
from src.document_splitter import split_all_documents
from src.llm import get_llm
from src.vector_store import get_vector_store, KNOWLEDGE_BASE_COLLECTION


print("==================== BUILDING THE KNOWLEDGE BASE ====================")
print()

# ----------------------------------------------------------
# STEP 1: LOAD (and clean) all trusted documents
# ----------------------------------------------------------
print("STEP 1 - Loading")
documents = load_all_documents()
print()

# ----------------------------------------------------------
# STEP 2: SPLIT them into chunks
# ----------------------------------------------------------
print("STEP 2 - Splitting")
chunks = split_all_documents(documents)
print(f"   {len(documents)} documents -> {len(chunks)} chunks")
print()

# ----------------------------------------------------------
# STEP 2b: TAG each chunk with its topic (the LLM decides)
# ----------------------------------------------------------
# Used by structured retrieval, for example to hide history and trivia.
print("STEP 2b - Tagging topics with the LLM (about a minute)...")
tag_topics(chunks, get_llm(temperature=0))

topic_counts = {}
for chunk in chunks:
    topic = chunk.metadata["topic"]
    topic_counts[topic] = topic_counts.get(topic, 0) + 1
for topic, count in topic_counts.items():
    print(f"   {topic:<20} {count:>3} chunks")
print()

# Safety check: stop if something went badly wrong,
# so we never replace a good database with an empty one.
if len(chunks) == 0:
    print("ERROR: no chunks were created. The database was NOT changed.")
    raise SystemExit(1)

# ----------------------------------------------------------
# STEP 3: start from an EMPTY collection
# ----------------------------------------------------------
# Why empty it first?
#   If we removed a source or rewrote a guide, its OLD chunks would
#   otherwise stay in the database and keep showing up in searches.
#   Rebuilding from scratch costs less than a cent and is always correct.
print(f"STEP 3 - Emptying the '{KNOWLEDGE_BASE_COLLECTION}' collection")
vector_store = get_vector_store(KNOWLEDGE_BASE_COLLECTION)
vector_store.reset_collection()
print("   records now:", vector_store._collection.count())
print()

# ----------------------------------------------------------
# STEP 4: EMBED and STORE every chunk
# ----------------------------------------------------------
# Each chunk gets its stable id, like "troubleshooting_guide-3"
chunk_ids = []
for chunk in chunks:
    chunk_ids.append(chunk.metadata["chunk_id"])

print(f"STEP 4 - Embedding and storing {len(chunks)} chunks (a few seconds)...")
vector_store.add_documents(documents=chunks, ids=chunk_ids)
print("   records now:", vector_store._collection.count())
print()

# ----------------------------------------------------------
# STEP 5: a quick test search, to prove it works
# ----------------------------------------------------------
print("STEP 5 - Test search")
test_question = "My coffee tastes harsh and burnt, how can I fix it?"
print("   question:", test_question)

results = vector_store.similarity_search_with_score(test_question, k=3)

rank = 1
for document, distance in results:
    similarity = 1 - distance
    title = document.metadata["title"]
    section = document.metadata.get("section", "")
    print(f"   {rank}. {similarity:.3f}  [{title}] {section}")
    rank = rank + 1
print()

print("Done! The knowledge base is ready in the 'chroma_db' folder.")
