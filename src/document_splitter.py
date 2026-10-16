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
#
# LEARNING NOTES (Module 3, Lessons 5-6)
#
# When does this file run?
#   Only during the BUILD (python build_knowledge_base.py, step 2).
#   NOT when the app starts, and NOT on "New conversation": the app only reads
#   the chunks already saved in chroma_db/.
#
# The real build order:
#   1. load:   8 documents (src/document_loader.py)
#   2. split:  8 documents -> 160 chunks (THIS file); while splitting, each
#              chunk also gets its brew_method and taste_problem labels
#   3. topics: all chunks tagged at once (tag_topics in src/chunk_tags.py)
#   4. embed and store in chroma_db/ (build_knowledge_base.py)
#
# The simple picture: cutting long books into INDEX CARDS, one idea per card.
#   8 documents in -> 160 labelled cards with fixed names out (6 tiny ones removed)
# ==========================================================

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from src.brew_methods import detect_brew_method
from src.chunk_tags import detect_taste_problem

# LEARNING NOTE: this file CALLS the two labelling functions, which is why the
# course studied them first (learn the ingredient before the recipe).

# ----------------------------------------------------------
# Settings
# ----------------------------------------------------------
# Maximum length of one chunk, in characters
CHUNK_SIZE = 1000
# LEARNING NOTE: a MAXIMUM, not an exact size. 1,000 characters is about 250
# tokens: big enough for one complete idea, small enough to stay precise, and far
# below the embedding model's limit (~8,000 tokens, see check_embedding_ctx_length
# in src/embeddings.py). Four chunks fit easily in a prompt.

# How many characters each chunk repeats from the previous one,
# so ideas at the border are not cut in half
CHUNK_OVERLAP = 150
# LEARNING NOTE: the overlap, pictured:
#   chunk 1: [.................... the bloom releases gas]
#   chunk 2:               [the bloom releases gas, so wait 30 seconds ....]
#                           ^ the 150 repeated characters
# Overlap only happens when text is cut BY SIZE. Sections cut at headings don't
# overlap: each heading is a clean new start.

# Chunks shorter than this are dropped. A chunk of 18 characters
# (like a stray heading) has almost no meaning, but it would still
# take a place in the search results if it happened to match.
MIN_CHUNK_CHARACTERS = 100
# LEARNING NOTE: in our build, 6 tiny chunks were removed this way.

# Which Markdown headings start a new chunk, and the metadata
# name to save them under. "#" = title, "##" = section.
MARKDOWN_HEADINGS = [
    ("#", "document_title"),
    ("##", "section"),
]
# LEARNING NOTE: this is where two labels come from. In our real bitter chunk:
#   document_title: 'Coffee Troubleshooting Guide'   (the file's "#" heading)
#   section: 'Bitter, harsh, burnt or astringent coffee'   (its "##" heading)


# ----------------------------------------------------------
# The two splitters
# ----------------------------------------------------------
# Splits Markdown at the headings above.
# strip_headers=False keeps the heading INSIDE the chunk text.
# That matters: our headings contain synonyms like
# "Bitter, harsh, burnt or astringent coffee", which help the search.
# LEARNING NOTE: only the chunk TEXT is embedded. Keeping the heading in the text
# puts all its synonyms into the embedding, which is why "harsh and burnt" finds
# the bitter section first (about 0.74). If a section is longer than CHUNK_SIZE
# and gets cut again, the heading text appears only on the FIRST piece; the other
# pieces still keep the section's LABELS (in metadata).
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=MARKDOWN_HEADINGS,
    strip_headers=False,
)

# Splits any text by size. It tries to cut at the most natural
# place first: paragraphs ("\n\n"), then lines ("\n"),
# then words (" "), and only as a last resort anywhere ("").
# LEARNING NOTE: "\n\n" (a blank line) marks a paragraph break. That's why
# remove_extra_blank_lines() in src/document_loader.py keeps exactly one blank
# line between paragraphs: the splitter needs it to find natural cut points.
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
    # LEARNING NOTE: think of a guide as a booklet with chapters (## headings).
    # split_text() only receives the TEXT, so each new piece knows only its heading
    # labels and FORGETS the booklet's own labels (source, title, source_type).
    # The loop below puts them back:
    #   1. heading_metadata = section.metadata   -> save the chapter's labels
    #   2. dict(document.metadata)               -> a COPY of the booklet's labels
    #                                               (dict() makes a copy, so pieces
    #                                               don't share one dictionary)
    #   3. .update(heading_metadata)             -> add the chapter's labels on top
    # Result: every piece has ALL its labels (e.g. source_type AND section).
    # Heading-based cutting works because the text under each heading really is
    # about that heading. We also kept each section under 1,000 characters (e.g.
    # the 5 newer brew methods), so each stays ONE chunk with its heading on it.
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
    # LEARNING NOTE: the loops in this function
    #   Loop B  for document in documents:   8 rounds, one per document (the main loop)
    #     Loop C  for chunk in chunks:       each piece: throw away tiny ones (filtering)
    #     Loop D  for chunk in chunks:       each kept piece: name tag + 2 stickers
    #   Loops C and D are INSIDE loop B: for every document, they run through
    #   THAT document's pieces. all_chunks is the big pile, empty at the start;
    #   removed_count counts the thrown-away pieces.
    all_chunks = []
    removed_count = 0

    for document in documents:
        # Choose the strategy based on the type of document
        # LEARNING NOTE: step 1, choose how to cut. The source_type label from the LOADER
        # decides: own guide -> by chapters; Wikipedia -> by size only.
        if document.metadata.get("source_type") == "own guide":
            chunks = split_markdown_document(document)
        else:
            # split_documents keeps the metadata (source, title, ...)
            # on every chunk automatically
            chunks = size_splitter.split_documents([document])

        # Drop chunks that are too short to be useful
        # LEARNING NOTE: step 2, the FILTERING pattern: start with an empty list, look at
        # each item, and append() only the ones that pass the test (100+ characters).
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
        # LEARNING NOTE: step 3, a fixed name tag for every chunk: title + number.
        #   - Chroma stores chunks BY ID: the same id on a rebuild REPLACES the old chunk,
        #     while random ids would store duplicates. Together with reset_collection()
        #     in build_knowledge_base.py, this guarantees exactly one copy of each chunk.
        #   - Readable ids also make chunks easy to find and test ("troubleshooting_guide-3").
        #   - chunk_number is a COUNTER (0, 1, 2...), so each piece gets a different number.
        #     The number is the chunk's POSITION, so inserting a new section earlier in a
        #     guide shifts the numbers after it (fine, because the build resets first).
        #   - Known weakness (AI review #25): two sources with the same title would give
        #     the same ids, and the build would fail.
        title_for_id = document.metadata["title"].replace(" ", "_")
        chunk_number = 0
        for chunk in chunks:
            chunk.metadata["chunk_id"] = f"{title_for_id}-{chunk_number}"
            chunk_number = chunk_number + 1

            # STRUCTURED METADATA for structured retrieval:
            # tag each chunk with the brew method it is about
            # ("moka pot", "espresso", ... or "general")
            # LEARNING NOTE: step 4, two stickers (src/brew_methods.py, src/chunk_tags.py).
            # .get("section", "") = the section label, or an empty text if there is none.
            # Wikipedia chunks have NO section: their brew method comes from the TITLE alone
            # ("Espresso" -> espresso), and their taste problem is always "none".
            chunk.metadata["brew_method"] = detect_brew_method(
                chunk.metadata.get("title", ""),
                chunk.metadata.get("section", ""),
            )

            # ...and with the taste problem its section is about
            # ("bitter", "sour", ... or "none")
            chunk.metadata["taste_problem"] = detect_taste_problem(chunk.metadata.get("section", ""))

        # LEARNING NOTE: append(x) adds ONE item; extend(list) adds ALL items of a list.
        all_chunks.extend(chunks)

    print(f"   removed {removed_count} chunk(s) shorter than {MIN_CHUNK_CHARACTERS} characters")
    return all_chunks
