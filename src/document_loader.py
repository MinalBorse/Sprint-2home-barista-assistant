# ==========================================================
# src/document_loader.py
# ==========================================================
# Purpose: LOAD and CLEAN all documents for the knowledge base.
#
# RAG Step 1:  LOAD -> split -> embed -> store
#
# Every document comes from src/knowledge_sources.py
# (our list of trusted sources), and nowhere else.
#
# REQUIREMENT: "Create a knowledge base relevant to your domain"
# REQUIREMENT: "Implement proper error handling"
# ==========================================================

import re

# Load .env FIRST, so USER_AGENT is set before the web loader starts
from dotenv import load_dotenv
load_dotenv()

import bs4
from langchain_community.document_loaders import DirectoryLoader, TextLoader, WebBaseLoader
from src.knowledge_sources import LOCAL_DATA_FOLDER, TRUSTED_WEB_SOURCES


# Wikipedia sections that come AFTER the useful article text.
# Everything from the first of these headings onward is removed.
END_SECTIONS = [
    "See also",
    "Notes",
    "References",
    "Further reading",
    "External links",
    "Bibliography",
]


# ==========================================================
# Cleaning helpers
# ==========================================================
def remove_end_sections(text):
    """
    Cut the text at the first end section, like "References".
    We check line by line: if a line IS one of those headings,
    we keep only the text before it.
    """
    lines = text.split("\n")

    for line_number in range(len(lines)):
        # Wikipedia headings may end with "[edit]", so we remove that first
        line = lines[line_number].replace("[edit]", "").strip()

        if line in END_SECTIONS:
            kept_lines = lines[:line_number]
            return "\n".join(kept_lines)

    # No end section found: keep everything
    return text


def remove_citation_markers(text):
    """
    Remove markers like [12], [citation needed] and [edit].
    The pattern below means: "[" + one or more digits + "]"
    """
    text = re.sub(r"\[\d+\]", "", text)
    text = text.replace("[citation needed]", "")
    text = text.replace("[edit]", "")
    return text


# Lines at the top of Wikipedia pages that only help navigation,
# like "This article is about..." or "Not to be confused with...".
# They are called "hatnotes" and never answer a coffee question.
HATNOTE_STARTS = [
    "This article is about",
    "For other uses",
    "Not to be confused with",
    "For the ",
]


def remove_hatnotes(text):
    """Drop navigation lines (hatnotes) and keep every other line."""
    kept_lines = []

    for line in text.split("\n"):
        stripped = line.strip()

        # Is this line a hatnote?
        is_hatnote = False
        for start in HATNOTE_STARTS:
            if stripped.startswith(start):
                is_hatnote = True
        if "redirects here" in stripped:
            is_hatnote = True

        if not is_hatnote:
            kept_lines.append(line)

    return "\n".join(kept_lines)


def remove_extra_blank_lines(text):
    """Turn 3 or more line breaks in a row into just 2."""
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()


def clean_wikipedia_text(text):
    """Run all cleaning steps, in order."""
    text = remove_end_sections(text)
    text = remove_hatnotes(text)
    text = remove_citation_markers(text)
    text = remove_extra_blank_lines(text)
    return text


# ==========================================================
# Loading our own Markdown guides
# ==========================================================
def load_local_documents():
    """Load every .md file from the data folder."""
    print(f"Loading local files from '{LOCAL_DATA_FOLDER}'...")

    loader = DirectoryLoader(
        LOCAL_DATA_FOLDER,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    documents = loader.load()

    for document in documents:
        document.metadata["source_type"] = "own guide"
        # A readable title from the file name:
        # "data/troubleshooting_guide.md" -> "troubleshooting guide"
        file_name = document.metadata["source"].replace("\\", "/").split("/")[-1]
        document.metadata["title"] = file_name.replace(".md", "").replace("_", " ")

    print(f"   loaded {len(documents)} local document(s)")
    return documents


# ==========================================================
# Loading the trusted web pages
# ==========================================================
def load_web_documents():
    """Load and clean each trusted URL. If one fails, report it and continue."""
    print(f"Loading {len(TRUSTED_WEB_SOURCES)} web page(s)...")
    documents = []

    for url in TRUSTED_WEB_SOURCES:
        try:
            loader = WebBaseLoader(
                web_paths=[url],
                bs_kwargs={"parse_only": bs4.SoupStrainer(id="mw-content-text")},
            )
            loaded = loader.load()

            for document in loaded:
                length_before = len(document.page_content)
                document.page_content = clean_wikipedia_text(document.page_content)
                length_after = len(document.page_content)

                page_name = url.split("/")[-1]
                document.metadata["title"] = page_name.replace("_", " ")
                document.metadata["source_type"] = "Wikipedia"

                documents.append(document)

                print(f"   OK      {page_name:<20} {length_before:>7,} -> {length_after:>7,} characters after cleaning")

        except Exception as error:
            print(f"   FAILED  {url}")
            print(f"           reason: {error}")

    print(f"   loaded {len(documents)} web document(s)")
    return documents


# ==========================================================
# Loading everything
# ==========================================================
def load_all_documents():
    """Load our own guides and the trusted web pages, as one list."""
    local_documents = load_local_documents()
    web_documents = load_web_documents()
    return local_documents + web_documents
