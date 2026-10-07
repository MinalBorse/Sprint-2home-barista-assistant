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
# ==========================================================


# ----------------------------------------------------------
# Our own documents (written by us, so fully trusted)
# ----------------------------------------------------------
# Every .md file inside this folder will be loaded.
LOCAL_DATA_FOLDER = "data"


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