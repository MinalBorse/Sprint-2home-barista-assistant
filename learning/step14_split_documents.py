# ==========================================================
# step14_split_documents.py
# ==========================================================
# Goal: LOAD and SPLIT all documents, then INSPECT the chunks
#       before we embed and store them (next lesson).
#
# RAG Step 1:  load -> SPLIT -> embed -> store
#
# Always look at your chunks before embedding:
# bad chunks = bad search results, and embedding costs money.
# ==========================================================

from src.document_loader import load_all_documents
from src.document_splitter import CHUNK_OVERLAP, CHUNK_SIZE, split_all_documents

# ----------------------------------------------------------
# STEP 1: load (and clean) all documents
# ----------------------------------------------------------
documents = load_all_documents()
print()


# ----------------------------------------------------------
# STEP 2: split them into chunks
# ----------------------------------------------------------
print(f"Splitting with chunk size {CHUNK_SIZE} and overlap {CHUNK_OVERLAP}...")
chunks = split_all_documents(documents)
print(f"   {len(documents)} documents -> {len(chunks)} chunks")
print()


# ----------------------------------------------------------
# STEP 3: how many chunks came from each document?
# ----------------------------------------------------------
print("==================== CHUNKS PER DOCUMENT ====================")

# Count chunks per title, using a dictionary: title -> count
chunk_counts = {}
for chunk in chunks:
    title = chunk.metadata["title"]
    chunk_counts[title] = chunk_counts.get(title, 0) + 1

for title, count in chunk_counts.items():
    print(f"   {title:<25} {count:>3} chunks")
print()


# ----------------------------------------------------------
# STEP 4: chunk sizes (are they in a sensible range?)
# ----------------------------------------------------------
sizes = []
for chunk in chunks:
    sizes.append(len(chunk.page_content))

average_size = sum(sizes) / len(sizes)
print("==================== CHUNK SIZES ====================")
print(f"   smallest: {min(sizes)} characters")
print(f"   largest:  {max(sizes)} characters (limit is {CHUNK_SIZE})")
print(f"   average:  {average_size:.0f} characters")
print()


# ----------------------------------------------------------
# STEP 5: our own guide - one chunk per section?
# ----------------------------------------------------------
print("==================== OUR GUIDE, SECTION BY SECTION ====================")
for chunk in chunks:
    if chunk.metadata.get("source_type") == "own guide":
        chunk_id = chunk.metadata["chunk_id"]
        section = chunk.metadata.get("section", "(introduction)")
        size = len(chunk.page_content)
        print(f"   {chunk_id:<26} {size:>4} chars   section: {section}")
print()


# ----------------------------------------------------------
# STEP 6: look at two Wikipedia chunks in full
# ----------------------------------------------------------
print("==================== TWO EXAMPLE WIKIPEDIA CHUNKS ====================")

# Find the first two chunks of the French press page
examples_shown = 0
for chunk in chunks:
    if chunk.metadata["title"] == "French press" and examples_shown < 2:
        print(f"--- {chunk.metadata['chunk_id']} ({len(chunk.page_content)} chars) ---")
        print(chunk.page_content)
        print()
        examples_shown = examples_shown + 1

print("Note: these two chunks may NOT share text. The splitter prefers to cut")
print("at a paragraph break, and a clean break needs no overlap. The")
print(f"{CHUNK_OVERLAP}-character overlap only appears when a cut has to happen")
print("in the middle of a long paragraph.")
print()


# ----------------------------------------------------------
# STEP 7: the shortest chunks we KEPT (are they useful?)
# ----------------------------------------------------------
print("==================== THE 5 SHORTEST CHUNKS WE KEPT ====================")
chunks_by_size = sorted(chunks, key=lambda chunk: len(chunk.page_content))
for chunk in chunks_by_size[:5]:
    preview = chunk.page_content[:90].replace("\n", " ")
    print(f"   {len(chunk.page_content):>4} chars  [{chunk.metadata['chunk_id']}] {preview}")
