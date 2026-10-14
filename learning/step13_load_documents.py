# ==========================================================
# step13_load_documents.py
# ==========================================================
# Goal: LOAD our real coffee documents into LangChain.
#
# RAG Step 1 has 4 parts:  LOAD -> split -> embed -> store
# This script does LOAD only, and shows what we got,
# so we can check the quality BEFORE we split and embed.
#
# REQUIREMENT: "Create a knowledge base relevant to your domain"
# REQUIREMENT: "Implement proper error handling"
# ==========================================================

# Load .env FIRST, so USER_AGENT is set before the web loader starts
from dotenv import load_dotenv

load_dotenv()

import bs4
from langchain_community.document_loaders import DirectoryLoader, TextLoader, WebBaseLoader

from src.knowledge_sources import LOCAL_DATA_FOLDER, TRUSTED_WEB_SOURCES


# ==========================================================
# PART 1: load our own Markdown files
# ==========================================================
def load_local_documents():
    """Load every .md file from the data folder."""

    print(f"Loading local files from '{LOCAL_DATA_FOLDER}'...")

    loader = DirectoryLoader(
        LOCAL_DATA_FOLDER,
        glob="**/*.md",  # all .md files, also in subfolders
        loader_cls=TextLoader,  # read each one as plain text
        loader_kwargs={"encoding": "utf-8"},  # avoid Windows character problems
    )
    documents = loader.load()

    # Add extra metadata we will use later
    for document in documents:
        document.metadata["source_type"] = "own guide"

    print(f"   loaded {len(documents)} local document(s)")
    return documents


# ==========================================================
# PART 2: load the trusted web pages
# ==========================================================
def clean_text(text):
    """Remove the many empty lines that web pages often contain."""
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()


def load_web_documents():
    """Load each trusted URL. If one fails, report it and continue."""

    print(f"Loading {len(TRUSTED_WEB_SOURCES)} web page(s)...")
    documents = []

    for url in TRUSTED_WEB_SOURCES:
        # REQUIREMENT: error handling.
        # try/except means: TRY this code; if something goes wrong,
        # run the EXCEPT part instead of crashing the whole program.
        try:
            loader = WebBaseLoader(
                web_paths=[url],
                # Only read the article itself, not menus and sidebars
                bs_kwargs={"parse_only": bs4.SoupStrainer(id="mw-content-text")},
            )
            loaded = loader.load()

            for document in loaded:
                document.page_content = clean_text(document.page_content)

                # A readable title from the URL:
                # ".../wiki/French_press" -> "French press"
                page_name = url.split("/")[-1]
                document.metadata["title"] = page_name.replace("_", " ")
                document.metadata["source_type"] = "Wikipedia"

                documents.append(document)

            print(f"   OK      {url}")

        except Exception as error:
            print(f"   FAILED  {url}")
            print(f"           reason: {error}")

    print(f"   loaded {len(documents)} web document(s)")
    return documents


# ==========================================================
# PART 3: load everything and inspect it
# ==========================================================
local_documents = load_local_documents()
web_documents = load_web_documents()

# Put both lists together
all_documents = local_documents + web_documents
print()

print("==================== WHAT WE LOADED ====================")
total_characters = 0

for document in all_documents:
    source = document.metadata["source"]
    source_type = document.metadata["source_type"]
    length = len(document.page_content)
    total_characters = total_characters + length

    # Show the first 120 characters on one line
    preview = document.page_content[:120].replace("\n", " ")

    print(f"[{source_type}] {source}")
    print(f"   {length:,} characters")
    print(f"   preview: {preview}...")
    print()

print("========================================================")
print(f"Total documents:  {len(all_documents)}")
print(f"Total characters: {total_characters:,}")
print()
print("These documents are much too long to embed as single pieces.")
print("Next lesson: split them into smaller chunks.")
