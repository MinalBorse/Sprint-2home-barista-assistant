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
#
# LEARNING NOTES (Module 4)
#
# What this file is: the CONDUCTOR of phase 1 (the build).
#   The src/ files contain HOW each step works. This file decides WHEN and in
#   which ORDER, passes each step's result to the next (documents -> chunks ->
#   vector store), does the final steps itself (safety check, emptying,
#   storing, test search), and prints a progress report.
#   Analogy: the src/ files are kitchen stations; this file is the head
#   barista who says "grind, then brew, then pour" and checks the cup.
#
# It is NOT part of the app. It is a separate command:
#   python build_knowledge_base.py   (phase 1: prepare, once)
#   streamlit run app.py             (phase 2: answer, every question)
#   The only connection between them is the chroma_db/ folder:
#   this file WRITES it, the app READS it.
#
# Before running:  stop the app (Ctrl + C), and check the internet works
#                  (Wikipedia, topic tagging and embeddings all need it).
# After running:   restart the app, so it opens the fresh database.
# Cost:            less than a cent. Time: about a minute.
#
# This script has NO functions (no "def"): its code runs from top to bottom
# as soon as you run the file. Known weakness (AI review #26): it would also
# run if someone IMPORTED it; an  if __name__ == "__main__":  guard would stop that.
# ==========================================================

from src.chunk_tags import tag_topics
from src.document_loader import load_all_documents
from src.document_splitter import split_all_documents
from src.llm import get_llm
from src.vector_store import KNOWLEDGE_BASE_COLLECTION, get_vector_store

print("==================== BUILDING THE KNOWLEDGE BASE ====================")
print()

# ----------------------------------------------------------
# STEP 1: LOAD (and clean) all trusted documents
# ----------------------------------------------------------
print("STEP 1 - Loading")
documents = load_all_documents()
# LEARNING NOTE: expect 2 own guides + 6 Wikipedia pages = 8 documents.
# After every build, check the line "loaded 6 web document(s)". Fewer than 6
# means a page FAILED (see its FAILED line): just run the build again.
print()

# ----------------------------------------------------------
# STEP 2: SPLIT them into chunks
# ----------------------------------------------------------
print("STEP 2 - Splitting")
chunks = split_all_documents(documents)
# LEARNING NOTE: 8 documents -> 160 chunks (6 tiny ones removed). Splitting has
# no randomness: the same documents always give the same chunks. Each chunk
# already has its chunk_id, brew_method and taste_problem labels here.
print(f"   {len(documents)} documents -> {len(chunks)} chunks")
print()

# ----------------------------------------------------------
# STEP 2b: TAG each chunk with its topic (the LLM decides)
# ----------------------------------------------------------
# Used by structured retrieval, for example to hide history and trivia.
print("STEP 2b - Tagging topics with the LLM (about a minute)...")
tag_topics(chunks, get_llm(temperature=0))
# LEARNING NOTE: temperature=0, because tagging is a DECISION (one of 7 topics),
# like the security guard. The counting loop below uses a dictionary:
# topic_counts.get(topic, 0) + 1 = "the count so far (0 if new), plus one".
# Even at temperature 0, a few borderline chunks can get a different topic
# between builds (e.g. brewing 65 in one build, 70 in another). The history
# count, the one used by a filter, stayed at 46.

topic_counts = {}
for chunk in chunks:
    topic = chunk.metadata["topic"]
    topic_counts[topic] = topic_counts.get(topic, 0) + 1
for topic, count in topic_counts.items():
    print(f"   {topic:<20} {count:>3} chunks")
print()

# Safety check: stop if something went badly wrong,
# so we never replace a good database with an empty one.
# LEARNING NOTE: this check comes BEFORE step 3 on purpose: if nothing was
# created, we stop while the old, working database is still untouched.
# raise SystemExit(1) ends the program with error code 1 ("something went wrong").
# Its limit (AI review #3): it only catches ZERO chunks. If embedding fails
# later, in step 4, the collection has already been emptied in step 3.
# A safer design: build into a NEW collection first, and switch only when it
# succeeded.
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
# LEARNING NOTE: get_vector_store() opens "coffee_knowledge" (Module 1, Lesson 5),
# and reset_collection() deletes everything in it. Together with the FIXED chunk
# ids, this guarantees exactly one copy of every chunk, and no stale chunks from
# deleted or renamed sections.
# From here until step 4 succeeds is the RISKY moment: the database is empty.
# vector_store._collection is a PRIVATE attribute of Chroma (the leading "_"),
# used here just to count records (AI review #30).
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
# LEARNING NOTE: this ONE line, for each chunk:
#   1. Chroma calls get_embeddings(): the chunk's TEXT goes to OpenRouter, and
#      1,536 numbers come back (this needs the internet)
#   2. Chroma STORES the text, the numbers, the metadata labels and the id
# The ids list is built in the same order as the chunks, so each chunk keeps
# its own id. "records now: 160" afterwards = success.
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
# LEARNING NOTE: the test search, a quick proof that the knowledge base works.
#   - k=3: the 3 closest chunks. Each result is a pair: (document, distance).
#   - Chroma returns cosine DISTANCE, so similarity = 1 - distance
#     (the "hnsw:space": "cosine" setting in src/vector_store.py).
#   - Expected: the bitter section first, about 0.742, even though the question
#     never says "bitter": the embeddings and the heading's synonyms find it.
#   - The score is the same in every build: embeddings have no randomness.
#   - This is a "smoke test": it shows the result, but it does not FAIL
#     automatically if the result is wrong. You check it by reading.

rank = 1
for document, distance in results:
    similarity = 1 - distance
    title = document.metadata["title"]
    section = document.metadata.get("section", "")
    print(f"   {rank}. {similarity:.3f}  [{title}] {section}")
    rank = rank + 1
print()

print("Done! The knowledge base is ready in the 'chroma_db' folder.")
# LEARNING NOTE: now restart the app (streamlit run app.py). The app opened the
# old database once at startup (st.cache_resource) and won't see this new one
# until it restarts.
