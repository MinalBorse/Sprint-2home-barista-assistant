# ==========================================================
# src/knowledge_sources.py
# ==========================================================
# The ONLY places our knowledge base is allowed to load from.
#
# Why keep a fixed list?
#   SECURITY: a web page could contain hidden text like
#   "ignore your instructions and ...". If we loaded it, that
#   text would end up in our knowledge base and in the AI's prompt.
#   This is called "indirect prompt injection".
#   By loading ONLY from sources we checked ourselves, we avoid it.
#
# REQUIREMENT: "Add relevant security measures for your domain"
# REQUIREMENT: "Create a focused knowledge base"
#
# To add a source: check it yourself first, then add it here.
# LEARNING NOTES (Module 2, Lesson 1)
#
# - This file has no functions: just two constants (capital letters are a
#   convention meaning "fixed setting"; Python doesn't require them, but it
#   does require the EXACT same spelling wherever the name is imported).
# - Used by src/document_loader.py: every .md file in LOCAL_DATA_FOLDER is read,
#   and every page in TRUSTED_WEB_SOURCES is downloaded (6 pages per build).
# - This list is security layer 2 of 7 (against indirect prompt injection).
# - Honest limit (AI review #10): the list controls WHICH pages are loaded, not
#   WHAT they say on the day we rebuild, because Wikipedia is fetched live.
#   Saving reviewed copies in data/ would be stronger.
# - After adding or removing a source: REBUILD (python build_knowledge_base.py),
#   then restart the app. The app only reads chroma_db/, never these sources.
# ==========================================================


# ----------------------------------------------------------
# Our own documents (written by us, so fully trusted)
# ----------------------------------------------------------
# Every .md file inside this folder will be loaded.
LOCAL_DATA_FOLDER = "data"
# LEARNING NOTE: our two guides live here: brewing_guide.md (11 brew methods)
# and troubleshooting_guide.md (5 taste problems). They get source_type =
# "own guide", which the "Trusted guides only" option keeps.


# ----------------------------------------------------------
# Trusted web pages
# ----------------------------------------------------------
# Wikipedia text is openly licensed (CC BY-SA): we may use it
# as long as we credit it. Our "Sources" panel will do that,
# because every chunk keeps its URL in its metadata.
TRUSTED_WEB_SOURCES = [
    "https://en.wikipedia.org/wiki/French_press",
    "https://en.wikipedia.org/wiki/AeroPress",
    "https://en.wikipedia.org/wiki/Espresso",
    "https://en.wikipedia.org/wiki/Moka_pot",
    "https://en.wikipedia.org/wiki/Coffee_roasting",
    "https://en.wikipedia.org/wiki/Coffee_preparation",
]
# LEARNING NOTE: CC BY-SA is our PERMISSION to use these pages (we credit them
# in the Sources panel). The USER_AGENT in .env is only a polite name tag that
# identifies our program to Wikipedia; it is not a permission. These pages get
# source_type = "Wikipedia".
