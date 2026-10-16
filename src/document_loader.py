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
#
# LEARNING NOTES (Module 2, Lessons 2-5)
#
# When does this file run?
#   Only during the BUILD (python build_knowledge_base.py, step 1).
#   The app never loads documents while answering: it reads chroma_db/.
#
# What is a Document?
#   LangChain stores every piece of text as a Document with two parts:
#     - page_content: the TEXT
#     - metadata:     a dictionary of LABELS, e.g. {"title": ..., "source_type": ...}
#
# The flow of this file:
#   data/*.md         -> load_local_documents() -> 2 Documents ("own guide")
#   6 Wikipedia URLs  -> load_web_documents()   -> 6 Documents ("Wikipedia")
#                        (download -> keep the article -> clean -> label)
#   both              -> load_all_documents()   -> 8 Documents, as one list
#   Each Document is still a WHOLE file or page here. Cutting them into
#   chunks happens next, in src/document_splitter.py.
#
# Docstrings in this file are for PEOPLE. Nothing here is sent to the model.
# ==========================================================

import re

# Load .env FIRST, so USER_AGENT is set before the web loader starts
from dotenv import load_dotenv

load_dotenv()

# LEARNING NOTE: why these imports come AFTER load_dotenv()
# WebBaseLoader reads the USER_AGENT environment variable (a polite name tag
# for Wikipedia, which asks automated programs to identify themselves).
# It must be set BEFORE the loader is imported. Normally ruff wants all imports
# at the top (rule E402), so pyproject.toml allows this one deliberate exception
# for this file ([tool.ruff.lint.per-file-ignores]).
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
# LEARNING NOTE: Python names are case-sensitive and exact. "References" here
# must match the heading exactly (after removing "[edit]" and spaces).


# ==========================================================
# Cleaning helpers
# ==========================================================
# LEARNING NOTE: the cleaning pipeline (see clean_wikipedia_text below)
# Each helper cleans ONE thing and passes the text on, like
# grinder -> filter -> cup. Cleaning removes noise that would waste chunk
# space and confuse the meaning search. Example from a real build:
# French press went from 13,893 to 6,963 characters after cleaning.
#
# remove_end_sections removes the MOST text: everything from "References"
# (or "See also"...) onwards, which is only reference lists and links.
#   text.split("\n")         -> a list of lines
#   lines[:line_number]       -> only the lines BEFORE the end heading
#   "\n".join(kept_lines)     -> glue the kept lines back into one text
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


# LEARNING NOTE: re.sub(r"\[\d+\]", "", text) is a REGULAR EXPRESSION:
#   \[ = an opening bracket, \d+ = one or more digits, \] = a closing bracket.
# re.sub replaces EVERY match, so "pressure.[12][13]" -> "pressure."
# (brackets included). It does NOT remove spaces: "pressure [12] and" would
# leave a double space. That is harmless for embeddings (same meaning).
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


# LEARNING NOTE: the inner "for start in HATNOTE_STARTS" loop checks every
# known hatnote opening for each line.
# Known weakness (AI review #14, still to verify): "For the " would also drop a
# normal sentence like "For the best results, ...". Checking only the first few
# lines of a page, or matching the full hatnote shape, would be safer.
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


# LEARNING NOTE: removing lines leaves big gaps. This keeps paragraphs separated
# by exactly ONE blank line, which matters later: the splitter uses blank lines
# to find paragraph boundaries. .strip() removes spaces and line breaks only at
# the very START and END of the whole text.
def remove_extra_blank_lines(text):
    """Turn 3 or more line breaks in a row into just 2."""
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()


# LEARNING NOTE: why this order?
#   - end sections FIRST: they remove the most text, so later steps do less work
#   - blank lines LAST: they tidy the gaps the other steps created
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
# LEARNING NOTE: our own guides (Module 2, Lesson 2)
#   DirectoryLoader + loader.load() CONVERTS the .md files into Documents.
#   The for loop does not convert anything: it LABELS each Document.
#   - glob="**/*.md": every .md file, in any subfolder, so a NEW guide
#     (e.g. data/milk_drinks.md) is picked up automatically, no code change
#   - encoding "utf-8": characters like °C and é read correctly on Windows
#   - source_type "own guide": powers the "Trusted guides only" option
#   - title: from the file name; shown in the Sources panel and citations.
#     .replace("\\", "/") makes Windows paths work like any other;
#     .split("/")[-1] keeps the last piece (the file name)
#   - DirectoryLoader also adds metadata["source"] (the file path) itself
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
# LEARNING NOTE: the Wikipedia pages (Module 2, Lesson 3)
#   - the try/except is INSIDE the loop: one failed page prints FAILED with the
#     reason, and the loop continues with the next URL. Pages before it are kept;
#     pages after it load if the connection comes back.
#   - SoupStrainer(id="mw-content-text") keeps only the ARTICLE part of the page
#     (menus, sidebars and footers are dropped before they reach us).
#   - title: the last part of the URL (".../Moka_pot" -> "Moka pot")
#   - source_type "Wikipedia": filtered OUT by "Trusted guides only"
#   - Honest limit (AI review #3): with no internet at all, the build still
#     continues with just the 2 own guides, but tagging and embedding also need
#     the internet, so the build fails AFTER the old collection was emptied.
#     Check that the final count says 6, and rebuild when the internet is back.
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
# LEARNING NOTE: one doorway for both kinds of source (Module 2, Lesson 5)
# build_knowledge_base.py just calls load_all_documents() and doesn't need to
# know where documents come from. "+" on two lists joins them: own guides first,
# then Wikipedia. A new kind of source (e.g. PDFs) would only need one new loader
# function and one more "+" here.
def load_all_documents():
    """Load our own guides and the trusted web pages, as one list."""
    local_documents = load_local_documents()
    web_documents = load_web_documents()
    return local_documents + web_documents
