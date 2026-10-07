# ==========================================================
# src/document_splitter.py
# ==========================================================
# Purpose: SPLIT long documents into smaller chunks.
#
# RAG Step 1:  load -> SPLIT -> embed -> store
#
# Why split?
#   A whole Wikipedia page as ONE vector has a blurry meaning
#   (an average of everything on the page). Small chunks that
#   each hold ONE idea match questions much more precisely.
#
# Two kinds of documents, two strategies:
#   - Our own Markdown guides -> split at the ## headings first,
#     so each problem ("Sour coffee", "Bitter coffee") is its own chunk.
#   - Wikipedia pages -> split by size, at natural places
#     (paragraphs first, then lines, then words).
# ==========================================================

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


# ----------------------------------------------------------
# Settings
# ----------------------------------------------------------
# Maximum length of one chunk, in characters
CHUNK_SIZE = 1000

# How many characters each chunk repeats from the previous one,
# so ideas at the border are not cut in half
CHUNK_OVERLAP = 150

# Chunks shorter than this are dropped. A chunk of 18 characters
# (like a stray heading) has almost no meaning, but it would still
# take a place in the search results if it happened to match.
MIN_CHUNK_CHARACTERS = 100

# Which Markdown headings start a new chunk, and the metadata
# name to save them under. "#" = title, "##" = section.
MARKDOWN_HEADINGS = [
    ("#", "document_title"),
    ("##", "section"),
]


# ----------------------------------------------------------
# The two splitters
# ----------------------------------------------------------
# Splits Markdown at the headings above.
# strip_headers=False keeps the heading INSIDE the chunk text.
# That matters: our headings contain synonyms like
# "Bitter, harsh, burnt or astringent coffee", which help the search.
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=MARKDOWN_HEADINGS,
    strip_headers=False,
)

# Splits any text by size. It tries to cut at the most natural
# place first: paragraphs ("\n\n"), then lines ("\n"),
# then words (" "), and only as a last resort anywhere ("").
size_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", " ", ""],
)


# ==========================================================
# Splitting one Markdown guide
# ==========================================================
def split_markdown_document(document):
    """
    Split one of our own guides:
      1. at the headings (one section = one chunk)
      2. by size, only if a section is still longer than CHUNK_SIZE
    """
    # Step 1: split at the headings.
    # The result only has the heading metadata (document_title, section),
    # so we copy the original metadata (source, title, ...) onto every piece.
    sections = markdown_splitter.split_text(document.page_content)

    for section in sections:
        heading_metadata = section.metadata
        section.metadata = dict(document.metadata)
        section.metadata.update(heading_metadata)

    # Step 2: split long sections by size (short ones stay as they are)
    chunks = size_splitter.split_documents(sections)
    return chunks


# ==========================================================
# Splitting everything
# ==========================================================
def split_all_documents(documents):
    """
    Split every document with the right strategy,
    and give every chunk a stable, unique id.
    """
    all_chunks = []
    removed_count = 0

    for document in documents:
        # Choose the strategy based on the type of document
        if document.metadata.get("source_type") == "own guide":
            chunks = split_markdown_document(document)
        else:
            # split_documents keeps the metadata (source, title, ...)
            # on every chunk automatically
            chunks = size_splitter.split_documents([document])

        # Drop chunks that are too short to be useful
        useful_chunks = []
        for chunk in chunks:
            if len(chunk.page_content.strip()) >= MIN_CHUNK_CHARACTERS:
                useful_chunks.append(chunk)
            else:
                removed_count = removed_count + 1
        chunks = useful_chunks

        # Give each chunk an id like "troubleshooting_guide-3".
        # The same document always gives the same ids, so building
        # the database again REPLACES chunks instead of duplicating them.
        title_for_id = document.metadata["title"].replace(" ", "_")
        chunk_number = 0
        for chunk in chunks:
            chunk.metadata["chunk_id"] = f"{title_for_id}-{chunk_number}"
            chunk_number = chunk_number + 1

        all_chunks.extend(chunks)

    print(f"   removed {removed_count} chunk(s) shorter than {MIN_CHUNK_CHARACTERS} characters")
    return all_chunks
