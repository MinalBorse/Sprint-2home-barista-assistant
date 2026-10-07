# ==========================================================
# step11_chroma_build.py
# ==========================================================
# Goal: store our coffee notes in Chroma ONCE.
#
# This is RAG Step 1: "prepare the knowledge base".
#   - Each note is embedded (turned into numbers) one time
#   - Text + embedding + metadata are saved to the chroma_db folder
#   - Later scripts search the saved data without re-embedding
#
# Run this script again only when the notes change.
# ==========================================================

from langchain_core.documents import Document
from src.sample_notes import SAMPLE_NOTES
from src.vector_store import get_vector_store


COLLECTION_NAME = "sample_notes"


# ----------------------------------------------------------
# STEP 1: open the collection
# ----------------------------------------------------------
vector_store = get_vector_store(COLLECTION_NAME)

count_before = vector_store._collection.count()
print("Records in Chroma before:", count_before)


# ----------------------------------------------------------
# STEP 2: turn each note into a LangChain Document
# ----------------------------------------------------------
# A Document has:
#   page_content -> the text that gets embedded and searched
#   metadata     -> extra info stored next to it (NOT embedded)
# We keep the source in metadata, so we can show it to the user.

documents = []
document_ids = []

for note in SAMPLE_NOTES:
    document = Document(
        page_content=note["text"],
        metadata={
            "source": note["source"],
            "note_id": note["id"],
        },
    )
    documents.append(document)

    # Each record gets a fixed id ("bitter", "sour", ...).
    # If we run this script again, records with the same id are
    # REPLACED, not added a second time. So no duplicates.
    document_ids.append(note["id"])


# ----------------------------------------------------------
# STEP 3: add them to Chroma
# ----------------------------------------------------------
# add_documents() does two things for us:
#   1. calls the embedding model for every document
#   2. saves text + embedding + metadata to disk
print(f"Embedding and storing {len(documents)} notes...")
vector_store.add_documents(documents=documents, ids=document_ids)


# ----------------------------------------------------------
# STEP 4: check the result
# ----------------------------------------------------------
count_after = vector_store._collection.count()
print("Records in Chroma after:", count_after)
print()
print("Done! The notes are saved in the 'chroma_db' folder.")
print("You can now search them without embedding them again.")